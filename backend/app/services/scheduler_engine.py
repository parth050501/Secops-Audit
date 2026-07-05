"""
Scheduling engine.

A lightweight background loop that runs inside the backend process. Every minute
it looks for asset groups whose next scheduled run has arrived, and for each one
it queues a scan job per member agent (exactly like a manual group "Scan Now"),
then computes the group's next run time.

Design notes / honesty:
- This is a single-process in-app scheduler. It's simple and reliable for one
  backend instance (the current deployment). If the platform is ever scaled to
  multiple backend replicas, this would need a lock or a dedicated worker so the
  same job isn't queued twice — noted for later, not needed now.
- It only QUEUES jobs. The collector still pulls and the agents still scan, so
  the scheduler respects the same async, pull-based model as everything else.
- Missed runs (e.g. backend was down) are handled by "if next_run_at <= now, run
  it now and schedule the next one" — so a due scan fires on the next tick rather
  than being lost.
"""
import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.collector import AssetGroup, Agent, ScanJob
from app.models.tenant import Tenant
from app.api.routes.scheduler import _next_run

log = logging.getLogger("scheduler.engine")

CHECK_INTERVAL_SECONDS = 60   # how often the loop wakes up


async def _run_due_groups_once():
    """One pass: find groups due to run and queue their scans."""
    now = datetime.utcnow()
    async with AsyncSessionLocal() as db:
        # groups with a real schedule and a next_run_at that has arrived
        due = (await db.execute(
            select(AssetGroup).where(
                AssetGroup.schedule != "manual",
                AssetGroup.next_run_at.isnot(None),
                AssetGroup.next_run_at <= now,
            )
        )).scalars().all()

        if not due:
            return 0

        total_jobs = 0
        for g in due:
            # resolve this group's agents (scoped to the group's tenant)
            agents = {a.id: a for a in (await db.execute(
                select(Agent).where(Agent.tenant_id == g.tenant_id)
            )).scalars().all()}

            t = (await db.execute(
                select(Tenant).where(Tenant.id == g.tenant_id)
            )).scalar_one_or_none()
            framework = t.active_framework if t else None

            queued = 0
            for aid in (g.agent_ids or []):
                a = agents.get(aid)
                if not a:
                    continue
                db.add(ScanJob(
                    tenant_id=g.tenant_id, collector_id=a.collector_id, agent_id=a.id,
                    system_type=a.system_type, target=a.target, framework=framework,
                    status="pending", origin="scheduled",
                ))
                queued += 1

            g.last_run_at = now
            g.next_run_at = _next_run(g.schedule, g.schedule_time, g.schedule_day)
            total_jobs += queued
            log.info("scheduled scan: group '%s' (tenant %s) queued %d job(s); next run %s",
                     g.name, g.tenant_id, queued, g.next_run_at)

        await db.commit()
        return total_jobs


async def scheduler_loop():
    """Long-running background task. Started from the app lifespan."""
    log.info("scheduling engine started (checks every %ss)", CHECK_INTERVAL_SECONDS)
    while True:
        try:
            await _run_due_groups_once()
        except asyncio.CancelledError:
            log.info("scheduling engine stopping")
            raise
        except Exception as e:
            # never let a bad pass kill the loop
            log.warning("scheduler pass failed: %s", e)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
