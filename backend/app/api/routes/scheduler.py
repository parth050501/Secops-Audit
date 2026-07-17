"""
Scheduler — asset groups and group-wide scans.

An asset group is a tenant-defined set of agents the customer creates and names
themselves. Groups let you scan many systems at once ("Scan Now" across a group)
and (stage two) run them on a schedule.

Everything here is scoped to the caller's tenant (derived from the session) — a
tenant can only see and act on its own groups and agents.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.tenant_guard import tenant_query
from app.models.collector import AssetGroup, Agent, ScanJob
from app.models.user import User

router = APIRouter()


# ── schemas ──
class GroupIn(BaseModel):
    name: str
    description: Optional[str] = ""
    agent_ids: Optional[List[int]] = []
    schedule: Optional[str] = "manual"          # manual|daily|weekly|monthly
    schedule_time: Optional[str] = "02:00"
    schedule_day: Optional[str] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agent_ids: Optional[List[int]] = None
    schedule: Optional[str] = None
    schedule_time: Optional[str] = None
    schedule_day: Optional[str] = None


def _next_run(schedule: str, time_str: str, day: str = None) -> Optional[datetime]:
    """Compute an informational next-run timestamp. The stage-two engine will use
    this; for now it makes the UI show when a group would next scan."""
    if not schedule or schedule == "manual":
        return None
    try:
        hh, mm = [int(x) for x in (time_str or "02:00").split(":")]
    except Exception:
        hh, mm = 2, 0
    now = datetime.utcnow()
    nxt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if schedule == "daily":
        if nxt <= now:
            nxt += timedelta(days=1)
    elif schedule == "weekly":
        days = ["mon","tue","wed","thu","fri","sat","sun"]
        target = days.index(day.lower()[:3]) if day and day.lower()[:3] in days else 0
        delta = (target - now.weekday()) % 7
        nxt = nxt + timedelta(days=delta)
        if nxt <= now:
            nxt += timedelta(days=7)
    elif schedule == "monthly":
        try:
            dom = int(day) if day else 1
        except Exception:
            dom = 1
        nxt = nxt.replace(day=min(dom, 28))
        if nxt <= now:
            # move to next month
            month = nxt.month + 1
            year = nxt.year + (1 if month > 12 else 0)
            month = 1 if month > 12 else month
            nxt = nxt.replace(year=year, month=month)
    return nxt


def _ser_group(g: AssetGroup, agents_by_id: dict) -> dict:
    members = [agents_by_id[a] for a in (g.agent_ids or []) if a in agents_by_id]
    return {
        "id": g.id, "name": g.name, "description": g.description,
        "agent_ids": g.agent_ids or [],
        "agents": members,               # resolved agent summaries for display
        "agent_count": len(members),
        "schedule": g.schedule, "schedule_time": g.schedule_time,
        "schedule_day": g.schedule_day,
        "last_run_at": g.last_run_at.isoformat() if g.last_run_at else None,
        "next_run_at": g.next_run_at.isoformat() if g.next_run_at else None,
    }


async def _agents_map(user: User, db: AsyncSession) -> dict:
    rows = (await db.execute(tenant_query(Agent, user))).scalars().all()
    return {a.id: {"id": a.id, "name": a.name, "system_type": a.system_type,
                   "target": a.target, "status": a.derived_status()} for a in rows}


@router.get("")
async def list_groups(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    groups = (await db.execute(tenant_query(AssetGroup, user))).scalars().all()
    amap = await _agents_map(user, db)
    return [_ser_group(g, amap) for g in groups]


@router.post("")
async def create_group(data: GroupIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("admin", "engineer"):
        raise HTTPException(status_code=403, detail="Not permitted")
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name required")
    g = AssetGroup(
        tenant_id=user.tenant_id, name=name, description=(data.description or "").strip(),
        agent_ids=data.agent_ids or [], schedule=data.schedule or "manual",
        schedule_time=data.schedule_time or "02:00", schedule_day=data.schedule_day,
        next_run_at=_next_run(data.schedule, data.schedule_time, data.schedule_day),
    )
    db.add(g); await db.commit(); await db.refresh(g)
    amap = await _agents_map(user, db)
    return _ser_group(g, amap)


@router.patch("/{group_id}")
async def update_group(group_id: int, data: GroupUpdate,
                       user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("admin", "engineer"):
        raise HTTPException(status_code=403, detail="Not permitted")
    g = (await db.execute(
        tenant_query(AssetGroup, user).where(AssetGroup.id == group_id)
    )).scalar_one_or_none()
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    for field in ("name", "description", "agent_ids", "schedule", "schedule_time", "schedule_day"):
        val = getattr(data, field)
        if val is not None:
            setattr(g, field, val)
    g.next_run_at = _next_run(g.schedule, g.schedule_time, g.schedule_day)
    await db.commit(); await db.refresh(g)
    amap = await _agents_map(user, db)
    return _ser_group(g, amap)


@router.delete("/{group_id}")
async def delete_group(group_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can delete a group")
    g = (await db.execute(
        tenant_query(AssetGroup, user).where(AssetGroup.id == group_id)
    )).scalar_one_or_none()
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")
    await db.delete(g); await db.commit()
    return {"deleted": True, "id": group_id}


@router.post("/{group_id}/scan")
async def scan_group(group_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Fan out a scan to every agent in the group — one ScanJob per agent. The
    collector picks these up on its next poll (async, by design)."""
    if user.role not in ("admin", "engineer"):
        raise HTTPException(status_code=403, detail="Not permitted")
    g = (await db.execute(
        tenant_query(AssetGroup, user).where(AssetGroup.id == group_id)
    )).scalar_one_or_none()
    if not g:
        raise HTTPException(status_code=404, detail="Group not found")

    from app.models.tenant import Tenant
    t = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one_or_none()
    framework = t.active_framework if t else None

    # Resolve the group's agents (scoped to tenant)
    amap = {a.id: a for a in (await db.execute(tenant_query(Agent, user))).scalars().all()}
    queued = 0
    for aid in (g.agent_ids or []):
        a = amap.get(aid)
        if not a:
            continue
        db.add(ScanJob(
            tenant_id=user.tenant_id, collector_id=a.collector_id, agent_id=a.id,
            system_type=a.system_type, target=a.target, framework=framework,
            status="pending", origin="on_demand",
        ))
        queued += 1
    g.last_run_at = datetime.utcnow()
    await db.commit()
    return {"queued_jobs": queued, "group": g.name,
            "note": "Each agent in the group will run on its collector's next poll."}
