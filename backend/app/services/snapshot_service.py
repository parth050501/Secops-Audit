"""
Compliance snapshot service.

Captures a point-in-time record of each framework's readiness for a tenant,
reusing the same compliance computation the live views use — so a snapshot is a
faithful freeze of what the posture actually was at that moment.
"""
from datetime import datetime
from sqlalchemy import select
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.tenant import Tenant


async def capture_snapshot(db, tenant_id: int, captured_by: str = "manual") -> list:
    """Snapshot every selected framework's posture for this tenant. Returns the
    created snapshot rows (as dicts). Reuses governance._controls_for_framework."""
    from app.api.routes.governance import _controls_for_framework
    from app.services.framework_store import get_frameworks

    t = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not t:
        return []
    selected = (t.frameworks if t.frameworks else [t.active_framework]) if t else []
    all_fw = await get_frameworks(db, tenant_id)

    created = []
    now = datetime.utcnow()
    for fw_key in selected:
        fw = all_fw.get(fw_key)
        if not fw:
            continue
        controls = await _controls_for_framework(db, tenant_id, fw_key)
        total = len(controls)
        passing = sum(1 for c in controls if c["status"] == "passing")
        failing = total - passing
        readiness = round((passing / total) * 100, 1) if total else 0.0

        # per-family breakdown
        families = {}
        for c in controls:
            fam = c.get("category", "general")
            families.setdefault(fam, {"passing": 0, "total": 0})
            families[fam]["total"] += 1
            if c["status"] == "passing":
                families[fam]["passing"] += 1
        breakdown = [
            {"category": fam, "passing": v["passing"], "total": v["total"],
             "readiness_pct": round((v["passing"] / v["total"]) * 100) if v["total"] else 0}
            for fam, v in sorted(families.items())
        ]

        snap = ComplianceSnapshot(
            tenant_id=tenant_id, framework_key=fw_key,
            framework_name=fw.get("name", fw_key),
            framework_version=fw.get("version"),
            readiness_pct=readiness, total_controls=total,
            passing=passing, failing=failing,
            family_breakdown=breakdown, captured_at=now, captured_by=captured_by,
        )
        db.add(snap)
        created.append(snap)

    if created:
        await db.commit()
        for s in created:
            await db.refresh(s)
    return created
