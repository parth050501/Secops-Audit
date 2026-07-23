"""
Notification preference endpoints.

  GET  /me                  -> current user's effective prefs (+ source)
  PATCH /me                 -> set/clear the current user's custom prefs
  GET  /defaults            -> tenant role defaults (admin view)
  PATCH /defaults/{role}    -> admin sets a role's default
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.notification_prefs import (
    NotificationDefault, UserNotificationPref, ROLE_DEFAULTS, NOTIFICATION_TYPES, _prefs_dict,
)
from app.services.notification_service import resolve_for_user, get_role_default

router = APIRouter()
ROLES = ["admin", "manager", "engineer", "auditor"]


class PrefsIn(BaseModel):
    custom: Optional[bool] = None
    report_ciso: Optional[bool] = None
    report_engineer: Optional[bool] = None
    report_auditor: Optional[bool] = None
    ticket_assigned: Optional[bool] = None
    ticket_status: Optional[bool] = None
    finding_critical: Optional[bool] = None


@router.get("/me")
async def my_prefs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    prefs = await resolve_for_user(db, user)
    return {"role": user.role, "prefs": {k: v for k, v in prefs.items() if k != "_source"},
            "source": prefs.get("_source"), "types": NOTIFICATION_TYPES}


@router.patch("/me")
async def set_my_prefs(data: PrefsIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pref = (await db.execute(
        select(UserNotificationPref).where(UserNotificationPref.user_id == user.id)
    )).scalar_one_or_none()
    if not pref:
        # seed from current role default so toggles start sensibly
        base = await get_role_default(db, user.tenant_id, user.role or "engineer")
        pref = UserNotificationPref(tenant_id=user.tenant_id, user_id=user.id, custom=True, **base)
        db.add(pref)
    for t in NOTIFICATION_TYPES:
        val = getattr(data, t)
        if val is not None:
            setattr(pref, t, val)
    if data.custom is not None:
        pref.custom = data.custom
    await db.commit(); await db.refresh(pref)
    return {"custom": pref.custom, "prefs": _prefs_dict(pref)}


@router.get("/defaults")
async def get_defaults(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only a tenant admin can view role defaults")
    out = {}
    for role in ROLES:
        out[role] = await get_role_default(db, user.tenant_id, role)
    return {"defaults": out, "types": NOTIFICATION_TYPES}


@router.patch("/defaults/{role}")
async def set_default(role: str, data: PrefsIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only a tenant admin can set role defaults")
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="Unknown role")
    row = (await db.execute(
        select(NotificationDefault).where(
            NotificationDefault.tenant_id == user.tenant_id, NotificationDefault.role == role)
    )).scalar_one_or_none()
    if not row:
        base = dict(ROLE_DEFAULTS.get(role, ROLE_DEFAULTS["engineer"]))
        row = NotificationDefault(tenant_id=user.tenant_id, role=role, **base)
        db.add(row)
    for t in NOTIFICATION_TYPES:
        val = getattr(data, t)
        if val is not None:
            setattr(row, t, val)
    await db.commit(); await db.refresh(row)
    return {"role": role, "prefs": _prefs_dict(row)}
