from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.event import GovernanceEvent
from app.models.connector import Connector
from app.models.ticket import Ticket
from app.frameworks.definitions import FRAMEWORKS, CATEGORY_LABELS
from app.services.framework_store import get_framework, get_frameworks

router = APIRouter()

@router.get("/dashboard")
async def dashboard(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    tid = user.tenant_id

    events = (await db.execute(select(GovernanceEvent).where(GovernanceEvent.tenant_id == tid))).scalars().all()
    open_ev = [e for e in events if e.status == "open"]
    tickets = (await db.execute(select(Ticket).where(Ticket.tenant_id == tid))).scalars().all()
    connectors = (await db.execute(select(Connector).where(Connector.tenant_id == tid))).scalars().all()

    critical = sum(1 for e in open_ev if e.severity == "critical")
    high     = sum(1 for e in open_ev if e.severity == "high")
    medium   = sum(1 for e in open_ev if e.severity == "medium")
    open_tickets = sum(1 for t in tickets if t.status in ("open","assigned","in_review"))
    resolved = sum(1 for t in tickets if t.status == "remediated")

    # Score: start at 100, deduct per open finding
    deductions = critical * 8 + high * 4 + medium * 2
    score = max(0, 100 - deductions)

    # Category breakdown
    categories = {}
    for e in open_ev:
        cat = e.category or "other"
        categories[cat] = categories.get(cat, 0) + 1

    # Severity trend (last 10 events)
    recent = sorted(events, key=lambda x: x.occurred_at or x.created_at, reverse=True)[:10]

    return {
        "score": score,
        "critical": critical,
        "high": high,
        "medium": medium,
        "open_tickets": open_tickets,
        "resolved": resolved,
        "connectors": len(connectors),
        "total_events": len(events),
        "categories": categories,
        "recent_events": [_ser_event(e) for e in recent],
    }

@router.get("/events")
async def get_events(
    severity: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(GovernanceEvent).where(GovernanceEvent.tenant_id == user.tenant_id)
    if severity: q = q.where(GovernanceEvent.severity == severity)
    if category: q = q.where(GovernanceEvent.category == category)
    if status:   q = q.where(GovernanceEvent.status == status)
    q = q.order_by(GovernanceEvent.occurred_at.desc()).limit(limit)
    events = (await db.execute(q)).scalars().all()
    return [_ser_event(e) for e in events]

@router.get("/controls")
async def get_controls(framework: str = None, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.tenant import Tenant
    t = (await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )).scalar_one_or_none()
    # Use the requested framework if given (and the tenant has it selected), else active
    fw_key = framework or (t.active_framework if t else "pci_dss")
    return await _controls_for_framework(db, user.tenant_id, fw_key)


async def _controls_for_framework(db, tenant_id, fw_key):
    fw = await get_framework(db, fw_key, tenant_id) or {}
    controls = fw.get("controls", [])
    events = (await db.execute(
        select(GovernanceEvent).where(
            GovernanceEvent.tenant_id == tenant_id,
            GovernanceEvent.status == "open"
        )
    )).scalars().all()
    result = []
    for ctrl in controls:
        ctrl_id = ctrl["id"]
        mapped = [e for e in events
                  if ctrl_id in (e.framework_mappings or {}).get(fw_key, [])]
        status = "failing" if mapped else "passing"
        result.append({
            **ctrl,
            "label": CATEGORY_LABELS.get(ctrl["category"], ctrl["category"]),
            "status": status,
            "open_findings": len(mapped),
            "finding_titles": [e.title for e in mapped[:3]],
        })
    return result


@router.get("/compliance")
async def get_compliance(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Unified compliance view across ALL the tenant's selected frameworks.
    Returns each framework with its controls + a readiness summary."""
    from app.models.tenant import Tenant
    t = (await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )).scalar_one_or_none()
    selected = (t.frameworks if t and t.frameworks else [t.active_framework if t else "pci_dss"])

    frameworks_out = []
    all_fw = await get_frameworks(db, user.tenant_id)
    for fw_key in selected:
        fw = all_fw.get(fw_key)
        if not fw:
            continue
        controls = await _controls_for_framework(db, user.tenant_id, fw_key)
        total = len(controls)
        passing = sum(1 for c in controls if c["status"] == "passing")
        failing = total - passing
        readiness = round((passing / total) * 100) if total else 0
        frameworks_out.append({
            "key": fw_key,
            "name": fw.get("name", fw_key),
            "short": fw.get("short", fw_key),
            "color": fw.get("color"),
            "description": fw.get("description"),
            "controls": controls,
            "summary": {
                "total_controls": total,
                "passing": passing,
                "failing": failing,
                "readiness_pct": readiness,
            },
        })
    return {
        "active_framework": t.active_framework if t else None,
        "frameworks": frameworks_out,
    }

def _ser_event(e: GovernanceEvent):
    return {
        "id": e.id, "title": e.title, "description": e.description,
        "severity": e.severity, "category": e.category,
        "source_type": e.source_type,
        "framework_mappings": e.framework_mappings,
        "status": e.status, "ticket_id": e.ticket_id,
        "connector_id": e.connector_id,
        "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
        "ai_recommendation": e.ai_recommendation,
    }
