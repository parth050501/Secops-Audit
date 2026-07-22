"""
Cody isolation test.

Proves the security boundary: build_tenant_posture for tenant A contains ONLY
tenant A's findings, never tenant B's. The chat endpoint derives the tenant from
the session, so a user can never retrieve another tenant's posture.

Run: python tests/test_cody_isolation.py
"""
import os, asyncio, sys
os.environ.setdefault("ENVIRONMENT", "qc")
os.environ.setdefault("JWT_SECRET", "test-cody")
os.environ.setdefault("SECOPS_ENCRYPTION_KEY", "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base, AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.event import GovernanceEvent
from app.services.cody import build_tenant_posture
from datetime import datetime


async def run():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.drop_all)
        await c.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        a = Tenant(name="Tenant A", industry="tech", frameworks=["soc2"], active_framework="soc2", onboarded=True)
        b = Tenant(name="Tenant B", industry="tech", frameworks=["soc2"], active_framework="soc2", onboarded=True)
        db.add(a); db.add(b); await db.flush()
        # A's finding
        db.add(GovernanceEvent(tenant_id=a.id, title="A-SECRET: public S3 bucket",
            severity="high", category="x", source_type="scan", status="open",
            framework_mappings={"soc2":["CC6.1"]}, raw_data={"source":"aws"}, occurred_at=datetime.utcnow()))
        # B's finding
        db.add(GovernanceEvent(tenant_id=b.id, title="B-SECRET: open database",
            severity="high", category="x", source_type="scan", status="open",
            framework_mappings={"soc2":["CC6.7"]}, raw_data={"source":"postgres"}, occurred_at=datetime.utcnow()))
        await db.commit()
        a_id, b_id = a.id, b.id

    results = []
    def check(name, cond): results.append(cond); print(("  PASS  " if cond else "  FAIL  ")+name)

    async with AsyncSessionLocal() as db:
        pa = await build_tenant_posture(db, a_id)
        pb = await build_tenant_posture(db, b_id)

    a_titles = [f["title"] for f in pa["findings"]]
    b_titles = [f["title"] for f in pb["findings"]]

    check("A posture includes A's finding", any("A-SECRET" in t for t in a_titles))
    check("A posture does NOT include B's finding", not any("B-SECRET" in t for t in a_titles))
    check("B posture includes B's finding", any("B-SECRET" in t for t in b_titles))
    check("B posture does NOT include A's finding", not any("A-SECRET" in t for t in b_titles))
    check("A organization name correct", pa["organization"] == "Tenant A")
    check("A finding count is exactly 1", pa["summary"]["total_open_findings"] == 1)

    passed = sum(results)
    print(f"\n{passed}/{len(results)} Cody isolation checks passed")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(run()) else 1)
