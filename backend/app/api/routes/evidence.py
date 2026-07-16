"""
Evidence & attestation API.

Lets a tenant attach evidence (documents, attestations) to framework controls,
and roll that up into per-control status for audit readiness.
"""
import os
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.tenant_guard import tenant_query, get_owned_or_404, require_tenant_capability
from app.models.user import User
from app.models.evidence import Evidence, ControlStatus
from app.models.event import GovernanceEvent
from app.models.audit_log import AuditLog

router = APIRouter()

# Evidence files are stored under a per-tenant directory.
EVIDENCE_ROOT = os.environ.get("EVIDENCE_DIR", "/app/data/evidence")
MAX_FILE_MB = 25
ALLOWED_TYPES = {
    "application/pdf", "image/png", "image/jpeg", "image/gif",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "text/csv",
}


def _tenant_dir(tenant_id: int) -> str:
    d = os.path.join(EVIDENCE_ROOT, str(tenant_id))
    os.makedirs(d, exist_ok=True)
    return d


# ── Upload a document as evidence ──
@router.post("/document")
async def upload_document(
    framework: str = Form(...),
    control_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    valid_until: str = Form(""),
    file: UploadFile = File(...),
    user: User = Depends(require_tenant_capability("manage_evidence")),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")

    contents = await file.read()
    if len(contents) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_FILE_MB}MB limit")

    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(file.filename or 'evidence')}"
    dest = os.path.join(_tenant_dir(user.tenant_id), safe_name)
    with open(dest, "wb") as f:
        f.write(contents)

    ev = Evidence(
        tenant_id=user.tenant_id, framework=framework, control_id=control_id,
        evidence_type="document", title=title, description=description,
        file_name=file.filename, file_path=dest, file_size=len(contents),
        content_type=file.content_type, created_by=user.name,
        valid_until=_parse_date(valid_until),
    )
    db.add(ev)
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                    action="evidence_uploaded", entity_type="evidence",
                    details={"framework": framework, "control": control_id, "title": title}))
    await db.commit(); await db.refresh(ev)
    await _recompute_control(db, user.tenant_id, framework, control_id)
    return _ser_evidence(ev)


# ── Record an attestation as evidence ──
class AttestationIn(BaseModel):
    framework: str
    control_id: str
    title: str
    attestation_note: str
    valid_until: Optional[str] = None


@router.post("/attestation")
async def create_attestation(data: AttestationIn, user: User = Depends(require_tenant_capability("manage_evidence")),
                             db: AsyncSession = Depends(get_db)):
    ev = Evidence(
        tenant_id=user.tenant_id, framework=data.framework, control_id=data.control_id,
        evidence_type="attestation", title=data.title,
        attested_by=user.name, attestation_note=data.attestation_note,
        created_by=user.name, valid_until=_parse_date(data.valid_until or ""),
    )
    db.add(ev)
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                    action="attestation_recorded", entity_type="evidence",
                    details={"framework": data.framework, "control": data.control_id}))
    await db.commit(); await db.refresh(ev)
    await _recompute_control(db, user.tenant_id, data.framework, data.control_id)
    return _ser_evidence(ev)


# ── List evidence for a control (or whole framework) ──
@router.get("")
async def list_evidence(framework: Optional[str] = None, control_id: Optional[str] = None,
                        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = tenant_query(Evidence, user)
    if framework:
        q = q.where(Evidence.framework == framework)
    if control_id:
        q = q.where(Evidence.control_id == control_id)
    rows = (await db.execute(q.order_by(Evidence.created_at.desc()))).scalars().all()
    return [_ser_evidence(e) for e in rows]


# ── Download an evidence document (tenant-scoped) ──
@router.get("/{evidence_id}/download")
async def download_evidence(evidence_id: int, user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    ev = await get_owned_or_404(db, Evidence, evidence_id, user, "Evidence not found")
    if ev.evidence_type != "document" or not ev.file_path or not os.path.exists(ev.file_path):
        raise HTTPException(status_code=404, detail="No file for this evidence")
    return FileResponse(ev.file_path, filename=ev.file_name, media_type=ev.content_type)


# ── Delete evidence (tenant-scoped) ──
@router.delete("/{evidence_id}")
async def delete_evidence(evidence_id: int, user: User = Depends(require_tenant_capability("manage_evidence")),
                          db: AsyncSession = Depends(get_db)):
    ev = await get_owned_or_404(db, Evidence, evidence_id, user, "Evidence not found")
    fw, ctrl = ev.framework, ev.control_id
    if ev.file_path and os.path.exists(ev.file_path):
        try:
            os.remove(ev.file_path)
        except OSError:
            pass
    await db.delete(ev)
    await db.commit()
    await _recompute_control(db, user.tenant_id, fw, ctrl)
    return {"message": "Evidence deleted"}


# ── Control status: list + update ──
@router.get("/controls/{framework}")
async def control_statuses(framework: str, user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        tenant_query(ControlStatus, user).where(ControlStatus.framework == framework)
    )).scalars().all()
    return [_ser_control(c) for c in rows]


class ControlUpdate(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None


@router.patch("/controls/{framework}/{control_id}")
async def update_control(framework: str, control_id: str, data: ControlUpdate,
                         user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cs = (await db.execute(
        tenant_query(ControlStatus, user).where(
            ControlStatus.framework == framework, ControlStatus.control_id == control_id)
    )).scalar_one_or_none()
    if not cs:
        cs = ControlStatus(tenant_id=user.tenant_id, framework=framework, control_id=control_id)
        db.add(cs)
    if data.status is not None:
        cs.status = data.status
    if data.owner is not None:
        cs.owner = data.owner
    if data.notes is not None:
        cs.notes = data.notes
    cs.last_reviewed = datetime.utcnow()
    await db.commit(); await db.refresh(cs)
    return _ser_control(cs)


# ── Coverage summary: how audit-ready is this framework? ──
@router.get("/coverage/{framework}")
async def coverage(framework: str, user: User = Depends(get_current_user),
                   db: AsyncSession = Depends(get_db)):
    controls = (await db.execute(
        tenant_query(ControlStatus, user).where(ControlStatus.framework == framework)
    )).scalars().all()
    evidence = (await db.execute(
        tenant_query(Evidence, user).where(Evidence.framework == framework)
    )).scalars().all()

    by_status = {}
    for c in controls:
        by_status[c.status] = by_status.get(c.status, 0) + 1

    ev_by_type = {}
    for e in evidence:
        ev_by_type[e.evidence_type] = ev_by_type.get(e.evidence_type, 0) + 1

    total = len(controls)
    satisfied = by_status.get("satisfied", 0)
    return {
        "framework": framework,
        "total_controls_tracked": total,
        "satisfied": satisfied,
        "readiness_pct": round((satisfied / total * 100) if total else 0),
        "by_status": by_status,
        "evidence_count": len(evidence),
        "evidence_by_type": ev_by_type,
    }


# ── helpers ──
def _parse_date(s: str):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", ""))
    except ValueError:
        return None


async def _recompute_control(db: AsyncSession, tenant_id: int, framework: str, control_id: str):
    """Recompute a control's satisfied_by + status from its evidence and any
    technical findings. A control with at least one piece of active evidence (or
    a handled technical finding) moves toward 'satisfied'."""
    ev = (await db.execute(
        select(Evidence).where(
            Evidence.tenant_id == tenant_id, Evidence.framework == framework,
            Evidence.control_id == control_id, Evidence.status == "active")
    )).scalars().all()

    satisfied_by = sorted({e.evidence_type for e in ev})

    # Technical signal: is there an OPEN finding mapping to this control? If so,
    # there's an unresolved technical gap. If a control had findings that are now
    # all ticketed/closed, that counts as technical coverage.
    open_findings = (await db.execute(
        select(GovernanceEvent).where(
            GovernanceEvent.tenant_id == tenant_id,
            GovernanceEvent.status == "open")
    )).scalars().all()
    has_open_tech_gap = any(
        control_id in (f.framework_mappings or {}).get(framework, []) for f in open_findings
    )

    cs = (await db.execute(
        select(ControlStatus).where(
            ControlStatus.tenant_id == tenant_id, ControlStatus.framework == framework,
            ControlStatus.control_id == control_id)
    )).scalar_one_or_none()
    if not cs:
        cs = ControlStatus(tenant_id=tenant_id, framework=framework, control_id=control_id)
        db.add(cs)

    cs.satisfied_by = satisfied_by
    # Derive a sensible status unless a human has explicitly set gap/n/a
    if cs.status not in ("not_applicable", "gap"):
        if has_open_tech_gap:
            cs.status = "in_progress"
        elif satisfied_by:
            cs.status = "satisfied"
        else:
            cs.status = "not_started"
    await db.commit()


def _ser_evidence(e: Evidence) -> dict:
    return {
        "id": e.id, "framework": e.framework, "control_id": e.control_id,
        "evidence_type": e.evidence_type, "title": e.title, "description": e.description,
        "file_name": e.file_name, "file_size": e.file_size,
        "attested_by": e.attested_by, "attestation_note": e.attestation_note,
        "status": e.status,
        "valid_until": e.valid_until.isoformat() if e.valid_until else None,
        "created_by": e.created_by,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _ser_control(c: ControlStatus) -> dict:
    return {
        "control_id": c.control_id, "framework": c.framework, "status": c.status,
        "owner": c.owner, "notes": c.notes, "satisfied_by": c.satisfied_by or [],
        "last_reviewed": c.last_reviewed.isoformat() if c.last_reviewed else None,
    }
