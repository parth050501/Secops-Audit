"""
Framework & control management.

Lets a tenant:
  - list all frameworks (global built-ins + their own custom ones)
  - view a framework's controls
  - add / edit / delete individual controls
  - bulk-upload controls from CSV (to an existing OR new framework)
  - create and delete custom frameworks

Scope & safety:
  - Built-in (global) frameworks: a tenant can ADD controls to them (tenant sees
    the extended set), but cannot delete the built-in framework itself.
  - Custom frameworks: fully owned and editable by the tenant that created them.
  - All control edits are scoped so a tenant can only touch controls on a
    framework it is allowed to edit.

Honest note on data accuracy: this gives the TOOL to load complete control sets.
The control DATA must come from authoritative sources the operator provides — the
platform does not invent control definitions.
"""
import csv, io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.framework import CustomFramework, FrameworkControl

router = APIRouter()


def _slugify(name: str) -> str:
    import re
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "framework"


async def _framework_editable_by(db, fw_id, user) -> Optional[CustomFramework]:
    """Return the framework if this user may edit its controls, else None.
    Editable = a global built-in (anyone can extend) OR the tenant's own custom."""
    f = (await db.execute(select(CustomFramework).where(CustomFramework.id == fw_id))).scalar_one_or_none()
    if not f:
        return None
    if f.tenant_id is None or f.tenant_id == user.tenant_id:
        return f
    return None


# ── list & view ──
@router.get("")
async def list_frameworks(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    fws = (await db.execute(select(CustomFramework).where(
        (CustomFramework.tenant_id.is_(None)) | (CustomFramework.tenant_id == user.tenant_id)
    ))).scalars().all()
    # control counts
    out = []
    for f in fws:
        n = len((await db.execute(
            select(FrameworkControl.id).where(FrameworkControl.framework_id == f.id)
        )).scalars().all())
        out.append({"id": f.id, "key": f.key, "name": f.name, "short": f.short,
                    "description": f.description, "color": f.color,
                    "is_builtin": f.is_builtin, "custom": f.tenant_id is not None,
                    "control_count": n})
    return out


@router.get("/{fw_id}/controls")
async def get_controls(fw_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    f = (await db.execute(select(CustomFramework).where(
        CustomFramework.id == fw_id,
        (CustomFramework.tenant_id.is_(None)) | (CustomFramework.tenant_id == user.tenant_id),
    ))).scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Framework not found")
    controls = (await db.execute(
        select(FrameworkControl).where(FrameworkControl.framework_id == fw_id)
    )).scalars().all()
    return {
        "framework": {"id": f.id, "key": f.key, "name": f.name, "is_builtin": f.is_builtin},
        "controls": [{"id": c.id, "control_id": c.control_id, "title": c.title,
                      "category": c.category, "weight": c.weight, "guidance": c.guidance}
                     for c in controls],
    }


# ── create / delete framework ──
class FrameworkIn(BaseModel):
    name: str
    short: Optional[str] = None
    description: Optional[str] = ""
    color: Optional[str] = "#0F8B8D"


@router.post("")
async def create_framework(data: FrameworkIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("admin", "engineer"):
        raise HTTPException(status_code=403, detail="Not permitted")
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Framework name required")
    key = _slugify(name)
    # ensure key unique within tenant scope
    exists = (await db.execute(select(CustomFramework).where(
        CustomFramework.key == key,
        (CustomFramework.tenant_id == user.tenant_id) | (CustomFramework.tenant_id.is_(None)),
    ))).scalars().first()
    if exists:
        key = f"{key}_{int(datetime.utcnow().timestamp())}"
    f = CustomFramework(key=key, tenant_id=user.tenant_id, name=name,
                        short=(data.short or name)[:40], description=data.description,
                        color=data.color or "#0F8B8D", is_builtin=False)
    db.add(f); await db.commit(); await db.refresh(f)
    return {"id": f.id, "key": f.key, "name": f.name, "custom": True, "control_count": 0}


@router.delete("/{fw_id}")
async def delete_framework(fw_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can delete a framework")
    f = (await db.execute(select(CustomFramework).where(CustomFramework.id == fw_id))).scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Framework not found")
    if f.is_builtin or f.tenant_id is None:
        raise HTTPException(status_code=400, detail="Built-in frameworks cannot be deleted")
    if f.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Not your framework")
    # delete its controls too
    for c in (await db.execute(select(FrameworkControl).where(FrameworkControl.framework_id == fw_id))).scalars().all():
        await db.delete(c)
    await db.delete(f); await db.commit()
    return {"deleted": True, "id": fw_id}


# ── control CRUD ──
class ControlIn(BaseModel):
    control_id: str
    title: str
    category: Optional[str] = "general"
    weight: Optional[str] = "medium"
    guidance: Optional[str] = None


@router.post("/{fw_id}/controls")
async def add_control(fw_id: int, data: ControlIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("admin", "engineer"):
        raise HTTPException(status_code=403, detail="Not permitted")
    f = await _framework_editable_by(db, fw_id, user)
    if not f:
        raise HTTPException(status_code=404, detail="Framework not found or not editable")
    if not (data.control_id or "").strip() or not (data.title or "").strip():
        raise HTTPException(status_code=400, detail="control_id and title are required")
    c = FrameworkControl(framework_id=fw_id, control_id=data.control_id.strip(),
                         title=data.title.strip(), category=(data.category or "general").strip(),
                         weight=(data.weight or "medium").strip(), guidance=data.guidance)
    db.add(c); await db.commit(); await db.refresh(c)
    return {"id": c.id, "control_id": c.control_id, "title": c.title,
            "category": c.category, "weight": c.weight}


@router.patch("/controls/{control_pk}")
async def edit_control(control_pk: int, data: ControlIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("admin", "engineer"):
        raise HTTPException(status_code=403, detail="Not permitted")
    c = (await db.execute(select(FrameworkControl).where(FrameworkControl.id == control_pk))).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Control not found")
    if not await _framework_editable_by(db, c.framework_id, user):
        raise HTTPException(status_code=403, detail="Not editable")
    c.control_id = data.control_id.strip(); c.title = data.title.strip()
    c.category = (data.category or "general").strip(); c.weight = (data.weight or "medium").strip()
    c.guidance = data.guidance
    await db.commit()
    return {"id": c.id, "control_id": c.control_id, "title": c.title, "category": c.category, "weight": c.weight}


@router.delete("/controls/{control_pk}")
async def delete_control(control_pk: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("admin", "engineer"):
        raise HTTPException(status_code=403, detail="Not permitted")
    c = (await db.execute(select(FrameworkControl).where(FrameworkControl.id == control_pk))).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Control not found")
    if not await _framework_editable_by(db, c.framework_id, user):
        raise HTTPException(status_code=403, detail="Not editable")
    await db.delete(c); await db.commit()
    return {"deleted": True, "id": control_pk}


# ── bulk upload ──
@router.get("/controls-template", response_class=PlainTextResponse)
async def controls_template(user: User = Depends(get_current_user)):
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["control_id", "title", "category", "weight", "guidance"])
    w.writerow(["CC6.1", "Logical and physical access controls restrict access", "access_control", "critical", ""])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=controls_template.csv"})


@router.post("/{fw_id}/controls/bulk-upload")
async def bulk_upload_controls(fw_id: int, file: UploadFile = File(...),
                               user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("admin", "engineer"):
        raise HTTPException(status_code=403, detail="Not permitted")
    f = await _framework_editable_by(db, fw_id, user)
    if not f:
        raise HTTPException(status_code=404, detail="Framework not found or not editable")
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 text")

    reader = csv.DictReader(io.StringIO(text))
    created, errors = 0, []
    valid_weights = {"critical", "high", "medium", "low"}
    for i, row in enumerate(reader, start=2):
        cid = (row.get("control_id") or "").strip()
        title = (row.get("title") or "").strip()
        if not cid or not title:
            errors.append(f"row {i}: control_id and title required"); continue
        weight = (row.get("weight") or "medium").strip().lower()
        if weight not in valid_weights:
            weight = "medium"
        db.add(FrameworkControl(
            framework_id=fw_id, control_id=cid, title=title,
            category=(row.get("category") or "general").strip() or "general",
            weight=weight, guidance=(row.get("guidance") or "").strip() or None,
        ))
        created += 1
    if created:
        await db.commit()
    return {"created": created, "errors": errors[:50], "error_count": len(errors)}
