# CodeCore Collector Engine (Relay)

Runs inside the customer network (packaged in your hardened OVA). The collector
is a RELAY: it does NOT scan. Agents on internal systems do all scanning and
send raw results to this collector, which authenticates them, buffers results
durably, and forwards them to the CodeCore platform (APE) over outbound HTTPS.

    Agent (scans a system) --> Collector/CCE (relay) --> Platform (APE: parse+map)

## Why a relay
- One outbound egress (the collector). Agents talk only to the collector, locally.
- The collector is bound to ONE tenant via its platform token; everything it
  forwards is stamped that tenant server-side. No cross-tenant risk.
- All compliance logic lives in the platform — the collector stays dumb, so
  changing checks never means updating deployed collectors.

## Deploy inputs
- APE_URL          e.g. https://qc.codecoresystems.in
- COLLECTOR_TOKEN  secret token from the platform console (per tenant, shown once)
- ENROLL_SECRET    a strong shared secret; agents present it to enroll with this CCE

## Run with Docker (recommended; goes inside your OVA)
    APE_URL=https://qc.codecoresystems.in \
    COLLECTOR_TOKEN=cce_xxxx \
    ENROLL_SECRET=$(openssl rand -hex 24) \
    docker compose up --build -d
    docker compose logs -f collector    # "Enrolled and connected. Collecting for: <name>"

## Ports
- OUTBOUND 443 to the platform (HTTPS).
- INBOUND 8514 for agents — INTERNAL network only. Never expose to the internet.

## How agents use it
1. Agent enrolls:  POST http://<collector-host>:8514/agent/enroll
     {name, system_type, enroll_secret}  -> {agent_token}
2. Agent submits results:  POST /agent/results
     Authorization: Bearer <agent_token>
     {system_type, raw_data, target?, framework?}  -> queued, then forwarded
   (The agent build does this automatically; this is the contract.)

## Security
- Platform token & agent tokens are never logged.
- Agent enrollment requires the shared enroll secret (stops rogue enrollment).
- Durable queue: if the platform is unreachable, results are kept and retried.
- Runs as non-root in the container. Outbound TLS verified by default.

## Files
- codecore_collector/  — engine (config, queue, agent_registry, inbound, ape_client, engine)
- Dockerfile, docker-compose.yml  — container build/run
- codecore-collector.service      — systemd unit (non-Docker)
- collector.conf.example          — config template

## Version 0.1.0
Modular (enrollment, heartbeat, inbound server, queue, uploader are separate),
built for the patch-update model — update parts without rebuilding the core.

## Scanning
The collector does NOT scan. Scanning lives in the AGENTS (Linux/Windows), which
run the actual checks (OpenSCAP, PowerShell, DB read-only queries — including a
DB hosted on that Linux/Windows host) and report here. A pure standalone DB
appliance with no host OS to run an agent is out of scope for now (would need the
agentless + credential-vault path, deferred).
