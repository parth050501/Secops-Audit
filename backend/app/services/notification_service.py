"""
Notification preference resolution.

Resolves what a given user effectively receives:
  user has custom prefs (custom=True)?  -> use them
  else                                  -> use tenant's admin-set role default
  else (admin never customized)         -> use built-in ROLE_DEFAULTS

Also provides recipient lookup: "who in this tenant should receive notification
type X" — used by report delivery and event notifications.
"""
from sqlalchemy import select
from app.models.user import User
from app.models.notification_prefs import (
    NotificationDefault, UserNotificationPref, ROLE_DEFAULTS, NOTIFICATION_TYPES, _prefs_dict,
)


async def get_role_default(db, tenant_id: int, role: str) -> dict:
    row = (await db.execute(
        select(NotificationDefault).where(
            NotificationDefault.tenant_id == tenant_id, NotificationDefault.role == role)
    )).scalar_one_or_none()
    if row:
        return _prefs_dict(row)
    return dict(ROLE_DEFAULTS.get(role, ROLE_DEFAULTS["engineer"]))


async def resolve_for_user(db, user: User) -> dict:
    """Effective prefs for one user (custom override or role default)."""
    pref = (await db.execute(
        select(UserNotificationPref).where(UserNotificationPref.user_id == user.id)
    )).scalar_one_or_none()
    if pref and pref.custom:
        return {**_prefs_dict(pref), "_source": "custom"}
    d = await get_role_default(db, user.tenant_id, user.role or "engineer")
    return {**d, "_source": "role_default"}


async def recipients_for(db, tenant_id: int, notif_type: str) -> list:
    """All (user) recipients in a tenant who should receive a given notif type,
    honoring per-user overrides. Returns list of User objects with an email."""
    if notif_type not in NOTIFICATION_TYPES:
        return []
    users = (await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.is_active == True)
    )).scalars().all()
    out = []
    for u in users:
        if not u.email:
            continue
        prefs = await resolve_for_user(db, u)
        if prefs.get(notif_type):
            out.append(u)
    return out
