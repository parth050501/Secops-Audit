from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.tenant_guard import require_tenant_capability
from app.models.user import User
from app.models.tenant import Tenant
from app.models.connector import Connector
from app.models.event import GovernanceEvent
from app.models.audit_log import AuditLog
from app.connectors.simulator import simulate_events_for_connector
from app.frameworks.definitions import CONNECTOR_CATALOG, fields_for_connector
from app.core.encryption import encrypt_dict, decrypt_dict, mask_credentials

router = APIRouter()

class ConnectorCreate(BaseModel):
    name: str
    category: str
    connector_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    credentials: Optional[dict] = None
    collection_mode: str = "polling"
    poll_interval_sec: int = 300
    realtime: bool = True

@router.get("/catalog")
async def get_catalog(include_all: bool = False):
    # Connectors connect DIRECTLY to the platform via API (cloud, identity, SaaS,
    # SIEM, custom APIs). Internal systems (servers, databases, network devices)
    # are assessed through the on-prem Collector + agents, NOT direct connectors.
    # So the Connectors tab shows only direct-connect categories by default.
    DIRECT_CATEGORIES = {"cloud", "identity", "siem", "custom"}
    COLLECTOR_CATEGORIES = {"server", "database", "network"}

    out = []
    for c in CONNECTOR_CATALOG:
        cat = c.get("category")
        delivery = "collector" if cat in COLLECTOR_CATEGORIES else "direct"
        entry = {**c, "fields": fields_for_connector(c["type"]), "delivery": delivery}
        if include_all or delivery == "direct":
            out.append(entry)
    return out

@router.get("")
async def list_connectors(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Connector).where(Connector.tenant_id == user.tenant_id))
    return [_ser(c) for c in result.scalars().all()]

@router.post("")
async def add_connector(
    data: ConnectorCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    user: User = Depends(require_tenant_capability("manage_connectors")),
    db: AsyncSession = Depends(get_db),
):
    payload = data.model_dump()
    raw_creds = payload.pop("credentials", None)
    c = Connector(**payload, tenant_id=user.tenant_id, status="connected", last_seen=datetime.utcnow())
    # Encrypt credentials at rest — never store partner secrets in plaintext
    c.credentials = {"_enc": encrypt_dict(raw_creds)} if raw_creds else None
    db.add(c)
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                    action="connector_added", entity_type="connector",
                    details={"name":data.name,"type":data.connector_type,"category":data.category}))
    await db.commit(); await db.refresh(c)
    # Auto-run initial scan in background
    background_tasks.add_task(_run_scan, c.id, user.tenant_id, request)
    return _ser(c)

@router.post("/{connector_id}/scan")
async def trigger_scan(
    connector_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    user: User = Depends(require_tenant_capability("manage_connectors")),
    db: AsyncSession = Depends(get_db),
):
    c = (await db.execute(select(Connector).where(Connector.id == connector_id, Connector.tenant_id == user.tenant_id))).scalar_one_or_none()
    if not c: raise HTTPException(status_code=404, detail="Connector not found")
    background_tasks.add_task(_run_scan, connector_id, user.tenant_id, request)
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                    action="scan_triggered", entity_type="connector", entity_id=connector_id,
                    details={"connector_name":c.name}))
    await db.commit()
    return {"message": f"Scan triggered for {c.name}"}

@router.delete("/{connector_id}")
async def remove_connector(connector_id: int, user: User = Depends(require_tenant_capability("manage_connectors")), db: AsyncSession = Depends(get_db)):
    c = (await db.execute(select(Connector).where(Connector.id == connector_id, Connector.tenant_id == user.tenant_id))).scalar_one_or_none()
    if not c: raise HTTPException(status_code=404, detail="Not found")
    await db.delete(c); await db.commit()
    return {"message": "Removed"}

async def _run_scan(connector_id: int, tenant_id: int, request: Request):
    """Background task: simulate pulling data and generating events."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        c = (await db.execute(select(Connector).where(Connector.id == connector_id))).scalar_one_or_none()
        if not c: return
        t = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
        framework = t.active_framework if t else "pci_dss"

        # Real connectors: Prowler (AWS/Azure/GCP) + OpenSCAP (linux server) +
        # Palo Alto firewall config assessment; simulator for everything else.
        REAL_CLOUD = {"aws", "azure", "gcp"}
        REAL_SERVER = {"linux", "windows_server"}
        REAL_NETWORK = {"paloalto"}
        REAL_DB = {"postgres"}
        if c.connector_type in REAL_CLOUD or c.connector_type in REAL_SERVER or c.connector_type in REAL_NETWORK or c.connector_type in REAL_DB:
            c.status = "scanning"
            await db.commit()
            try:
                creds = decrypt_dict((c.credentials or {}).get('_enc')) or {}
                if c.connector_type == "aws":
                    from app.connectors.prowler_aws import run_prowler_scan
                    events = run_prowler_scan(creds, tenant_id, connector_id)
                elif c.connector_type == "azure":
                    from app.connectors.prowler_azure import run_prowler_azure_scan
                    events = run_prowler_azure_scan(creds, tenant_id, connector_id)
                elif c.connector_type == "gcp":
                    from app.connectors.prowler_gcp import run_prowler_gcp_scan
                    events = run_prowler_gcp_scan(creds, tenant_id, connector_id)
                elif c.connector_type == "linux":
                    from app.connectors.openscap_server import run_openscap_scan
                    # tag findings with the tenant's active framework by default
                    creds.setdefault("framework", framework)
                    events = run_openscap_scan(creds, tenant_id, connector_id)
                elif c.connector_type == "windows_server":
                    from app.connectors.windows_server import run_windows_scan
                    creds.setdefault("framework", framework)
                    events = run_windows_scan(creds, tenant_id, connector_id)
                elif c.connector_type == "postgres":
                    from app.connectors.postgres_db import run_postgres_scan
                    creds.setdefault("framework", framework)
                    events = run_postgres_scan(creds, tenant_id, connector_id)
                else:  # paloalto — firewall config assessment
                    from app.connectors.paloalto_fw import run_paloalto_scan
                    creds.setdefault("framework", framework)
                    events = run_paloalto_scan(creds, tenant_id, connector_id)
                c.last_error = None
                # Clear prior OPEN, un-ticketed events so a re-scan reflects current
                # state rather than accumulating duplicates. Ticketed events preserved.
                prior = (await db.execute(
                    select(GovernanceEvent).where(
                        GovernanceEvent.connector_id == connector_id,
                        GovernanceEvent.status == "open",
                    )
                )).scalars().all()
                for p in prior:
                    await db.delete(p)
            except Exception as e:
                c.status = "error"
                c.last_error = str(e)[:500]
                await db.commit()
                return
        else:
            events = simulate_events_for_connector(c.connector_type, connector_id, tenant_id, framework)
        new_events = []
        for ev in events:
            ge = GovernanceEvent(**ev)
            db.add(ge)
            new_events.append(ge)

        c.last_seen = datetime.utcnow()
        if c.status == "scanning":
            c.status = "connected"
        await db.commit()

        # Broadcast via WebSocket
        try:
            manager = request.app.state.manager
            for ev in new_events:
                await manager.broadcast_to_tenant(tenant_id, {
                    "type": "governance_event",
                    "event": {
                        "id": ev.id,
                        "title": ev.title,
                        "severity": ev.severity,
                        "category": ev.category,
                        "connector_id": connector_id,
                        "occurred_at": ev.occurred_at.isoformat() if ev.occurred_at else None,
                    }
                })
        except Exception:
            pass

def _ser(c: Connector):
    # Never return raw credentials — only a masked, display-safe view
    masked = {}
    try:
        if c.credentials and c.credentials.get("_enc"):
            masked = mask_credentials(decrypt_dict(c.credentials["_enc"]))
    except Exception:
        masked = {}
    return {"id":c.id,"name":c.name,"category":c.category,"connector_type":c.connector_type,
            "host":c.host,"status":c.status,"realtime":c.realtime,
            "collection_mode":c.collection_mode,"poll_interval_sec":c.poll_interval_sec,
            "last_error":c.last_error,
            "credentials_masked":masked,
            "last_seen":c.last_seen.isoformat() if c.last_seen else None}
