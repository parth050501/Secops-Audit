"""
Platform role enforcement tests.

Proves the capability boundaries actually hold:
  - super_admin can do everything (incl. billing + team)
  - admin can onboard tenants + manage team, but NOT billing
  - analyst can view + impersonate, but NOT onboard/delete/billing/team
  - read_only can view, but NOT anything mutating

Run:  python tests/test_platform_roles.py
"""
import os, asyncio, sys
os.environ.setdefault("ENVIRONMENT", "qc")
os.environ.setdefault("JWT_SECRET", "test-roles")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import hash_password
from app.models.platform import PlatformAdmin, TenantBilling
from app.models.tenant import Tenant
from app.models.user import User


async def _setup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        for role in ("super_admin", "admin", "analyst", "read_only"):
            db.add(PlatformAdmin(email=f"{role}@plat.com", name=role, role=role,
                                 hashed_pw=hash_password("pw")))
        # a tenant to act on
        t = Tenant(name="Target", industry="tech", frameworks=["soc2"],
                   active_framework="soc2", onboarded=True)
        db.add(t); await db.flush()
        db.add(User(email="ta@target.com", name="TA", role="admin",
                    hashed_pw=hash_password("pw"), tenant_id=t.id))
        db.add(TenantBilling(tenant_id=t.id, plan="starter", status="active", mrr=499))
        await db.commit()
        return t.id


async def _login(client, role):
    r = await client.post("/api/platform/login", json={"email": f"{role}@plat.com", "password": "pw"})
    assert r.status_code == 200, f"{role} login failed"
    return {"Authorization": f"Bearer {r.json()['token']}"}


async def run():
    tid = await _setup()
    results = []
    def check(name, cond):
        results.append(cond); print(("  PASS  " if cond else "  FAIL  ") + name)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h = {r: await _login(client, r) for r in ("super_admin", "admin", "analyst", "read_only")}

        # Everyone can view overview
        for role in h:
            r = await client.get("/api/platform/overview", headers=h[role])
            check(f"{role} can view overview", r.status_code == 200)

        # Onboard tenant: super_admin + admin yes; analyst + read_only no
        body = lambda n: {"name": n, "admin_name": "X", "admin_email": f"x_{n}@c.com",
                          "admin_password": "pw123", "plan": "starter"}
        check("super_admin CAN onboard",
              (await client.post("/api/platform/tenants", headers=h["super_admin"], json=body("t1"))).status_code == 200)
        check("admin CAN onboard",
              (await client.post("/api/platform/tenants", headers=h["admin"], json=body("t2"))).status_code == 200)
        check("analyst CANNOT onboard (403)",
              (await client.post("/api/platform/tenants", headers=h["analyst"], json=body("t3"))).status_code == 403)
        check("read_only CANNOT onboard (403)",
              (await client.post("/api/platform/tenants", headers=h["read_only"], json=body("t4"))).status_code == 403)

        # Billing: ONLY super_admin
        check("super_admin CAN change billing",
              (await client.patch(f"/api/platform/tenants/{tid}/plan", headers=h["super_admin"], json={"plan": "professional"})).status_code == 200)
        check("admin CANNOT change billing (403)",
              (await client.patch(f"/api/platform/tenants/{tid}/plan", headers=h["admin"], json={"plan": "enterprise"})).status_code == 403)
        check("analyst CANNOT change billing (403)",
              (await client.patch(f"/api/platform/tenants/{tid}/plan", headers=h["analyst"], json={"plan": "enterprise"})).status_code == 403)

        # Team management: super_admin + admin yes; analyst + read_only no
        tm = lambda e: {"name": "New", "email": e, "password": "pw123", "role": "analyst"}
        check("super_admin CAN add team member",
              (await client.post("/api/platform/team", headers=h["super_admin"], json=tm("m1@plat.com"))).status_code == 200)
        check("admin CAN add team member",
              (await client.post("/api/platform/team", headers=h["admin"], json=tm("m2@plat.com"))).status_code == 200)
        check("analyst CANNOT add team member (403)",
              (await client.post("/api/platform/team", headers=h["analyst"], json=tm("m3@plat.com"))).status_code == 403)
        check("read_only CANNOT add team member (403)",
              (await client.post("/api/platform/team", headers=h["read_only"], json=tm("m4@plat.com"))).status_code == 403)

        # Only super_admin can create another super_admin
        check("admin CANNOT create a super_admin (403)",
              (await client.post("/api/platform/team", headers=h["admin"],
                                 json={"name": "S", "email": "s2@plat.com", "password": "pw123", "role": "super_admin"})).status_code == 403)

        # Impersonate: analyst yes, read_only no
        check("analyst CAN impersonate",
              (await client.post(f"/api/platform/tenants/{tid}/impersonate", headers=h["analyst"])).status_code == 200)
        check("read_only CANNOT impersonate (403)",
              (await client.post(f"/api/platform/tenants/{tid}/impersonate", headers=h["read_only"])).status_code == 403)

    passed = sum(results); total = len(results)
    print(f"\n{passed}/{total} role-enforcement checks passed")
    return passed == total


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(run()) else 1)
