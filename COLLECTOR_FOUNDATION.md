# Collector Foundation (APE side) — built & tested

The secure backend half of the Agent → Collector(CCE) → APE architecture. The
collector/agent PROGRAMS come next; this is what they talk to.

## What's built
Models (app/models/collector.py):
- Collector (CCE) — per tenant, named, token (hashed), status, last_seen. Many per tenant.
- Agent — reports through a collector; system_type, target, schedule, status.
- ScanJob — unit of work; pending→dispatched→done/error; on_demand or scheduled.

Auth (app/core/collector_security.py):
- Token issued at registration (shown once, only bcrypt hash stored).
- authenticate_collector resolves token → Collector → tenant_id. The collector
  NEVER supplies a tenant; the token determines it. Any authed call updates
  last_seen (liveness).

Collector-facing API (app/api/routes/collector_ingest.py) — token-authed:
- POST /api/collector/heartbeat   — liveness + version
- GET  /api/collector/jobs        — poll pending jobs (THIS tenant only)
- POST /api/collector/results     — submit raw scan output

  The "type-routed core": results are tagged system_type (linux/windows_server/
  postgres/paloalto) and routed to the EXISTING parsers we built. Events are
  stamped with the derived tenant_id, always.

Admin/console API (app/api/routes/collector_admin.py):
- POST /api/collectors/platform/register  — staff register a collector (returns token ONCE)
- GET  /api/collectors/platform/all       — platform view of all collectors
- GET  /api/collectors                     — tenant sees its own collectors + status
- GET  /api/collectors/agents              — tenant's agents + status
- POST /api/collectors/scan-now            — queue on-demand job (collector polls it)
- GET  /api/collectors/jobs                — scan job history

## Status model
Collector/agent status is derived from last_seen: "connected" if seen within
5 minutes (HEARTBEAT_TIMEOUT_SECONDS), else "disconnected" (or "pending" if never).

## Scan flow (how it works)
- On-demand: user clicks Scan Now → job queued → collector polls (~1 min) →
  agent runs scan → raw output POSTed to /results → parsed → findings appear.
  NOT instant by design (outbound-only; platform can't push into the network).
- Scheduled: the agent holds its own schedule and pushes results up. (The
  central scheduler that auto-creates jobs is a NEXT piece — not built yet.)

## Security — tested
tests/test_collector_isolation.py (10 checks, all pass):
- heartbeat/auth works; invalid token rejected
- collector A sees only its own jobs, never B's
- A cannot submit against B's job (404)
- every submission stamped with the token's tenant
- tenant B ends with ZERO events — collector A cannot leak across the boundary

## NOT yet built (next sessions)
- The COLLECTOR program (registers, heartbeats, polls, buffers, uploads) — Docker package
- The AGENT program (runs scanners, reports to collector)
- The central SCHEDULER (auto-create jobs on a calendar)
- Collector/agent DASHBOARD UI (status display) — backend ready, UI pending
- Network device scanners (Cisco/Fortinet/pfSense) — pending team's design output
- Credential vault (needed before agentless network scanning) — deferred
