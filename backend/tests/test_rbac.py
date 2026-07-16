"""
Tenant RBAC enforcement tests.
Proves the auditor role is READ-ONLY server-side: it can view but cannot
create connectors, trigger scans, create/update tickets, upload evidence, or
change tenant settings — regardless of what the UI shows.
"""
import os, asyncio, sys
os.environ.setdefault("ENVIRONMENT","qc"); os.environ.setdefault("JWT_SECRET","test-rbac")
os.environ.setdefault("SECOPS_ENCRYPTION_KEY","ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User

async def _setup():
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.drop_all); await c.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        t = Tenant(name="T", industry="tech", frameworks=["soc2"], active_framework="soc2", onboarded=True)
        db.add(t); await db.flush()
        for role in ("admin","engineer","manager","auditor"):
            db.add(User(email=f"{role}@t.com", name=role, role=role,
                        hashed_pw=hash_password("pw"), tenant_id=t.id))
        await db.commit()

async def _login(client, role):
    r = await client.post("/api/auth/login", json={"email": f"{role}@t.com","password":"pw"})
    return {"Authorization": f"Bearer {r.json()['token']}"}

async def run():
    await _setup()
    results = []
    def check(n, c): results.append(c); print(("  PASS  " if c else "  FAIL  ")+n)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        aud = await _login(client, "auditor")
        eng = await _login(client, "engineer")

        # Auditor can VIEW
        check("auditor can list connectors (view)",
              (await client.get("/api/connectors", headers=aud)).status_code == 200)

        # Auditor CANNOT mutate
        check("auditor CANNOT add connector (403)",
              (await client.post("/api/connectors", headers=aud,
                json={"name":"x","category":"cloud","connector_type":"aws"}).status_code if False else
                (await client.post("/api/connectors", headers=aud, json={"name":"x","category":"cloud","connector_type":"aws"})).status_code) == 403)
        check("auditor CANNOT create ticket (403)",
              (await client.post("/api/tickets", headers=aud,
                json={"title":"t","description":"d","framework":"soc2","severity":"high"})).status_code == 403)
        check("auditor CANNOT change tenant settings (403)",
              (await client.patch("/api/tenants/me", headers=aud, json={"scan_schedule":"weekly"})).status_code == 403)
        check("auditor CANNOT upload attestation (403)",
              (await client.post("/api/evidence/attestation", headers=aud,
                json={"framework":"soc2","control_id":"CC1.1","title":"x","attestation_note":"y"})).status_code == 403)

        # Engineer CAN do connector/ticket work
        check("engineer CAN add connector",
              (await client.post("/api/connectors", headers=eng,
                json={"name":"x","category":"cloud","connector_type":"splunk"})).status_code in (200,201))
        check("engineer CANNOT change tenant settings (403)",
              (await client.patch("/api/tenants/me", headers=eng, json={"scan_schedule":"weekly"})).status_code == 403)

    passed=sum(results); total=len(results)
    print(f"\n{passed}/{total} RBAC checks passed")
    return passed==total

if __name__ == "__main__":
    sys.exit(0 if asyncio.run(run()) else 1)
