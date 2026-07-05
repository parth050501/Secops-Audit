"""
Collector-facing API (used by the deployed collector, authenticated by token).

Endpoints:
  POST /api/collector/heartbeat        — liveness + report version
  GET  /api/collector/jobs             — poll for pending scan jobs (this tenant only)
  POST /api/collector/results          — submit raw scan output for a job

The tenant is ALWAYS derived from the collector's token (see
authenticate_collector). Nothing here trusts a tenant id from the request body.

The ingestion endpoint is the "type-routed core": it receives raw scan output
tagged with a system_type, routes to the matching parser (the existing connector
modules), and creates GovernanceEvents stamped with the derived tenant_id.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.collector_security import authenticate_collector
from app.models.collector import Collector, Agent, ScanJob
from app.models.event import GovernanceEvent

router = APIRouter()


# ── Map a system_type to the parser that handles its raw output ──
# Each parser takes (raw_data, tenant_id, connector_id, framework_hint) and
# returns a list of GovernanceEvent dicts. These are the modules we already built.
def _parse(system_type: str, raw: Any, tenant_id: int, ref_id: int, framework: Optional[str]):
    if system_type == "linux":
        from app.connectors.openscap_server import parse_openscap_xccdf
        # OpenSCAP parser expects a file path; accept raw XML by writing to temp
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".xml")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(raw if isinstance(raw, str) else str(raw))
            return parse_openscap_xccdf(path, tenant_id, ref_id, framework_hint=framework)
        finally:
            os.unlink(path)
    elif system_type == "windows_server":
        from app.connectors.windows_server import assess_windows_config
        return assess_windows_config(raw, tenant_id, ref_id, framework_hint=framework)
    elif system_type == "postgres":
        from app.connectors.postgres_db import assess_postgres_config
        return assess_postgres_config(raw, tenant_id, ref_id, framework_hint=framework)
    elif system_type == "paloalto":
        from app.connectors.paloalto_fw import assess_paloalto_config
        return assess_paloalto_config(raw if isinstance(raw, str) else str(raw),
                                      tenant_id, ref_id, framework_hint=framework)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown system_type '{system_type}'")


@router.post("/heartbeat")
async def heartbeat(payload: dict = None, collector: Collector = Depends(authenticate_collector),
                    db: AsyncSession = Depends(get_db)):
    """Liveness ping. authenticate_collector already updated last_seen/status."""
    if payload and payload.get("version"):
        collector.version = str(payload["version"])[:50]
        await db.commit()
    return {"status": "ok", "collector": collector.name,
            "server_time": datetime.utcnow().isoformat()}


@router.get("/jobs")
async def poll_jobs(collector: Collector = Depends(authenticate_collector),
                    db: AsyncSession = Depends(get_db)):
    """Return pending jobs for THIS collector's tenant, mark them dispatched.
    Tenant is derived from the token — a collector only ever sees its own
    tenant's jobs."""
    jobs = (await db.execute(
        select(ScanJob).where(
            ScanJob.tenant_id == collector.tenant_id,
            ScanJob.status == "pending",
        )
    )).scalars().all()
    out = []
    for j in jobs:
        j.status = "dispatched"
        j.dispatched_at = datetime.utcnow()
        out.append({
            "job_id": j.id, "system_type": j.system_type,
            "target": j.target, "framework": j.framework,
        })
    await db.commit()
    return {"jobs": out}


class ResultIn(BaseModel):
    job_id: Optional[int] = None
    system_type: str
    target: Optional[str] = None
    framework: Optional[str] = None
    raw_data: Any            # raw scanner output (XML string, or settings dict/JSON)


@router.post("/results")
async def submit_results(data: ResultIn, collector: Collector = Depends(authenticate_collector),
                         db: AsyncSession = Depends(get_db)):
    """Receive raw scan output, route to the right parser, create GovernanceEvents
    stamped with the collector's tenant. The collector cannot specify the tenant."""
    tenant_id = collector.tenant_id   # derived from token — the security boundary

    # Resolve the job (if referenced) and confirm it belongs to this tenant
    job = None
    if data.job_id is not None:
        job = (await db.execute(
            select(ScanJob).where(ScanJob.id == data.job_id,
                                  ScanJob.tenant_id == tenant_id)
        )).scalar_one_or_none()
        if not job:
            # Job doesn't exist or isn't this tenant's — refuse
            raise HTTPException(status_code=404, detail="Job not found for this collector")

    framework = data.framework or (job.framework if job else None)
    ref_id = data.job_id or 0

    try:
        events = _parse(data.system_type, data.raw_data, tenant_id, ref_id, framework)
    except HTTPException:
        raise
    except Exception as e:
        if job:
            job.status = "error"; job.error = str(e)[:500]; job.completed_at = datetime.utcnow()
            await db.commit()
        raise HTTPException(status_code=400, detail=f"Failed to parse {data.system_type} output: {e}")

    # Persist events — every one stamped with the derived tenant_id
    created = 0
    for ev in events:
        ev["tenant_id"] = tenant_id   # enforce, regardless of what the parser set
        db.add(GovernanceEvent(**ev))
        created += 1

    if job:
        job.status = "done"; job.completed_at = datetime.utcnow(); job.findings_count = created

    # Update the reporting agent's last-scan info (for the Agents view), matching
    # by system_type (+ target if given) within this tenant/collector.
    agent_q = select(Agent).where(Agent.tenant_id == tenant_id,
                                  Agent.collector_id == collector.id,
                                  Agent.system_type == data.system_type)
    if getattr(data, "target", None):
        agent_q = agent_q.where(Agent.target == data.target)
    agent = (await db.execute(agent_q)).scalars().first()
    if agent:
        agent.last_scan_at = datetime.utcnow()
        agent.last_result = f"{created} finding{'s' if created != 1 else ''}"
        agent.last_seen = datetime.utcnow()

    await db.commit()
    return {"status": "ok", "findings_created": created, "tenant_id": tenant_id}
