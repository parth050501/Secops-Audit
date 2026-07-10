"""
Collector management API (used by platform staff / tenant admins via the console).

CodeCore staff register collectors during customer deployment. The registration
returns the token ONCE — it is copied into the collector installer and never
shown again (only its hash is stored).
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.platform_security import get_platform_admin, require_capability
from app.core.collector_security import generate_collector_token, hash_token
from app.core.tenant_guard import tenant_query
from app.models.collector import Collector, Agent, ScanJob
from app.models.user import User
from app.models.platform import PlatformAdmin

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# TENANT-ADMIN action: a tenant admin registers their own CCE.
# The token is bound to THEIR tenant (derived from their session), shown once.
# Restricted to the tenant admin role. Logged in the audit trail.
# ─────────────────────────────────────────────────────────────
class TenantRegisterCollectorIn(BaseModel):
    name: str            # e.g. "NTIPLCCE1"


@router.post("/register")
async def tenant_register_collector(data: TenantRegisterCollectorIn,
                                    user: User = Depends(get_current_user),
                                    db: AsyncSession = Depends(get_db)):
    """A tenant admin registers a collector for THEIR tenant. Returns token once."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only a tenant admin can add a collector")
    from app.models.audit_log import AuditLog
    token = generate_collector_token()
    c = Collector(
        tenant_id=user.tenant_id, name=data.name,
        token_hash=hash_token(token), token_prefix=token[:12],
        status="pending", created_by=user.name,
    )
    db.add(c)
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                    action="collector_registered", entity_type="collector",
                    details={"name": data.name}))
    await db.commit(); await db.refresh(c)
    return {
        "id": c.id, "name": c.name, "tenant_id": c.tenant_id,
        "token": token,
        "note": "Store this token securely. It will not be shown again. "
                "Enter it (with the platform URL) when deploying the CCE OVA.",
    }


# ─────────────────────────────────────────────────────────────
# PLATFORM-STAFF actions (register collectors during deployment)
# ─────────────────────────────────────────────────────────────
class RegisterCollectorIn(BaseModel):
    tenant_id: int
    name: str            # e.g. "NTIPLCCE1"


@router.post("/platform/register")
async def register_collector(data: RegisterCollectorIn,
                             admin: PlatformAdmin = Depends(require_capability("manage_tenants")),
                             db: AsyncSession = Depends(get_db)):
    """Register a new collector for a tenant. Returns the token ONCE."""
    token = generate_collector_token()
    c = Collector(
        tenant_id=data.tenant_id, name=data.name,
        token_hash=hash_token(token), token_prefix=token[:12],
        status="pending", created_by=admin.name,
    )
    db.add(c); await db.commit(); await db.refresh(c)
    return {
        "id": c.id, "name": c.name, "tenant_id": c.tenant_id,
        "token": token,   # shown once — copy into the collector installer now
        "note": "Store this token securely. It will not be shown again.",
    }


@router.get("/platform/all")
async def list_all_collectors(admin: PlatformAdmin = Depends(get_platform_admin),
                              db: AsyncSession = Depends(get_db)):
    """All collectors across all tenants (platform view)."""
    rows = (await db.execute(select(Collector))).scalars().all()
    return [_ser_collector(c) for c in rows]


# ─────────────────────────────────────────────────────────────
# TENANT view (a tenant sees ITS OWN collectors + status)
# ─────────────────────────────────────────────────────────────
@router.get("")
async def list_my_collectors(user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(tenant_query(Collector, user))).scalars().all()
    return [_ser_collector(c) for c in rows]


@router.delete("/{collector_id}")
async def delete_collector(collector_id: int,
                           user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    """Delete a collector (and its agents) the tenant no longer wants."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only a tenant admin can delete a collector")
    c = (await db.execute(
        tenant_query(Collector, user).where(Collector.id == collector_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Collector not found")
    # remove its agents first
    agents = (await db.execute(
        tenant_query(Agent, user).where(Agent.collector_id == collector_id)
    )).scalars().all()
    for a in agents:
        await db.delete(a)
    await db.delete(c)
    await db.commit()
    return {"deleted": True, "id": collector_id, "agents_removed": len(agents)}


@router.get("/agents")
async def list_my_agents(user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(tenant_query(Agent, user))).scalars().all()
    # map collector_id -> name for display
    collectors = (await db.execute(tenant_query(Collector, user))).scalars().all()
    cname = {c.id: c.name for c in collectors}
    return [_ser_agent(a, cname.get(a.collector_id)) for a in rows]


# ── On-demand scan ("Scan Now") — queues a job the collector will poll ──
class ScanNowIn(BaseModel):
    system_type: str
    target: Optional[str] = None
    collector_id: Optional[int] = None
    agent_id: Optional[int] = None


@router.post("/scan-now")
async def scan_now(data: ScanNowIn, user: User = Depends(get_current_user),
                   db: AsyncSession = Depends(get_db)):
    """Queue an on-demand scan job for this tenant. The collector picks it up on
    its next poll (results return asynchronously — not instant, by design, since
    the platform cannot reach into the customer network)."""
    # Resolve tenant's active framework for mapping
    from app.models.tenant import Tenant
    t = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one_or_none()
    framework = t.active_framework if t else None

    job = ScanJob(
        tenant_id=user.tenant_id, collector_id=data.collector_id, agent_id=data.agent_id,
        system_type=data.system_type, target=data.target, framework=framework,
        status="pending", origin="on_demand",
    )
    db.add(job); await db.commit(); await db.refresh(job)
    return {"job_id": job.id, "status": "queued",
            "note": "The collector will run this on its next poll; findings appear when complete."}


@router.get("/jobs")
async def list_my_jobs(user: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        tenant_query(ScanJob, user).order_by(ScanJob.created_at.desc())
    )).scalars().all()
    return [_ser_job(j) for j in rows[:100]]


# ── serializers ──
def _ser_collector(c: Collector) -> dict:
    return {"id": c.id, "name": c.name, "tenant_id": c.tenant_id,
            "status": c.derived_status(), "version": c.version,
            "last_seen": c.last_seen.isoformat() if c.last_seen else None,
            "token_prefix": c.token_prefix, "created_by": c.created_by}


def _ser_agent(a: Agent, collector_name: str = None) -> dict:
    return {"id": a.id, "name": a.name, "system_type": a.system_type,
            "target": a.target, "schedule": a.schedule, "status": a.derived_status(),
            "collector_id": a.collector_id, "collector_name": collector_name,
            "last_scan_at": a.last_scan_at.isoformat() if a.last_scan_at else None,
            "last_result": a.last_result,
            "last_seen": a.last_seen.isoformat() if a.last_seen else None}


def _ser_job(j: ScanJob) -> dict:
    return {"id": j.id, "system_type": j.system_type, "target": j.target,
            "status": j.status, "origin": j.origin,
            "findings_count": j.findings_count,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            "error": j.error}
