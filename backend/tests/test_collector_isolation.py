"""
Collector foundation tests.

Proves:
  1. End-to-end: register collector → heartbeat → queue job → poll → submit
     results → governance events created, stamped with the right tenant.
  2. ISOLATION (security-critical): a collector token for tenant A cannot
     - submit results that land in tenant B
     - poll/see tenant B's jobs
     - reference tenant B's job
  3. The token determines the tenant — a collector cannot claim another tenant.

Run: python tests/test_collector_isolation.py
"""
import os, asyncio, sys
os.environ.setdefault("ENVIRONMENT", "qc")
os.environ.setdefault("JWT_SECRET", "test-collector")
os.environ.setdefault("SECOPS_ENCRYPTION_KEY", "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import hash_password
from app.core.collector_security import generate_collector_token, hash_token
from app.models.tenant import Tenant
from app.models.user import User
from app.models.collector import Collector, ScanJob
from app.models.event import GovernanceEvent
from sqlalchemy import select


# A realistic Postgres assessment payload (weak settings → should yield findings)
PG_PAYLOAD = {"settings": {"ssl": "off", "password_encryption": "md5"}, "superuser_count": 5}


async def _setup():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.drop_all)
        await c.run_sync(Base.metadata.create_all)
    ids = {}
    async with AsyncSessionLocal() as db:
        for tag in ("A", "B"):
            t = Tenant(name=f"Tenant {tag}", industry="tech", frameworks=["pci_dss"],
                       active_framework="pci_dss", onboarded=True)
            db.add(t); await db.flush()
            # a collector per tenant, with a known token
            token = generate_collector_token()
            col = Collector(tenant_id=t.id, name=f"{tag}-CCE1",
                            token_hash=hash_token(token), token_prefix=token[:12],
                            status="pending")
            db.add(col); await db.flush()
            ids[tag] = {"tenant": t.id, "collector": col.id, "token": token}
        await db.commit()
    return ids


async def run():
    ids = await _setup()
    results = []
    def check(name, cond):
        results.append(cond); print(("  PASS  " if cond else "  FAIL  ") + name)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        hA = {"Authorization": f"Bearer {ids['A']['token']}"}
        hB = {"Authorization": f"Bearer {ids['B']['token']}"}

        # 1. Heartbeat works and authenticates
        r = await client.post("/api/collector/heartbeat", headers=hA, json={"version": "0.1"})
        check("collector A heartbeat ok", r.status_code == 200)

        # 2. Invalid token rejected
        r = await client.post("/api/collector/heartbeat", headers={"Authorization": "Bearer cce_bogus"})
        check("invalid token rejected (401)", r.status_code == 401)

        # 3. Queue a job for tenant A (directly), poll as A → sees it
        async with AsyncSessionLocal() as db:
            job = ScanJob(tenant_id=ids['A']['tenant'], system_type="postgres",
                          framework="pci_dss", status="pending", origin="on_demand")
            db.add(job); await db.commit(); await db.refresh(job)
            jobA_id = job.id
            # also a job for tenant B
            jobB = ScanJob(tenant_id=ids['B']['tenant'], system_type="postgres",
                           framework="pci_dss", status="pending", origin="on_demand")
            db.add(jobB); await db.commit(); await db.refresh(jobB)
            jobB_id = jobB.id

        r = await client.get("/api/collector/jobs", headers=hA)
        job_ids = [j["job_id"] for j in r.json()["jobs"]]
        check("A polls and sees its own job", jobA_id in job_ids)
        check("A does NOT see B's job", jobB_id not in job_ids)

        # 4. A submits results for its job → events created in tenant A
        r = await client.post("/api/collector/results", headers=hA, json={
            "job_id": jobA_id, "system_type": "postgres", "framework": "pci_dss",
            "raw_data": PG_PAYLOAD,
        })
        check("A submits results ok", r.status_code == 200 and r.json()["findings_created"] > 0)
        check("A results stamped tenant A", r.json().get("tenant_id") == ids['A']['tenant'])

        # 5. ISOLATION: A tries to submit results referencing B's job → 404
        r = await client.post("/api/collector/results", headers=hA, json={
            "job_id": jobB_id, "system_type": "postgres", "raw_data": PG_PAYLOAD,
        })
        check("A CANNOT submit against B's job (404)", r.status_code == 404)

        # 6. ISOLATION: even a job-less submit by A only ever lands in tenant A
        r = await client.post("/api/collector/results", headers=hA, json={
            "system_type": "postgres", "framework": "pci_dss", "raw_data": PG_PAYLOAD,
        })
        check("A job-less submit stamped tenant A", r.json().get("tenant_id") == ids['A']['tenant'])

        # 7. Verify in DB: NO governance events exist for tenant B (A never leaked in)
        async with AsyncSessionLocal() as db:
            b_events = (await db.execute(
                select(GovernanceEvent).where(GovernanceEvent.tenant_id == ids['B']['tenant'])
            )).scalars().all()
            a_events = (await db.execute(
                select(GovernanceEvent).where(GovernanceEvent.tenant_id == ids['A']['tenant'])
            )).scalars().all()
        check("tenant B has ZERO events (no cross-tenant leak)", len(b_events) == 0)
        check("tenant A has events", len(a_events) > 0)

    passed = sum(results); total = len(results)
    print(f"\n{passed}/{total} collector foundation checks passed")
    return passed == total


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(run()) else 1)
