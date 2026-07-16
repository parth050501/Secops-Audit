from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_token, get_current_user
from app.models.user import User

router = APIRouter()

class LoginReq(BaseModel):
    email: str; password: str

class RegisterReq(BaseModel):
    email: str; name: str; password: str; role: str = "engineer"

@router.post("/login")
async def login(data: LoginReq, db: AsyncSession = Depends(get_db)):
    u = (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
    if not u or not verify_password(data.password, u.hashed_pw):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(u.id, u.email, u.role),
            "user": {"id":u.id,"email":u.email,"name":u.name,"role":u.role,"tenant_id":u.tenant_id}}

@router.post("/register")
async def register(data: RegisterReq, db: AsyncSession = Depends(get_db)):
    # Public self-registration is intentionally disabled. In a multi-tenant
    # compliance platform, users must be provisioned through controlled flows:
    #   - tenants are onboarded by platform admins (POST /api/platform/tenants)
    #   - users within a tenant are added by that tenant's admin (POST /api/users)
    # Allowing anyone to self-register and choose their own role is a
    # privilege-escalation risk, so this endpoint is closed.
    raise HTTPException(
        status_code=403,
        detail="Self-registration is disabled. Accounts are created by an administrator.",
    )

@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id":user.id,"email":user.email,"name":user.name,"role":user.role,"tenant_id":user.tenant_id}
