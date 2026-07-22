from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.platform_security import get_platform_admin, create_platform_token, require_capability
from app.core.security import verify_password, create_token
from app.models.platform import PlatformAdmin, TenantBilling, PLAN_DEFAULTS
from app.models.tenant import Tenant
from app.models.user import User
from app.models.connector import Connector
from app.models.event import GovernanceEvent
from app.models.ticket import Ticket
from app.models.ai_usage import AIUsage, AICreditsBalance

router = APIRouter()


# ── Auth ──
class PlatformLogin(BaseModel):
    email: str
    password: str


@router.post("/login")
async def platform_login(data: PlatformLogin, db: AsyncSession = Depends(get_db)):
    admin = (await db.execute(select(PlatformAdmin).where(PlatformAdmin.email == data.email))).scalar_one_or_none()
    if not admin or not verify_password(data.password, admin.hashed_pw):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    admin.last_login = datetime.utcnow()
    await db.commit()
    return {"token": create_platform_token(admin.id, admin.email, admin.role),
            "admin": {"id": admin.id, "email": admin.email, "name": admin.name}}


@router.get("/me")
async def platform_me(admin: PlatformAdmin = Depends(get_platform_admin)):
    return {"id": admin.id, "email": admin.email, "name": admin.name}


# ── Overview / Metrics ──
@router.get("/overview")
async def overview(admin: PlatformAdmin = Depends(get_platform_admin), db: AsyncSession = Depends(get_db)):
    tenants = (await db.execute(select(Tenant))).scalars().all()
    billings = (await db.execute(select(TenantBilling))).scalars().all()
    bill_map = {b.tenant_id: b for b in billings}

    total_mrr = sum(b.mrr for b in billings if b.status == "active")
    active = sum(1 for b in billings if b.status == "active")
    trial = sum(1 for b in billings if b.status == "trial")
    suspended = sum(1 for b in billings if b.status == "suspended")

    users = (await db.execute(select(func.count(User.id)))).scalar()
    connectors = (await db.execute(select(func.count(Connector.id)))).scalar()
    events = (await db.execute(select(func.count(GovernanceEvent.id)))).scalar()
    tickets = (await db.execute(select(func.count(Ticket.id)))).scalar()

    # AI revenue (credits consumed * approx price)
    ai_usage = (await db.execute(select(AIUsage))).scalars().all()
    ai_credits_used = sum(u.credits_used for u in ai_usage)

    # Plan distribution
    plans = {"starter": 0, "professional": 0, "enterprise": 0}
    for b in billings:
        plans[b.plan] = plans.get(b.plan, 0) + 1

    return {
        "total_tenants": len(tenants),
        "active": active, "trial": trial, "suspended": suspended,
        "total_mrr": total_mrr,
        "arr": total_mrr * 12,
        "total_users": users,
        "total_connectors": connectors,
        "total_events": events,
        "total_tickets": tickets,
        "ai_credits_consumed": ai_credits_used,
        "plan_distribution": plans,
    }


# ── Tenant management ──
@router.get("/tenants")
async def list_tenants(admin: PlatformAdmin = Depends(get_platform_admin), db: AsyncSession = Depends(get_db)):
    tenants = (await db.execute(select(Tenant))).scalars().all()
    billings = {b.tenant_id: b for b in (await db.execute(select(TenantBilling))).scalars().all()}

    result = []
    for t in tenants:
        b = billings.get(t.id)
        users = (await db.execute(select(func.count(User.id)).where(User.tenant_id == t.id))).scalar()
        connectors = (await db.execute(select(func.count(Connector.id)).where(Connector.tenant_id == t.id))).scalar()
        events = (await db.execute(select(func.count(GovernanceEvent.id)).where(GovernanceEvent.tenant_id == t.id))).scalar()
        credits = (await db.execute(select(AICreditsBalance).where(AICreditsBalance.tenant_id == t.id))).scalar_one_or_none()

        result.append({
            "id": t.id, "name": t.name, "industry": t.industry,
            "active_framework": t.active_framework, "frameworks": t.frameworks,
            "onboarded": t.onboarded,
            "plan": b.plan if b else "none",
            "mrr": b.mrr if b else 0,
            "status": b.status if b else "active",
            "users": users, "connectors": connectors, "events": events,
            "ai_credits_used": credits.credits_used if credits else 0,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return result


class OnboardTenant(BaseModel):
    name: str
    industry: str = "technology"
    active_framework: str = "soc2"
    frameworks: list = None
    plan: str = "starter"
    admin_name: str
    admin_email: str
    admin_password: str


@router.post("/tenants")
async def onboard_tenant(data: OnboardTenant, admin: PlatformAdmin = Depends(require_capability("manage_tenants")),
                         db: AsyncSession = Depends(get_db)):
    """Onboard a new client: create the tenant, its first admin user, and billing.
    This is the MSSP 'add a client' action."""
    from app.core.security import hash_password
    from app.models.audit_log import AuditLog

    # Guard: email must be unique across the platform
    existing = (await db.execute(select(User).where(User.email == data.admin_email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="A user with that email already exists")
    if data.plan not in PLAN_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Plan must be one of {list(PLAN_DEFAULTS)}")

    frameworks = data.frameworks or [data.active_framework]
    t = Tenant(name=data.name, industry=data.industry, active_framework=data.active_framework,
               frameworks=frameworks, onboarded=True)
    db.add(t); await db.flush()

    # First admin user for the client
    user = User(email=data.admin_email, name=data.admin_name, role="admin",
                hashed_pw=hash_password(data.admin_password), tenant_id=t.id)
    db.add(user)

    # Billing on the chosen plan
    defaults = PLAN_DEFAULTS[data.plan]
    db.add(TenantBilling(tenant_id=t.id, plan=data.plan, status="active",
                         mrr=defaults["mrr"], seats=defaults["seats"],
                         connectors_limit=defaults["connectors_limit"],
                         ai_credits_monthly=defaults["ai_credits_monthly"],
                         billing_email=data.admin_email))

    db.add(AuditLog(tenant_id=t.id, user_id=None, user_name=f"[PLATFORM] {admin.name}",
                    action="tenant_onboarded", entity_type="tenant", entity_id=t.id,
                    details={"name": data.name, "plan": data.plan, "admin": data.admin_email}))
    await db.commit(); await db.refresh(t)
    return {"id": t.id, "name": t.name, "plan": data.plan,
            "admin_email": data.admin_email, "message": f"Tenant '{t.name}' onboarded"}


@router.get("/tenants/{tenant_id}")
async def tenant_detail(tenant_id: int, admin: PlatformAdmin = Depends(get_platform_admin), db: AsyncSession = Depends(get_db)):
    t = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    b = (await db.execute(select(TenantBilling).where(TenantBilling.tenant_id == tenant_id))).scalar_one_or_none()
    users = (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
    connectors = (await db.execute(select(Connector).where(Connector.tenant_id == tenant_id))).scalars().all()
    tickets = (await db.execute(select(Ticket).where(Ticket.tenant_id == tenant_id))).scalars().all()
    usage = (await db.execute(select(AIUsage).where(AIUsage.tenant_id == tenant_id).order_by(AIUsage.timestamp.desc()).limit(20))).scalars().all()

    return {
        "tenant": {"id": t.id, "name": t.name, "industry": t.industry,
                   "frameworks": t.frameworks, "active_framework": t.active_framework,
                   "created_at": t.created_at.isoformat() if t.created_at else None},
        "billing": {"plan": b.plan, "mrr": b.mrr, "status": b.status, "seats": b.seats,
                    "connectors_limit": b.connectors_limit} if b else None,
        "users": [{"id": u.id, "email": u.email, "name": u.name, "role": u.role} for u in users],
        "connectors": [{"id": c.id, "name": c.name, "type": c.connector_type, "status": c.status} for c in connectors],
        "ticket_count": len(tickets),
        "recent_ai_usage": [{"operation": u.operation, "user": u.user_name, "credits": u.credits_used,
                             "timestamp": u.timestamp.isoformat()} for u in usage],
    }


class PlanUpdate(BaseModel):
    plan: str


@router.patch("/tenants/{tenant_id}/plan")
async def update_plan(tenant_id: int, data: PlanUpdate, admin: PlatformAdmin = Depends(require_capability("manage_billing")), db: AsyncSession = Depends(get_db)):
    if data.plan not in PLAN_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"Plan must be one of {list(PLAN_DEFAULTS)}")
    b = (await db.execute(select(TenantBilling).where(TenantBilling.tenant_id == tenant_id))).scalar_one_or_none()
    if not b:
        b = TenantBilling(tenant_id=tenant_id)
        db.add(b)
    defaults = PLAN_DEFAULTS[data.plan]
    b.plan = data.plan
    b.mrr = defaults["mrr"]
    b.seats = defaults["seats"]
    b.connectors_limit = defaults["connectors_limit"]
    b.ai_credits_monthly = defaults["ai_credits_monthly"]
    await db.commit()
    return {"tenant_id": tenant_id, "plan": b.plan, "mrr": b.mrr}


class StatusUpdate(BaseModel):
    status: str


@router.patch("/tenants/{tenant_id}/status")
async def update_status(tenant_id: int, data: StatusUpdate, admin: PlatformAdmin = Depends(require_capability("manage_tenants")), db: AsyncSession = Depends(get_db)):
    if data.status not in ("active", "trial", "suspended", "churned"):
        raise HTTPException(status_code=400, detail="Invalid status")
    b = (await db.execute(select(TenantBilling).where(TenantBilling.tenant_id == tenant_id))).scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="No billing record")
    b.status = data.status
    await db.commit()
    return {"tenant_id": tenant_id, "status": b.status}


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(tenant_id: int, admin: PlatformAdmin = Depends(require_capability("manage_tenants")), db: AsyncSession = Depends(get_db)):
    t = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    # Cascade delete tenant data
    for model in (GovernanceEvent, Ticket, Connector):
        rows = (await db.execute(select(model).where(model.tenant_id == tenant_id))).scalars().all()
        for r in rows:
            await db.delete(r)
    await db.delete(t)
    await db.commit()
    return {"message": f"Tenant {tenant_id} and all data deleted"}


# ── Impersonation (support) ──
@router.post("/tenants/{tenant_id}/impersonate")
async def impersonate(tenant_id: int, admin: PlatformAdmin = Depends(require_capability("impersonate")), db: AsyncSession = Depends(get_db)):
    """Issue a regular tenant-user token for support access. Logs the action."""
    # Prefer an admin user in that tenant; fall back to any user. Use first match
    # (a tenant can legitimately have several users / several admins).
    user = (await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.role == "admin")
        .order_by(User.id).limit(1)
    )).scalars().first()
    if not user:
        user = (await db.execute(
            select(User).where(User.tenant_id == tenant_id)
            .order_by(User.id).limit(1)
        )).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="No users in this tenant to impersonate")

    from app.models.audit_log import AuditLog
    db.add(AuditLog(tenant_id=tenant_id, user_id=None, user_name=f"[PLATFORM] {admin.name}",
                    action="impersonation_started", entity_type="tenant", entity_id=tenant_id,
                    details={"platform_admin": admin.email, "impersonated_user": user.email}))
    await db.commit()

    token = create_token(user.id, user.email, user.role)
    return {"token": token, "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role},
            "impersonating": True, "tenant_id": tenant_id}


# ── Internal team management (platform staff) ──
from app.core.platform_security import require_capability as _rc
from app.models.platform import PLATFORM_ROLES


class TeamMemberIn(BaseModel):
    name: str
    email: str
    password: str
    role: str = "analyst"


@router.get("/team")
async def list_team(admin: PlatformAdmin = Depends(get_platform_admin), db: AsyncSession = Depends(get_db)):
    """Any platform staff can view the team roster."""
    members = (await db.execute(select(PlatformAdmin).order_by(PlatformAdmin.created_at))).scalars().all()
    return [{"id": m.id, "name": m.name, "email": m.email, "role": m.role,
             "is_active": m.is_active,
             "last_login": m.last_login.isoformat() if m.last_login else None}
            for m in members]


@router.post("/team")
async def add_team_member(data: TeamMemberIn,
                          admin: PlatformAdmin = Depends(require_capability("manage_team")),
                          db: AsyncSession = Depends(get_db)):
    from app.core.security import hash_password
    if data.role not in PLATFORM_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of {PLATFORM_ROLES}")
    # Only a super_admin may create another super_admin
    if data.role == "super_admin" and admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only a super-admin can create another super-admin")
    existing = (await db.execute(select(PlatformAdmin).where(PlatformAdmin.email == data.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="A platform user with that email already exists")
    m = PlatformAdmin(name=data.name, email=data.email, role=data.role,
                      hashed_pw=hash_password(data.password))
    db.add(m); await db.commit(); await db.refresh(m)
    return {"id": m.id, "name": m.name, "email": m.email, "role": m.role}


class TeamRoleUpdate(BaseModel):
    role: str


@router.patch("/team/{member_id}")
async def update_team_role(member_id: int, data: TeamRoleUpdate,
                           admin: PlatformAdmin = Depends(require_capability("manage_team")),
                           db: AsyncSession = Depends(get_db)):
    if data.role not in PLATFORM_ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of {PLATFORM_ROLES}")
    if data.role == "super_admin" and admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only a super-admin can grant super-admin")
    m = (await db.execute(select(PlatformAdmin).where(PlatformAdmin.id == member_id))).scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Team member not found")
    # Prevent removing the last super-admin's powers
    if m.role == "super_admin" and data.role != "super_admin":
        supers = (await db.execute(select(PlatformAdmin).where(PlatformAdmin.role == "super_admin", PlatformAdmin.is_active == True))).scalars().all()
        if len(supers) <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last super-admin")
    m.role = data.role
    await db.commit()
    return {"id": m.id, "role": m.role}


@router.delete("/team/{member_id}")
async def remove_team_member(member_id: int,
                             admin: PlatformAdmin = Depends(require_capability("manage_team")),
                             db: AsyncSession = Depends(get_db)):
    if member_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself")
    m = (await db.execute(select(PlatformAdmin).where(PlatformAdmin.id == member_id))).scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Team member not found")
    if m.role == "super_admin":
        supers = (await db.execute(select(PlatformAdmin).where(PlatformAdmin.role == "super_admin", PlatformAdmin.is_active == True))).scalars().all()
        if len(supers) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last super-admin")
    await db.delete(m); await db.commit()
    return {"message": "Team member removed"}


# ── Platform-wide email / SMTP settings (super-admin) ──
from app.models.platform_settings import PlatformSettings
from app.core.encryption import encrypt_value
from app.services import email_service


async def _get_or_create_settings(db):
    s = (await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))).scalar_one_or_none()
    if not s:
        s = PlatformSettings(id=1)
        db.add(s); await db.commit(); await db.refresh(s)
    return s


def _ser_settings(s: PlatformSettings) -> dict:
    # Never return the password; only whether one is set.
    return {
        "smtp_host": s.smtp_host, "smtp_port": s.smtp_port, "smtp_user": s.smtp_user,
        "smtp_use_tls": s.smtp_use_tls, "email_from": s.email_from,
        "email_from_name": s.email_from_name, "email_enabled": s.email_enabled,
        "smtp_password_set": bool(s.smtp_password_enc),
    }


class SmtpSettingsIn(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None      # plaintext in; stored encrypted. Blank = leave unchanged
    smtp_use_tls: Optional[bool] = None
    email_from: Optional[str] = None
    email_from_name: Optional[str] = None
    email_enabled: Optional[bool] = None


@router.get("/settings/email")
async def get_email_settings(admin: PlatformAdmin = Depends(get_platform_admin), db: AsyncSession = Depends(get_db)):
    s = await _get_or_create_settings(db)
    return _ser_settings(s)


@router.patch("/settings/email")
async def update_email_settings(data: SmtpSettingsIn,
                                admin: PlatformAdmin = Depends(require_capability("manage_tenants")),
                                db: AsyncSession = Depends(get_db)):
    s = await _get_or_create_settings(db)
    for field in ("smtp_host", "smtp_port", "smtp_user", "smtp_use_tls",
                  "email_from", "email_from_name", "email_enabled"):
        val = getattr(data, field)
        if val is not None:
            setattr(s, field, val)
    # password only if a non-empty value provided
    if data.smtp_password:
        s.smtp_password_enc = encrypt_value(data.smtp_password)
    await db.commit(); await db.refresh(s)
    return _ser_settings(s)


class TestEmailIn(BaseModel):
    to_address: str


@router.post("/settings/email/test")
async def test_email(data: TestEmailIn,
                     admin: PlatformAdmin = Depends(require_capability("manage_tenants")),
                     db: AsyncSession = Depends(get_db)):
    ok, message = await email_service.send_test_email(data.to_address)
    return {"ok": ok, "message": message}


# ── Editable tenant info (super-admin) ──
class TenantEditIn(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    active_framework: Optional[str] = None
    custom_domain: Optional[str] = None
    timezone: Optional[str] = None


@router.patch("/tenants/{tenant_id}/info")
async def edit_tenant_info(tenant_id: int, data: TenantEditIn,
                           admin: PlatformAdmin = Depends(require_capability("manage_tenants")),
                           db: AsyncSession = Depends(get_db)):
    t = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    for field in ("name", "industry", "active_framework", "custom_domain", "timezone"):
        val = getattr(data, field)
        if val is not None:
            setattr(t, field, val.strip() if isinstance(val, str) else val)
    await db.commit()
    return {"id": t.id, "name": t.name, "industry": t.industry,
            "active_framework": t.active_framework, "custom_domain": t.custom_domain,
            "timezone": t.timezone}
