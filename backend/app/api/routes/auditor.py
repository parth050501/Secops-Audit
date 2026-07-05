from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.event import GovernanceEvent
from app.models.audit_log import AuditLog
from app.models.connector import Connector
from app.models.tenant import Tenant
from app.frameworks.definitions import FRAMEWORKS
from app.services.template_engine import generate_audit_summary_from_template

router = APIRouter()

async def _build_report(user: User, db: AsyncSession) -> dict:
    tid = user.tenant_id
    t = (await db.execute(select(Tenant).where(Tenant.id == tid))).scalar_one_or_none()
    if not t: raise HTTPException(status_code=404, detail="Tenant not found")

    fw_key = t.active_framework
    fw     = FRAMEWORKS.get(fw_key, {})

    events  = (await db.execute(select(GovernanceEvent).where(GovernanceEvent.tenant_id == tid))).scalars().all()
    tickets = (await db.execute(select(Ticket).where(Ticket.tenant_id == tid))).scalars().all()
    connectors = (await db.execute(select(Connector).where(Connector.tenant_id == tid))).scalars().all()
    logs    = (await db.execute(select(AuditLog).where(AuditLog.tenant_id == tid).order_by(AuditLog.timestamp.desc()).limit(50))).scalars().all()

    open_ev   = [e for e in events if e.status == "open"]
    critical  = sum(1 for e in open_ev if e.severity == "critical")
    high      = sum(1 for e in open_ev if e.severity == "high")
    medium    = sum(1 for e in open_ev if e.severity == "medium")
    deductions = critical*8 + high*4 + medium*2
    score     = max(0, 100 - deductions)

    open_tickets = sum(1 for t_ in tickets if t_.status in ("open","assigned","in_review"))
    resolved  = sum(1 for t_ in tickets if t_.status == "remediated")
    accepted  = sum(1 for t_ in tickets if t_.status in ("accepted","remediated"))
    rejected  = sum(1 for t_ in tickets if t_.status == "rejected")

    # Control compliance
    controls = fw.get("controls", [])
    ctrl_status = []
    for ctrl in controls:
        ctrl_id = ctrl["id"]
        mapped = [e for e in open_ev if ctrl_id in (e.framework_mappings or {}).get(fw_key, [])]
        ctrl_status.append({**ctrl, "status": "failing" if mapped else "passing",
                             "open_findings": len(mapped)})

    # Evidence items — each connector represents an evidence source
    evidence = []
    for c in connectors:
        conn_events = [e for e in events if e.connector_id == c.id]
        evidence.append({
            "source": c.name, "type": c.category, "connector_type": c.connector_type,
            "events_collected": len(conn_events),
            "last_collected": c.last_seen.isoformat() if c.last_seen else None,
            "status": "current" if c.status == "connected" else "stale",
        })

    # Ticket summary for auditor
    ticket_summary = [{
        "id": t_.id,
        "ref": t_.ref, "title": t_.title, "severity": t_.severity,
        "status": t_.status, "framework": t_.framework, "control_ids": t_.control_ids,
        "created_at": t_.created_at.isoformat() if t_.created_at else None,
        "resolved_at": t_.updated_at.isoformat() if t_.status == "remediated" and t_.updated_at else None,
    } for t_ in sorted(tickets, key=lambda x: x.created_at, reverse=True)]

    # Audit trail
    audit_trail = [{
        "timestamp": l.timestamp.isoformat(), "user": l.user_name,
        "action": l.action, "entity_type": l.entity_type, "details": l.details,
    } for l in logs]

    stats = {"score":score,"critical":critical,"high":high,"open_tickets":open_tickets,
             "resolved":resolved,"connectors":len(connectors)}

    # Template-based executive summary (free)
    ai_summary = generate_audit_summary_from_template(
        {"name":t.name,"industry":t.industry}, stats, fw.get("name", fw_key)
    )

    # Custom company policies (the 10%)
    from app.models.custom_policy import CustomPolicy
    policies = (await db.execute(
        select(CustomPolicy).where(CustomPolicy.tenant_id == tid)
    )).scalars().all()
    custom_policies = [{
        "id": p.id, "policy_id": p.policy_id, "title": p.title,
        "category": p.category, "severity": p.severity, "eval_mode": p.eval_mode,
        "status": p.status, "last_result": p.last_result,
        "mapped_control": p.mapped_control,
    } for p in policies]

    return {
        "tenant": {"name":t.name,"industry":t.industry,"frameworks":t.frameworks,
                   "active_framework":fw_key,"framework_name":fw.get("name")},
        "score": score,
        "summary": {"critical":critical,"high":high,"medium":medium,
                    "open_tickets":open_tickets,"resolved":resolved,
                    "accepted":accepted,"rejected":rejected,
                    "total_events":len(events),"connectors":len(connectors)},
        "controls": ctrl_status,
        "custom_policies": custom_policies,
        "evidence": evidence,
        "tickets": ticket_summary,
        "audit_trail": audit_trail,
        "ai_summary": ai_summary,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
    }


@router.get("/report")
async def get_audit_report(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _build_report(user, db)


@router.get("/report/pdf")
async def download_pdf(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from fastapi.responses import Response
    from app.services.report_generator import generate_pdf_report
    report = await _build_report(user, db)
    pdf = generate_pdf_report(report)
    name = (report.get("tenant",{}).get("name","report").replace(" ","_"))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={name}_audit_report.pdf"})


@router.get("/report/excel")
async def download_excel(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from fastapi.responses import Response
    from app.services.report_generator import generate_excel_report
    report = await _build_report(user, db)
    xlsx = generate_excel_report(report)
    name = (report.get("tenant",{}).get("name","report").replace(" ","_"))
    return Response(content=xlsx,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename={name}_control_matrix.xlsx"})
