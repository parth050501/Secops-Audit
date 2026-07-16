# Code Core Systems — Project Tracker

Status key: DONE | IN PROGRESS | PENDING
Owner: Claude (code) | You (infra/testing/business)

## Foundation & connectors
| # | Task | Owner | Status |
|---|------|-------|--------|
| 1 | Security: credential encryption + bcrypt | Claude | DONE |
| 2 | Real AWS connector (Prowler) — proven on live account | Claude | DONE |
| 3 | Connector field schemas (per-type forms) | Claude | DONE |
| 4 | Azure + GCP connectors (built) | Claude | DONE |
| 5 | Finding dedup + framework-mapping merge | Claude | DONE |
| 6 | Test Azure against real account | You | PENDING |
| 7 | Test GCP against real account | You | PENDING |

## Multi-tenancy & MSSP
| # | Task | Owner | Status |
|---|------|-------|--------|
| 8 | Tenant isolation hardening + attack tests | Claude | DONE |
| 9 | MSSP console: overview, plan/status, impersonate, delete | Claude | DONE |
| 9b| Tenant onboarding (create client + admin from console) | Claude | DONE |
| 10| White-labeling (partner branding on reports) | Claude | PENDING |
| 31| Separate /platform URL kept as operator home (decided) | Claude | DONE |
| 32| Platform roles + team mgmt + Team tab UI | Claude | DONE |
| 33| Tenant user mgmt + UI (Team page, role-based) | Claude | DONE |

## Data layer & compliance depth
| # | Task | Owner | Status |
|---|------|-------|--------|
| 11| PostgreSQL migration (tested against real Postgres) | Claude | DONE |
| 12| Evidence/attestation layer (backend) | Claude | DONE |
| 12b| Evidence-layer frontend (upload/attest UI) | Claude | DONE |
| 13| Policy/document template library | Claude | PENDING |
| 14| Full per-control coverage view (3 evidence sources) | Claude | PENDING |
| 15| Audit-ready comprehensive report | Claude | PENDING |
| 34| SOC 2 readiness workflow (full TSC) | Claude | DONE |

## Hardening & deployment
| # | Task | Owner | Status |
|---|------|-------|--------|
| 16| Job queue for scans (Celery/RQ + worker) | Claude | PENDING |
| 17| Reverse proxy + HTTPS (Caddy) config | Claude | PENDING |
| 18| Production Docker Compose + secrets (Postgres) | Claude | DONE |
| 19| Provision EC2 + security groups | You | PENDING |
| 20| Domain + DNS | You | PENDING |
| 21| Deploy + verify (HTTPS, ports locked, scan works) | You+Claude | PENDING |
| 22| Backups (DB + volume snapshots, restore-tested) | You | PENDING |

## Validation & commercial
| # | Task | Owner | Status |
|---|------|-------|--------|
| 23| Talk to 10–15 real local buyers | You | PENDING |
| 24| Onboard first design partner (real data) | You | PENDING |
| 25| Stripe billing (replace simulated credits) | Claude | PENDING |
| 26| Transactional email (invites, alerts, reports) | Claude | PENDING |
| 27| Start your own SOC 2 process | You | PENDING |
| 28| On-prem collector agent | Claude+You | PENDING |
| 29| Additional connectors per demand | Claude | PENDING |
| 30| GA — SLA, support, incident plan | You | PENDING |

## Network connectors (config-assessment, posture only — NOT SIEM)
| # | Task | Owner | Status |
|---|------|-------|--------|
| 35| Palo Alto firewall config-assessment | Claude | DONE (test on real device) |
| 36| Fortinet config-assessment | Claude | PENDING |
| 37| Cisco ASA/IOS config-assessment | Claude | PENDING |

## Server connectors
| # | Task | Owner | Status |
|---|------|-------|--------|
| 42| Windows server (PowerShell assessment) | Claude | DONE (test in lab) |
| 43| PostgreSQL engine config-assessment | Claude | DONE (test in lab) |
| 44| SQL Server / Oracle / MySQL | Claude | PENDING (on demand) |
| 45| macOS / IBM AIX | Claude | PENDING (on demand) |
| # | Task | Owner | Status |
|---|------|-------|--------|
| 38| Linux server (OpenSCAP) detection+mapping | Claude | DONE (test on real server) |

## Hardening done this session
| # | Task | Owner | Status |
|---|------|-------|--------|
| 39| Production seed (super-admin only, env password) | Claude | DONE |
| 40| Login page: demo hints gated out of production | Claude | DONE |
| 41| Remove Platform Console link from tenant sidebar | Claude | DONE |

## Also done (not originally numbered)
- Landing page for Code Core Systems (lead capture) — DONE
- Custom policy engine, human-in-the-loop ticketing, PDF/Excel export — DONE
- Metered pay-as-you-go AI — DONE

## Critical path to "host for real-data partner testing"
Must-do before a partner connects real data:
  11 (Postgres) DONE → 17 (HTTPS) → 19 (EC2) → 20 (DNS) → 21 (deploy+verify) → 22 (backups)
Plus set production secrets (SECURITY_SETUP.md).

Highest-value next CODE pieces: 17 (Caddy/HTTPS), then 31–33 (login model + user mgmt),
then 12b (evidence UI).
