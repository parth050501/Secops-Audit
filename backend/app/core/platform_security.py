from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models.platform import PlatformAdmin

platform_bearer = HTTPBearer()


# ── Capability matrix: which platform roles can do what ──
# Each capability maps to the set of roles allowed to perform it.
CAPABILITIES = {
    "view":            {"super_admin", "admin", "analyst", "read_only"},
    "work_in_tenant":  {"super_admin", "admin", "analyst"},   # scans, findings, tickets
    "impersonate":     {"super_admin", "admin", "analyst"},
    "manage_tenants":  {"super_admin", "admin"},              # onboard / delete tenant
    "manage_team":     {"super_admin", "admin"},              # add / remove platform users
    "manage_billing":  {"super_admin"},                       # change plans / billing — super only
}


def create_platform_token(admin_id: int, email: str, role: str = "super_admin") -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": str(admin_id), "email": email, "role": role,
         "scope": "platform_admin", "exp": exp},
        settings.jwt_secret, algorithm=settings.jwt_algorithm,
    )


async def get_platform_admin(
    creds: HTTPAuthorizationCredentials = Depends(platform_bearer),
    db: AsyncSession = Depends(get_db),
) -> PlatformAdmin:
    """Authenticate any active platform staff member (any role)."""
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("scope") != "platform_admin":
            raise HTTPException(status_code=403, detail="Platform access required")
        admin_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid platform token")
    admin = (await db.execute(select(PlatformAdmin).where(PlatformAdmin.id == admin_id))).scalar_one_or_none()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Platform admin not found")
    return admin


def require_capability(capability: str):
    """Dependency factory: allow only platform roles that have `capability`.

    Usage:
        @router.post("/tenants")
        async def onboard(..., admin = Depends(require_capability("manage_tenants"))):
    """
    allowed = CAPABILITIES.get(capability, set())

    async def _checker(admin: PlatformAdmin = Depends(get_platform_admin)) -> PlatformAdmin:
        if admin.role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Your role ({admin.role}) cannot perform this action",
            )
        return admin

    return _checker
