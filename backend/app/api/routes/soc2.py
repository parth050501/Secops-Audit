from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.soc2 import SOC2Readiness, SOC2CriterionStatus
from app.models.event import GovernanceEvent
from app.frameworks.soc2_criteria import (TRUST_CATEGORIES, SOC2_CRITERIA, criteria_for_categories)

router = APIRouter()


@router.get("/criteria")
async def get_criteria(categories: Optional[str] = None):
    """Return SOC 2 criteria, optionally filtered to selected trust categories."""
    cats = categories.split(",") if categories else ["security"]
    return {"trust_categories": TRUST_CATEGORIES, "criteria": criteria_for_categories(cats)}


class ReadinessSetup(BaseModel):
    report_type: str = "type2"
    trust_categories: List[str] = ["security"]
    target_date: Optional[str] = None
    audit_period_start: Optional[str] = None
    audit_period_end: Optional[str] = None


@router.post("/setup")
async def setup_readiness(data: ReadinessSetup, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # One readiness record per tenant — replace if exists
    existing = (await db.execute(select(SOC2Readiness).where(SOC2Readiness.tenant_id == user.tenant_id))).scalar_one_or_none()
    if existing:
        await db.delete(existing)
    # Clear old criterion statuses
    old = (await db.execute(select(SOC2CriterionStatus).where(SOC2CriterionStatus.tenant_id == user.tenant_id))).scalars().all()
    for o in old:
        await db.delete(o)

    cats = list(set(data.trust_categories) | {"security"})
    r = SOC2Readiness(
        tenant_id=user.tenant_id, report_type=data.report_type, trust_categories=cats,
        target_date=_parse(data.target_date),
        audit_period_start=_parse(data.audit_period_start),
        audit_period_end=_parse(data.audit_period_end),
        status="preparing",
    )
    db.add(r)

    # Seed criterion statuses, auto-deriving readiness from existing governance events
    criteria = criteria_for_categories(cats)
    events = (await db.execute(
        select(GovernanceEvent).where(GovernanceEvent.tenant_id == user.tenant_id, GovernanceEvent.status == "open")
    )).scalars().all()
    open_focus = {e.category for e in events}

    for c in criteria:
        # If there are open findings in this criterion's focus area, it's a gap
        readiness = "gap" if c["focus"] in open_focus else "not_started"
        db.add(SOC2CriterionStatus(
            tenant_id=user.tenant_id, criterion_id=c["id"], category=c["category"],
            readiness=readiness,
        ))
    await db.commit()
    return await _readiness_summary(db, user.tenant_id)


@router.get("/readiness")
async def get_readiness(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _readiness_summary(db, user.tenant_id)


class CriterionUpdate(BaseModel):
    readiness: str          # not_started | in_progress | ready | gap
    owner: Optional[str] = None
    evidence_notes: Optional[str] = None


@router.patch("/criterion/{criterion_id}")
async def update_criterion(criterion_id: str, data: CriterionUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cs = (await db.execute(
        select(SOC2CriterionStatus).where(
            SOC2CriterionStatus.tenant_id == user.tenant_id,
            SOC2CriterionStatus.criterion_id == criterion_id)
    )).scalar_one_or_none()
    if not cs:
        raise HTTPException(status_code=404, detail="Criterion not found — run setup first")
    cs.readiness = data.readiness
    if data.owner is not None: cs.owner = data.owner
    if data.evidence_notes is not None: cs.evidence_notes = data.evidence_notes
    await db.commit()
    return await _readiness_summary(db, user.tenant_id)


def _parse(s: Optional[str]):
    if not s: return None
    try: return datetime.fromisoformat(s.replace("Z",""))
    except Exception: return None


async def _readiness_summary(db: AsyncSession, tenant_id: int) -> dict:
    r = (await db.execute(select(SOC2Readiness).where(SOC2Readiness.tenant_id == tenant_id))).scalar_one_or_none()
    if not r:
        return {"configured": False}

    statuses = (await db.execute(
        select(SOC2CriterionStatus).where(SOC2CriterionStatus.tenant_id == tenant_id)
    )).scalars().all()

    crit_map = {c["id"]: c for c in SOC2_CRITERIA}
    ready = sum(1 for s in statuses if s.readiness == "ready")
    in_progress = sum(1 for s in statuses if s.readiness == "in_progress")
    gaps = sum(1 for s in statuses if s.readiness == "gap")
    total = len(statuses)
    pct = round((ready / total * 100) if total else 0)

    # Persist overall
    r.overall_readiness = pct

    # group by trust category
    by_category = {}
    for s in statuses:
        cat = s.category
        by_category.setdefault(cat, {"ready":0,"total":0})
        by_category[cat]["total"] += 1
        if s.readiness == "ready":
            by_category[cat]["ready"] += 1

    await db.commit()

    return {
        "configured": True,
        "report_type": r.report_type,
        "trust_categories": r.trust_categories,
        "target_date": r.target_date.isoformat() if r.target_date else None,
        "audit_period_start": r.audit_period_start.isoformat() if r.audit_period_start else None,
        "audit_period_end": r.audit_period_end.isoformat() if r.audit_period_end else None,
        "overall_readiness": pct,
        "status": r.status,
        "summary": {"ready": ready, "in_progress": in_progress, "gaps": gaps,
                    "not_started": total - ready - in_progress - gaps, "total": total},
        "by_category": {k: {**v, "name": TRUST_CATEGORIES.get(k,{}).get("name",k)} for k,v in by_category.items()},
        "criteria": [{
            "criterion_id": s.criterion_id,
            "category": s.category,
            "title": crit_map.get(s.criterion_id, {}).get("title", ""),
            "focus": crit_map.get(s.criterion_id, {}).get("focus", ""),
            "readiness": s.readiness,
            "owner": s.owner,
            "evidence_notes": s.evidence_notes,
        } for s in sorted(statuses, key=lambda x: x.criterion_id)],
    }
