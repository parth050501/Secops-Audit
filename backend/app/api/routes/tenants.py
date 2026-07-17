from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.encryption import encrypt_dict, decrypt_dict
from app.core.tenant_guard import require_tenant_capability
from app.models.user import User
from app.models.tenant import Tenant
from app.models.audit_log import AuditLog
from app.frameworks.definitions import FRAMEWORKS, INDUSTRY_FRAMEWORKS

router = APIRouter()

class TenantCreate(BaseModel):
    name: str
    industry: str
    frameworks: List[str]
    active_framework: str
    timezone: str = "UTC"
    scan_schedule: str = "realtime"

class TenantUpdate(BaseModel):
    active_framework: Optional[str] = None
    frameworks: Optional[List[str]] = None
    jira_url: Optional[str] = None
    jira_token: Optional[str] = None
    servicenow_url: Optional[str] = None
    servicenow_token: Optional[str] = None

@router.post("/onboard")
async def onboard(data: TenantCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    t = Tenant(**data.model_dump(), onboarded=True)
    db.add(t); await db.commit(); await db.refresh(t)
    # Link user to tenant
    user.tenant_id = t.id
    db.add(AuditLog(tenant_id=t.id, user_id=user.id, user_name=user.name,
                    action="tenant_created", entity_type="tenant", entity_id=t.id,
                    details={"name":t.name,"industry":t.industry,"frameworks":t.frameworks}))
    await db.commit()
    return _serialize(t)

@router.get("/me")
async def get_my_tenant(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user.tenant_id:
        raise HTTPException(status_code=404, detail="No tenant — complete onboarding")
    t = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one_or_none()
    if not t: raise HTTPException(status_code=404, detail="Tenant not found")
    return _serialize(t)

@router.patch("/me")
async def update_tenant(data: TenantUpdate, user: User = Depends(require_tenant_capability("manage_tenant")), db: AsyncSession = Depends(get_db)):
    t = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one_or_none()
    if not t: raise HTTPException(status_code=404, detail="Tenant not found")
    for k, v in data.model_dump(exclude_none=True).items():
        # Encrypt integration tokens at rest rather than storing them plaintext
        if k in ("jira_token", "servicenow_token") and v:
            setattr(t, k, encrypt_dict({"t": v}))
        else:
            setattr(t, k, v)
    if data.active_framework:
        db.add(AuditLog(tenant_id=t.id, user_id=user.id, user_name=user.name,
                        action="framework_changed", entity_type="framework",
                        entity_id=t.id, details={"framework": data.active_framework}))
    await db.commit(); await db.refresh(t)
    return _serialize(t)

@router.get("/frameworks")
async def get_frameworks():
    return {k: {"name":v["name"],"short":v["short"],"description":v["description"],
                "industry":v["industry"],"color":v["color"]}
            for k,v in FRAMEWORKS.items()}

@router.get("/industry-frameworks")
async def get_industry_frameworks():
    return INDUSTRY_FRAMEWORKS

def _serialize(t: Tenant):
    return {"id":t.id,"name":t.name,"industry":t.industry,"frameworks":t.frameworks,
            "active_framework":t.active_framework,"timezone":t.timezone,
            "scan_schedule":t.scan_schedule,"onboarded":t.onboarded,
            "has_jira": bool(t.jira_url), "has_servicenow": bool(t.servicenow_url)}
