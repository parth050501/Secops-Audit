# Security Fixes — Changelog (this commit)

Addresses the external code-review findings. All changes tested.

## Critical security fixes

### 1. WebSocket tenant data-leak — FIXED (was: broadcast to all clients)
- `backend/app/main.py` — ConnectionManager now groups sockets per tenant
  (`by_tenant`) and `broadcast_to_tenant()` sends only to that tenant's clients.
  The `/ws/events` endpoint now REQUIRES a valid JWT (`?token=`), authenticates
  it, and binds the connection to the user's tenant. Anonymous/invalid tokens
  are rejected (close code 4401).
- `backend/app/api/routes/connectors.py` — broadcast call now uses
  `broadcast_to_tenant(tenant_id, ...)`.
- `frontend/app/(app)/layout.tsx` — WebSocket client now sends the auth token
  and only connects when logged in.

### 2. Backend RBAC enforcement — ADDED (was: any logged-in user could mutate)
- `backend/app/core/tenant_guard.py` — added TENANT_CAPABILITIES matrix +
  `require_tenant_capability()` dependency.
- Applied guards so the **auditor role is read-only** server-side:
  - connectors: add/scan/delete require `manage_connectors` (admin, engineer)
  - tickets: create/update require `work_tickets` (admin, manager, engineer)
  - evidence: upload/attest/delete require `manage_evidence`
  - tenant settings: update requires `manage_tenant` (admin only)
- Tested: `backend/tests/test_rbac.py` (7 checks) — auditor blocked from all
  mutations, engineer allowed connector/ticket work but not settings.

### 3. Public self-registration — DISABLED (was: anyone could register + pick role)
- `backend/app/api/routes/auth.py` — `/api/auth/register` now returns 403.
  Users are provisioned through controlled flows only (platform onboards
  tenants; tenant admins add users).

### 4. Demo accounts gated out of production — ADDED
- `backend/seed.py` — refuses to seed demo data when ENVIRONMENT=production
  unless ALLOW_PROD_SEED=1 is explicitly set.

### 5. Jira/ServiceNow tokens — NOW ENCRYPTED (was: plaintext columns)
- `backend/app/api/routes/tenants.py` — integration tokens are encrypted with
  the existing Fernet layer on write. (Serializer already only exposed
  has_jira/has_servicenow booleans, never the tokens.)

### 6. Duplicate axios import — FIXED (build risk)
- `frontend/lib/api.ts` — removed the second `import axios` (was redeclared).

## Production hardening (also in this commit)

### Production frontend build — ADDED (was: npm run dev in prod)
- `frontend/Dockerfile.prod` — multi-stage build, runs `npm run build` +
  `npm run start`.
- `docker-compose.prod.yml` — frontend now builds from Dockerfile.prod.

### PostgreSQL — already migrated (prior commit), tested against real Postgres.

## Tests (all passing)
- tests/test_tenant_isolation.py — 8 cross-tenant attack checks
- tests/test_platform_roles.py — 18 platform role-enforcement checks
- tests/test_rbac.py — 7 tenant RBAC checks
Run: `cd backend && python tests/test_<name>.py`

## Still pending (next, NOT in this commit)
- Job queue for scans (Celery/RQ) — so long Prowler runs don't tie up the API
- HTTPS/reverse proxy (Caddy) — once your subdomain is set up
- Alembic migrations (replace create_all for safe schema changes on live data)
- User-management UI (platform Team tab, tenant Users tab — backend done)
- Evidence-layer UI
- Backups + restore testing on the deployed instance
