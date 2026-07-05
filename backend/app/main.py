from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio, json
from typing import Set, Dict

from app.core.database import init_db
from app.core.config import settings
from app.api.routes import auth, tenants, connectors, governance, tickets, auditor, ai, policies, platform, soc2, evidence, tenant_users, collector_admin, collector_ingest, cody_chat, scheduler, frameworks_admin

# WebSocket connection manager — connections are grouped per tenant so live
# events are only ever sent to clients belonging to that tenant. Broadcasting
# to all clients would leak one tenant's findings to another.
class ConnectionManager:
    def __init__(self):
        # tenant_id -> set of sockets for that tenant
        self.by_tenant: Dict[int, Set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, tenant_id: int):
        await ws.accept()
        self.by_tenant.setdefault(tenant_id, set()).add(ws)

    def disconnect(self, ws: WebSocket, tenant_id: int):
        conns = self.by_tenant.get(tenant_id)
        if conns:
            conns.discard(ws)
            if not conns:
                self.by_tenant.pop(tenant_id, None)

    async def broadcast_to_tenant(self, tenant_id: int, data: dict):
        """Send only to sockets belonging to this tenant."""
        conns = self.by_tenant.get(tenant_id)
        if not conns:
            return
        dead = set()
        for ws in conns:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.add(ws)
        self.by_tenant[tenant_id] = conns - dead

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Seed code-defined frameworks into the DB (idempotent) so they're editable.
    from app.core.database import AsyncSessionLocal
    from app.services.framework_store import seed_frameworks
    async with AsyncSessionLocal() as db:
        try:
            n = await seed_frameworks(db)
            if n:
                import logging; logging.getLogger("startup").info("seeded %d frameworks into DB", n)
        except Exception as e:
            import logging; logging.getLogger("startup").warning("framework seed skipped: %s", e)
    # Start the background scheduling engine (auto-runs due group scans).
    from app.services.scheduler_engine import scheduler_loop
    task = asyncio.create_task(scheduler_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="SecOps AI — Governance Platform",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:3000","http://frontend:3000"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api/auth",       tags=["auth"])
app.include_router(tenants.router,     prefix="/api/tenants",    tags=["tenants"])
app.include_router(connectors.router,  prefix="/api/connectors", tags=["connectors"])
app.include_router(governance.router,  prefix="/api/governance", tags=["governance"])
app.include_router(tickets.router,     prefix="/api/tickets",    tags=["tickets"])
app.include_router(auditor.router,     prefix="/api/auditor",    tags=["auditor"])
app.include_router(ai.router,          prefix="/api/ai",         tags=["ai"])
app.include_router(policies.router,    prefix="/api/policies",   tags=["policies"])
app.include_router(platform.router,    prefix="/api/platform",   tags=["platform"])
app.include_router(soc2.router,        prefix="/api/soc2",       tags=["soc2"])
app.include_router(evidence.router,    prefix="/api/evidence",   tags=["evidence"])
app.include_router(tenant_users.router, prefix="/api/users",     tags=["users"])
app.include_router(collector_admin.router, prefix="/api/collectors", tags=["collectors"])
app.include_router(collector_ingest.router, prefix="/api/collector", tags=["collector-ingest"])
app.include_router(cody_chat.router, prefix="/api/cody", tags=["cody"])
app.include_router(scheduler.router, prefix="/api/scheduler", tags=["scheduler"])
app.include_router(frameworks_admin.router, prefix="/api/frameworks", tags=["frameworks"])

@app.websocket("/ws/events")
async def websocket_events(ws: WebSocket, token: str = Query(None)):
    """Authenticated, tenant-scoped event stream.

    The client must pass a valid JWT as ?token=... The connection is bound to
    that user's tenant, and only that tenant's events are delivered.
    """
    # Authenticate before accepting — reject anonymous or invalid tokens
    from jose import JWTError, jwt
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    if not token:
        await ws.close(code=4401)  # unauthorized
        return
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        await ws.close(code=4401)
        return

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        await ws.close(code=4401)
        return

    tenant_id = user.tenant_id
    await manager.connect(ws, tenant_id)
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(ws, tenant_id)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "SecOps AI Governance",
            "environment": settings.environment,
            "ai_mode": "pay_as_you_go"}

# Export manager so routes can broadcast
app.state.manager = manager
