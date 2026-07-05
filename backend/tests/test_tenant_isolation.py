"""
Tenant isolation test suite.

These tests actively try to break tenant isolation — they create two separate
tenants with their own data, then attempt to make one tenant's user access the
other tenant's connectors, tickets, events, and reports. Every cross-tenant
attempt MUST fail (404), and every same-tenant access MUST succeed.

Run with:  python -m pytest tests/test_tenant_isolation.py -v
or standalone:  python tests/test_tenant_isolation.py
"""
import os
import asyncio
import sys

os.environ.setdefault("ENVIRONMENT", "qc")
os.environ.setdefault("JWT_SECRET", "test-isolation")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.models.connector import Connector
from app.models.event import GovernanceEvent
from app.models.ticket import Ticket


async def _setup_two_tenants():
    """Create tenant A and tenant B, each with a user, connector, event, ticket."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    ids = {}
    async with AsyncSessionLocal() as db:
        for tag in ("A", "B"):
            t = Tenant(name=f"Tenant {tag}", industry="tech",
                       frameworks=["soc2"], active_framework="soc2", onboarded=True)
            db.add(t); await db.flush()
            u = User(email=f"user{tag}@test.com", name=f"User {tag}", role="admin",
                     hashed_pw=hash_password("password"), tenant_id=t.id)
            db.add(u)
            c = Connector(name=f"conn-{tag}", category="cloud", connector_type="aws",
                          tenant_id=t.id, status="connected")
            db.add(c); await db.flush()
            e = GovernanceEvent(tenant_id=t.id, connector_id=c.id, title=f"finding-{tag}",
                                severity="high", category="identity", status="open",
                                framework_mappings={"soc2": ["CC6.1"]})
            db.add(e); await db.flush()
            tk = Ticket(tenant_id=t.id, title=f"ticket-{tag}", description="x",
                        status="open", framework="soc2", severity="high",
                        event_id=e.id)
            db.add(tk); await db.flush()
            ids[tag] = {"tenant": t.id, "connector": c.id, "event": e.id, "ticket": tk.id}
        await db.commit()
    return ids


async def _login(client, tag):
    r = await client.post("/api/auth/login", json={"email": f"user{tag}@test.com", "password": "password"})
    assert r.status_code == 200, f"login {tag} failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['token']}"}


async def run():
    ids = await _setup_two_tenants()
    results = []
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        hA = await _login(client, "A")
        hB = await _login(client, "B")

        def check(name, cond):
            results.append((name, cond))
            print(("  PASS  " if cond else "  FAIL  ") + name)

        # 1. A lists connectors — sees only its own
        r = await client.get("/api/connectors", headers=hA)
        names = [c["name"] for c in r.json()]
        check("A sees only its own connectors", names == ["conn-A"])

        # 2. B lists connectors — sees only its own
        r = await client.get("/api/connectors", headers=hB)
        names = [c["name"] for c in r.json()]
        check("B sees only its own connectors", names == ["conn-B"])

        # 3. A tries to fetch B's ticket by id — must 404
        r = await client.get(f"/api/tickets/{ids['B']['ticket']}", headers=hA)
        check("A cannot read B's ticket (404)", r.status_code == 404)

        # 4. A can read its own ticket
        r = await client.get(f"/api/tickets/{ids['A']['ticket']}", headers=hA)
        check("A can read its own ticket", r.status_code == 200)

        # 5. A tries to delete B's connector — must 404 (and not delete)
        r = await client.delete(f"/api/connectors/{ids['B']['connector']}", headers=hA)
        check("A cannot delete B's connector (404)", r.status_code == 404)

        # 6. A tries to trigger a scan on B's connector — must 404
        r = await client.post(f"/api/connectors/{ids['B']['connector']}/scan", headers=hA)
        check("A cannot scan B's connector (404)", r.status_code == 404)

        # 7. A tries to transition B's ticket — must 404
        r = await client.patch(f"/api/tickets/{ids['B']['ticket']}",
                               headers=hA, json={"status": "in_review"})
        check("A cannot modify B's ticket (404)", r.status_code == 404)

        # 8. Governance list for A contains only A's events
        r = await client.get("/api/governance/events", headers=hA)
        if r.status_code == 200:
            titles = [e.get("title") for e in r.json()]
            check("A's governance list has no B events", all(t != "finding-B" for t in titles))
        else:
            check("A's governance list endpoint reachable", False)

    passed = sum(1 for _, c in results if c)
    total = len(results)
    print(f"\n{passed}/{total} isolation checks passed")
    return passed == total


if __name__ == "__main__":
    ok = asyncio.run(run())
    sys.exit(0 if ok else 1)
