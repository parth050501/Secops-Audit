"""
Reporting service — builds audience-appropriate compliance reports from the same
underlying data, presented through three lenses:

  - ciso      : executive/board level. Overall posture, scores, trends, risk
                summary. High-level, visual, no technical detail.
  - engineer  : operational level. Failing controls, specific findings,
                remediation. Technical and actionable.
  - auditor   : evidence level. Control-by-control status, evidence sources,
                what's tested vs attested. Structured for verification.

Each returns a structured dict; the PDF generator renders it. Reuses the live
compliance computation so a report matches what the dashboard shows.
"""
from datetime import datetime, timedelta
from sqlalchemy import select
from app.models.tenant import Tenant
from app.models.event import GovernanceEvent
from app.models.ticket import Ticket
from app.models.connector import Connector
from app.models.compliance_snapshot import ComplianceSnapshot


async def _base(db, tenant_id):
    from app.api.routes.governance import _controls_for_framework
    from app.services.framework_store import get_frameworks
    t = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    all_fw = await get_frameworks(db, tenant_id)
    selected = (t.frameworks if t and t.frameworks else [t.active_framework]) if t else []
    fw_data = []
    for fw_key in selected:
        fw = all_fw.get(fw_key)
        if not fw:
            continue
        controls = await _controls_for_framework(db, tenant_id, fw_key)
        total = len(controls)
        passing = sum(1 for c in controls if c["status"] == "passing")
        fw_data.append({
            "key": fw_key, "name": fw.get("name", fw_key), "version": fw.get("version"),
            "controls": controls, "total": total, "passing": passing,
            "failing": total - passing,
            "readiness_pct": round((passing / total) * 100) if total else 0,
        })
    return t, fw_data


async def _trend_for(db, tenant_id, fw_key, days=180):
    since = datetime.utcnow() - timedelta(days=days)
    snaps = (await db.execute(
        select(ComplianceSnapshot).where(
            ComplianceSnapshot.tenant_id == tenant_id,
            ComplianceSnapshot.framework_key == fw_key,
            ComplianceSnapshot.captured_at >= since,
        ).order_by(ComplianceSnapshot.captured_at.asc())
    )).scalars().all()
    return [{"at": s.captured_at.isoformat(), "readiness_pct": s.readiness_pct} for s in snaps]


async def build_ciso_report(db, tenant_id):
    """Executive summary — posture, scores, trends, risk headline."""
    t, fw_data = await _base(db, tenant_id)
    events = (await db.execute(select(GovernanceEvent).where(
        GovernanceEvent.tenant_id == tenant_id, GovernanceEvent.status == "open"))).scalars().all()
    crit = sum(1 for e in events if e.severity == "critical")
    high = sum(1 for e in events if e.severity == "high")

    overall = round(sum(f["readiness_pct"] for f in fw_data) / len(fw_data)) if fw_data else 0
    fw_summ = []
    for f in fw_data:
        trend = await _trend_for(db, tenant_id, f["key"])
        delta = None
        if len(trend) >= 2:
            delta = round(trend[-1]["readiness_pct"] - trend[0]["readiness_pct"], 1)
        fw_summ.append({"name": f["name"], "readiness_pct": f["readiness_pct"],
                        "passing": f["passing"], "total": f["total"], "delta": delta,
                        "trend": trend})

    # headline risk framing
    if crit > 0:
        headline = f"{crit} critical issue{'s' if crit != 1 else ''} require{'' if crit != 1 else 's'} immediate attention."
    elif high > 0:
        headline = f"{high} high-severity issue{'s' if high != 1 else ''} to address."
    elif overall >= 90:
        headline = "Strong compliance posture across frameworks."
    else:
        headline = "Compliance posture is progressing; gaps remain to close."

    return {
        "level": "ciso", "level_label": "Executive / CISO Report",
        "tenant": {"name": t.name if t else "", "industry": (t.industry if t else "") or ""},
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "overall_readiness": overall,
        "risk": {"critical": crit, "high": high, "headline": headline},
        "frameworks": fw_summ,
    }


async def build_engineer_report(db, tenant_id):
    """Operational — every failing control with its findings and weight."""
    t, fw_data = await _base(db, tenant_id)
    fw_out = []
    for f in fw_data:
        failing = [c for c in f["controls"] if c["status"] != "passing"]
        # worst weight first
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        failing.sort(key=lambda c: order.get(c.get("weight", "medium"), 2))
        fw_out.append({
            "name": f["name"], "readiness_pct": f["readiness_pct"],
            "failing_count": len(failing),
            "failing_controls": [{
                "id": c["id"], "title": c["title"], "weight": c.get("weight"),
                "category": c.get("category"), "findings": c.get("finding_titles", []),
                "open_findings": c.get("open_findings", 0),
            } for c in failing],
        })
    return {
        "level": "engineer", "level_label": "Engineering / Operational Report",
        "tenant": {"name": t.name if t else "", "industry": (t.industry if t else "") or ""},
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "frameworks": fw_out,
    }


async def build_auditor_report(db, tenant_id):
    """Evidence — control-by-control status + evidence sources."""
    t, fw_data = await _base(db, tenant_id)
    connectors = (await db.execute(select(Connector).where(Connector.tenant_id == tenant_id))).scalars().all()
    evidence = [{
        "source": c.name, "type": c.category,
        "last_collected": c.last_seen.isoformat() if c.last_seen else None,
        "status": "current" if c.status == "connected" else "stale",
    } for c in connectors]

    fw_out = []
    for f in fw_data:
        fw_out.append({
            "name": f["name"], "version": f["version"],
            "readiness_pct": f["readiness_pct"], "passing": f["passing"], "total": f["total"],
            "controls": [{
                "id": c["id"], "title": c["title"], "status": c["status"],
                "weight": c.get("weight"), "open_findings": c.get("open_findings", 0),
            } for c in f["controls"]],
        })
    return {
        "level": "auditor", "level_label": "Auditor / Evidence Report",
        "tenant": {"name": t.name if t else "", "industry": (t.industry if t else "") or ""},
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "frameworks": fw_out, "evidence_sources": evidence,
    }


BUILDERS = {
    "ciso": build_ciso_report,
    "engineer": build_engineer_report,
    "auditor": build_auditor_report,
}


async def build_report(db, tenant_id, level="ciso"):
    builder = BUILDERS.get(level, build_ciso_report)
    return await builder(db, tenant_id)


# ── Period helpers (quarterly / monthly labels) ──
def current_period_label(cadence: str) -> str:
    now = datetime.utcnow()
    if cadence == "quarterly":
        q = (now.month - 1) // 3 + 1
        return f"{now.year}-Q{q}"
    if cadence == "monthly":
        return now.strftime("%B %Y")
    if cadence == "weekly":
        return f"week of {now.strftime('%Y-%m-%d')}"
    return f"as of {now.strftime('%Y-%m-%d')}"


LEVEL_TITLES = {
    "ciso": "Executive Report", "engineer": "Engineering Report", "auditor": "Auditor Report",
}


async def build_and_store_report(db, tenant_id: int, level: str, generated_by: str,
                                 period_label: str = None, emailed_to: int = 0):
    """Build a report, render its PDF, and persist it to history. Returns the
    GeneratedReport row. Used by scheduled delivery and manual 'save'."""
    from app.services.report_generator import generate_leveled_pdf
    from app.models.report_schedule import GeneratedReport

    report = await build_report(db, tenant_id, level)
    pdf = generate_leveled_pdf(report)
    label = period_label or f"as of {datetime.utcnow().strftime('%Y-%m-%d')}"
    overall = report.get("overall_readiness")
    if overall is None:
        # engineer/auditor reports don't carry overall — derive a simple avg
        fws = report.get("frameworks", [])
        vals = [f.get("readiness_pct") for f in fws if f.get("readiness_pct") is not None]
        overall = round(sum(vals) / len(vals)) if vals else None

    row = GeneratedReport(
        tenant_id=tenant_id, level=level,
        title=f"{LEVEL_TITLES.get(level, 'Report')} — {label}",
        period_label=label, overall_readiness=overall,
        pdf_bytes=pdf, generated_by=generated_by, emailed_to=emailed_to,
    )
    db.add(row)
    await db.commit(); await db.refresh(row)
    return row
