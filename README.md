# Code Core Systems — Compliance Governance Platform

Continuous compliance governance. Connects to your cloud/systems (read-only),
detects findings that violate your chosen framework, maps them to controls,
turns them into human-reviewed tickets, and gives auditors a live read-only view
plus an evidence-backed report. MSSP-ready multi-tenant architecture.

## Stack
- Backend: FastAPI + SQLAlchemy (async) + SQLite (dev) — at `/backend`
- Frontend: Next.js 14 + TypeScript + Tailwind — at `/frontend`
- Orchestration: Docker Compose
- Detection engine: Prowler (AWS/Azure/GCP real connectors)

## Quick start (local)
```
docker compose up --build -d
sleep 25
docker compose exec backend python seed.py
# open http://localhost:3000
```

## Demo accounts
- admin@secops.ai / password        (tenant admin)
- engineer@ / manager@ / auditor@secops.ai / password
- Platform console (manage all tenants): super@secops.ai / superpassword → /platform

## What's built (and tested)
- Real cloud connectors via Prowler: AWS (proven on a live account), Azure, GCP
  - Findings mapped to SOC2 / ISO27001 / PCI / HIPAA / NIST control IDs
  - Dedup with framework-mapping merge
- Per-connector credential field schemas (correct fields per type)
- Security: credential encryption at rest (Fernet) + bcrypt passwords
- Multi-tenancy: tenant isolation hardening + cross-tenant attack test suite
- Platform/MSSP console: overview (MRR/ARR), tenant management, onboarding,
  plan/status changes, impersonation, delete
- SOC 2 readiness workflow (full Trust Services Criteria)
- Evidence & attestation layer: satisfy controls via technical findings,
  uploaded documents, or human attestations; per-control coverage + readiness
- Custom policy engine, human-in-the-loop ticketing, PDF/Excel audit export
- Pay-as-you-go metered AI (opt-in)

## Production prerequisites (before hosting with real data)
See SECURITY_SETUP.md. Required env vars: SECOPS_ENCRYPTION_KEY, JWT_SECRET,
ENVIRONMENT=production. Use docker-compose.prod.yml for the production overrides.

## Key docs in this repo
- SECURITY_SETUP.md          — security foundation + required env vars
- AWS_CONNECTOR.md           — connecting a real AWS account
- AZURE_GCP_CONNECTORS.md     — Azure + GCP setup
- EVIDENCE_AND_ISOLATION.md   — evidence layer + tenant isolation
- CHANGELOG.md                — platform admin + SOC 2 build notes

## Tests
```
cd backend && python tests/test_tenant_isolation.py   # cross-tenant attack tests
```

## Apply-update pattern
- Backend schema change: `docker compose down -v && docker compose up --build -d`
  then `docker compose exec backend python seed.py`
- Frontend-only: `docker compose up --build -d frontend` + hard refresh

## Status
Working prototype with one real connector proven (AWS). Not yet production-hardened:
pending PostgreSQL migration, job queue for scans, deployment (reverse proxy +
HTTPS), and the evidence-layer frontend. See the project tracker for the full plan.
