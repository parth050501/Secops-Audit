from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import os
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.tenant_guard import require_tenant_capability
from app.models.user import User
from app.models.ticket import Ticket
from app.models.event import GovernanceEvent
from app.models.audit_log import AuditLog
from app.services.template_engine import generate_ticket_from_template

router = APIRouter()

EVIDENCE_DIR = os.environ.get("EVIDENCE_DIR", "/var/lib/secops/evidence")
MAX_EVIDENCE_BYTES = 25 * 1024 * 1024  # 25 MB per file
ALLOWED_EVIDENCE_TYPES = {
    "application/pdf", "image/png", "image/jpeg", "image/gif",
    "text/plain", "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword", "application/vnd.ms-excel",
}

VALID_TRANSITIONS = {
    "open":      ["assigned","suppressed"],
    "assigned":  ["in_review","open"],
    "in_review": ["accepted","rejected"],
    "accepted":  ["remediated"],
    "rejected":  ["open"],
    "remediated":[], "suppressed":[],
}

class TicketCreate(BaseModel):
    event_id: int
    due_days: int = 30

class TicketUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    assigned_to: Optional[int] = None

@router.get("")
async def list_tickets(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(100, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Ticket).where(Ticket.tenant_id == user.tenant_id)
    if status:   q = q.where(Ticket.status == status)
    if severity: q = q.where(Ticket.severity == severity)
    q = q.order_by(Ticket.created_at.desc()).limit(limit)
    tickets = (await db.execute(q)).scalars().all()
    return [_ser(t) for t in tickets]

@router.post("")
async def create_ticket(
    data: TicketCreate,
    user: User = Depends(require_tenant_capability("work_tickets")),
    db: AsyncSession = Depends(get_db),
):
    ev = (await db.execute(
        select(GovernanceEvent).where(GovernanceEvent.id == data.event_id, GovernanceEvent.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if not ev: raise HTTPException(status_code=404, detail="Event not found")

    from app.models.tenant import Tenant
    t_obj = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one_or_none()
    fw = t_obj.active_framework if t_obj else "pci_dss"

    # Template-engine ticket content — zero cost, instant
    ai_data = generate_ticket_from_template(
        {"title":ev.title,"description":ev.description,"severity":ev.severity,
         "category":ev.category,"framework_mappings":ev.framework_mappings}, fw
    )

    # Generate ref number
    count = len((await db.execute(select(Ticket).where(Ticket.tenant_id == user.tenant_id))).scalars().all())
    ref = f"SECOPS-{count+1:04d}"

    ticket = Ticket(
        tenant_id   = user.tenant_id,
        ref         = ref,
        title       = ai_data.get("ticket_title", ev.title),
        description = ai_data.get("ticket_description", ev.description),
        severity    = ev.severity,
        category    = ev.category,
        framework   = fw,
        control_ids = list((ev.framework_mappings or {}).get(fw, [])),
        event_id    = ev.id,
        connector_id= ev.connector_id,
        status      = "open",
        created_by  = user.id,
        due_date    = datetime.utcnow() + timedelta(days=data.due_days),
        ai_recommendation = ev.ai_recommendation,
        remediation_steps = "\n".join(ai_data.get("remediation_steps", [])),
        history     = [{"timestamp": datetime.utcnow().isoformat(), "user": user.name,
                        "action": "created", "notes": "Ticket created from governance event"}],
    )
    db.add(ticket)
    ev.status    = "ticketed"
    ev.ticket_id = None  # will update after commit
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                    action="ticket_created", entity_type="ticket",
                    details={"ref":ref,"severity":ev.severity,"event_id":ev.id}))
    await db.commit(); await db.refresh(ticket)
    ev.ticket_id = ticket.id; await db.commit()
    return _ser(ticket)

@router.get("/{ticket_id}")
async def get_ticket(ticket_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    t = (await db.execute(select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id))).scalar_one_or_none()
    if not t: raise HTTPException(status_code=404, detail="Not found")
    return _ser(t)

@router.patch("/{ticket_id}")
async def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    user: User = Depends(require_tenant_capability("work_tickets")),
    db: AsyncSession = Depends(get_db),
):
    t = (await db.execute(select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id))).scalar_one_or_none()
    if not t: raise HTTPException(status_code=404, detail="Not found")

    if data.status not in VALID_TRANSITIONS.get(t.status, []):
        raise HTTPException(status_code=400, detail=f"Cannot transition from '{t.status}' to '{data.status}'")

    old_status = t.status
    t.status   = data.status
    t.updated_at = datetime.utcnow()

    if data.assigned_to: t.assigned_to = data.assigned_to
    if data.status == "accepted":  t.approved_by = user.id; t.approved_at = datetime.utcnow()
    if data.status == "rejected":  t.rejection_reason = data.notes
    if data.status == "remediated": t.resolution_notes = data.notes

    history = t.history or []
    history.append({"timestamp": datetime.utcnow().isoformat(), "user": user.name,
                    "action": f"{old_status} → {data.status}", "notes": data.notes or ""})
    t.history = history

    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                    action=f"ticket_{data.status}", entity_type="ticket", entity_id=ticket_id,
                    details={"ref":t.ref,"old_status":old_status,"new_status":data.status,"notes":data.notes}))
    await db.commit(); await db.refresh(t)

    # Fail-safe email notification on status change (never blocks; best-effort).
    try:
        from app.services.email_service import notify_ticket_event
        from app.models.tenant import Tenant
        tenant = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one_or_none()
        # notify the tenant's admins
        admins = (await db.execute(
            select(User).where(User.tenant_id == user.tenant_id, User.role == "admin")
        )).scalars().all()
        for a in admins:
            if a.email:
                await notify_ticket_event(a.email, t.title, data.status,
                                          tenant.name if tenant else "")
    except Exception:
        pass  # email is best-effort; never affect the ticket update

    return _ser(t)


class CommentIn(BaseModel):
    text: str


@router.post("/{ticket_id}/comments")
async def add_comment(ticket_id: int, data: CommentIn,
                      user: User = Depends(require_tenant_capability("work_tickets")),
                      db: AsyncSession = Depends(get_db)):
    """Add a work-done / progress comment to a ticket."""
    t = (await db.execute(select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id))).scalar_one_or_none()
    if not t: raise HTTPException(status_code=404, detail="Not found")
    text = (data.text or "").strip()
    if not text: raise HTTPException(status_code=400, detail="Empty comment")

    comments = list(t.comments or [])
    comments.append({"timestamp": datetime.utcnow().isoformat(), "user": user.name, "text": text})
    t.comments = comments
    t.updated_at = datetime.utcnow()
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                    action="ticket_comment", entity_type="ticket", entity_id=ticket_id,
                    details={"ref": t.ref}))
    await db.commit(); await db.refresh(t)
    return _ser(t)


@router.post("/{ticket_id}/evidence")
async def upload_ticket_evidence(ticket_id: int,
                                 file: UploadFile = File(...),
                                 note: str = Form(""),
                                 user: User = Depends(require_tenant_capability("work_tickets")),
                                 db: AsyncSession = Depends(get_db)):
    """Attach an evidence file to a ticket (proof the work was done)."""
    t = (await db.execute(select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id))).scalar_one_or_none()
    if not t: raise HTTPException(status_code=404, detail="Not found")

    if file.content_type not in ALLOWED_EVIDENCE_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {file.content_type}")

    contents = await file.read()
    if len(contents) > MAX_EVIDENCE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 25 MB)")

    # store under a per-tenant, per-ticket directory
    tenant_dir = os.path.join(EVIDENCE_DIR, str(user.tenant_id), "tickets", str(ticket_id))
    os.makedirs(tenant_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename or "evidence")
    dest = os.path.join(tenant_dir, f"{int(datetime.utcnow().timestamp())}_{safe_name}")
    with open(dest, "wb") as f:
        f.write(contents)

    evidence = list(t.evidence or [])
    evidence.append({
        "timestamp": datetime.utcnow().isoformat(), "user": user.name,
        "file_name": safe_name, "file_path": dest, "file_size": len(contents),
        "content_type": file.content_type, "note": (note or "").strip(),
    })
    t.evidence = evidence
    t.updated_at = datetime.utcnow()
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                    action="ticket_evidence_uploaded", entity_type="ticket", entity_id=ticket_id,
                    details={"ref": t.ref, "file_name": safe_name}))
    await db.commit(); await db.refresh(t)
    return _ser(t)


def _ser(t: Ticket):
    return {"id":t.id,"ref":t.ref,"title":t.title,"description":t.description,
            "severity":t.severity,"category":t.category,"framework":t.framework,
            "control_ids":t.control_ids,"status":t.status,
            "assigned_to":t.assigned_to,"created_by":t.created_by,
            "due_date":t.due_date.isoformat() if t.due_date else None,
            "resolution_notes":t.resolution_notes,"rejection_reason":t.rejection_reason,
            "approved_by":t.approved_by,
            "jira_key":t.jira_key,"servicenow_number":t.servicenow_number,
            "remediation_steps":t.remediation_steps,"ai_recommendation":t.ai_recommendation,
            "history":t.history or [],
            "comments":t.comments or [],
            "evidence":[{k:v for k,v in e.items() if k != "file_path"} for e in (t.evidence or [])],
            "created_at":t.created_at.isoformat() if t.created_at else None,
            "updated_at":t.updated_at.isoformat() if t.updated_at else None}
