"""
AI routes — ALL pay-as-you-go. Nothing here is called automatically.
Credits endpoints + explicit enhancement endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.tenant import Tenant
from app.models.ticket import Ticket
from app.services import ai_metered

router = APIRouter()


@router.get("/credits")
async def credits(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ai_metered.get_balance(db, user.tenant_id)


class AddCreditsReq(BaseModel):
    amount: int  # in QC this just adds; in prod this goes through Stripe first


@router.post("/credits/purchase")
async def purchase_credits(body: AddCreditsReq, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """QC environment: simulates a Stripe purchase. Production: verify payment first."""
    if body.amount not in (10, 50, 200):
        raise HTTPException(status_code=400, detail="Credit packs: 10 ($5), 50 ($20), 200 ($60)")
    return await ai_metered.add_credits(db, user.tenant_id, body.amount)


@router.get("/usage")
async def usage(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ai_metered.get_usage_history(db, user.tenant_id)


@router.post("/enhance/ticket/{ticket_id}")
async def enhance_ticket(ticket_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Pay-as-you-go: 1 credit. Returns AI-enhanced analysis for the ticket."""
    t = (await db.execute(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    tenant = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one_or_none()
    fw = tenant.active_framework if tenant else "pci_dss"

    enhancement = await ai_metered.enhance_ticket_ai(
        db, user.tenant_id, user,
        {"id": t.id, "title": t.title, "description": t.description,
         "severity": t.severity, "control_ids": t.control_ids},
        fw,
    )

    # Persist the enhancement onto the ticket
    t.ai_recommendation = enhancement.get("enhanced_description", "")
    extra_steps = enhancement.get("custom_steps", [])
    if extra_steps:
        t.remediation_steps = "\n".join(extra_steps)
    history = t.history or []
    from datetime import datetime
    history.append({"timestamp": datetime.utcnow().isoformat(), "user": user.name,
                    "action": "ai_enhanced", "notes": "AI enhancement applied (1 credit)"})
    t.history = history
    await db.commit()

    balance = await ai_metered.get_balance(db, user.tenant_id)
    return {**enhancement, "credits_remaining": balance["remaining"]}


@router.post("/enhance/audit-summary")
async def enhance_audit_summary(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Pay-as-you-go: 2 credits. AI-written executive summary for the audit report."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Compute live stats
    from app.models.event import GovernanceEvent
    from app.models.ticket import Ticket as Tk
    from app.models.connector import Connector
    events = (await db.execute(select(GovernanceEvent).where(GovernanceEvent.tenant_id == user.tenant_id))).scalars().all()
    tickets = (await db.execute(select(Tk).where(Tk.tenant_id == user.tenant_id))).scalars().all()
    connectors = (await db.execute(select(Connector).where(Connector.tenant_id == user.tenant_id))).scalars().all()

    open_ev = [e for e in events if e.status == "open"]
    critical = sum(1 for e in open_ev if e.severity == "critical")
    high = sum(1 for e in open_ev if e.severity == "high")
    medium = sum(1 for e in open_ev if e.severity == "medium")
    score = max(0, 100 - (critical*8 + high*4 + medium*2))

    stats = {
        "score": score, "critical": critical, "high": high,
        "open_tickets": sum(1 for t in tickets if t.status in ("open","assigned","in_review")),
        "resolved": sum(1 for t in tickets if t.status == "remediated"),
        "connectors": len(connectors),
    }

    from app.frameworks.definitions import FRAMEWORKS
    fw_name = FRAMEWORKS.get(tenant.active_framework, {}).get("name", tenant.active_framework)

    summary = await ai_metered.generate_audit_summary_ai(
        db, user.tenant_id, user,
        {"name": tenant.name, "industry": tenant.industry}, stats, fw_name,
    )
    balance = await ai_metered.get_balance(db, user.tenant_id)
    return {"summary": summary, "credits_remaining": balance["remaining"]}
