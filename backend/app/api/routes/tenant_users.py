"""
Tenant-level user management.

Lets a tenant ADMIN manage users within their own tenant — add team members,
set their role (admin / engineer / manager / auditor), and remove them. All
strictly scoped to the caller's tenant; a tenant admin can never touch another
tenant's users.

Client roles:
  admin    — full access within the tenant, incl. managing users
  manager  — review/approve tickets, manage compliance workflow
  engineer — work on findings/tickets
  auditor  — READ-ONLY access to the tenant's compliance data & reports
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.core.tenant_guard import tenant_query, get_owned_or_404
from app.models.user import User
from app.models.audit_log import AuditLog

router = APIRouter()

TENANT_ROLES = ["admin", "manager", "engineer", "auditor"]


def _require_tenant_admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only a tenant admin can manage users")


@router.get("")
async def list_users(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List users in the caller's tenant. Any tenant member can view the roster."""
    rows = (await db.execute(tenant_query(User, user).order_by(User.id))).scalars().all()
    return [{"id": u.id, "name": u.name, "email": u.email, "role": u.role} for u in rows]


class TenantUserIn(BaseModel):
    name: str
    email: str
    password: str
    role: str = "engineer"


@router.post("")
async def add_user(data: TenantUserIn, user: User = Depends(get_current_user),
                   db: AsyncSession = Depends(get_db)):
    _require_tenant_admin(user)
    if data.role not in TENANT_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of {TENANT_ROLES}")
    existing = (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="A user with that email already exists")
    u = User(name=data.name, email=data.email, role=data.role,
             hashed_pw=hash_password(data.password), tenant_id=user.tenant_id)
    db.add(u)
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                    action="user_added", entity_type="user",
                    details={"email": data.email, "role": data.role}))
    await db.commit(); await db.refresh(u)
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}


class RoleUpdate(BaseModel):
    role: str


@router.patch("/{user_id}")
async def update_user_role(user_id: int, data: RoleUpdate, user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    _require_tenant_admin(user)
    if data.role not in TENANT_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of {TENANT_ROLES}")
    target = await get_owned_or_404(db, User, user_id, user, "User not found")
    # Don't allow removing the last admin
    if target.role == "admin" and data.role != "admin":
        admins = (await db.execute(
            tenant_query(User, user).where(User.role == "admin")
        )).scalars().all()
        if len(admins) <= 1:
            raise HTTPException(status_code=400, detail="Cannot change the role of the last admin")
    target.role = data.role
    await db.commit()
    return {"id": target.id, "role": target.role}


@router.delete("/{user_id}")
async def remove_user(user_id: int, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    _require_tenant_admin(user)
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself")
    target = await get_owned_or_404(db, User, user_id, user, "User not found")
    if target.role == "admin":
        admins = (await db.execute(
            tenant_query(User, user).where(User.role == "admin")
        )).scalars().all()
        if len(admins) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last admin")
    await db.delete(target)
    await db.commit()
    return {"message": "User removed"}
