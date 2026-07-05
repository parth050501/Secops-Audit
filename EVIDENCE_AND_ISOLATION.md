# Tenant Isolation Hardening + Evidence/Attestation Layer

## 1. Tenant isolation hardening (MSSP security floor)
- app/core/tenant_guard.py — helpers that make tenant-scoping structural:
  - tenant_query(model, user) — builds a SELECT pre-filtered to the caller's tenant;
    refuses to run on models without a tenant_id (no accidental unscoped queries)
  - get_owned_or_404(db, model, id, user) — fetches by id only within the caller's
    tenant; a row owned by another tenant is indistinguishable from a missing one
  - assert_same_tenant(obj, user) — belt-and-braces check on loaded objects
- tests/test_tenant_isolation.py — actively ATTACKS the boundary with two tenants:
  - A cannot read / delete / scan / modify B's connectors, tickets, or events
  - List endpoints never leak across tenants
  - All 8 cross-tenant attacks correctly blocked (404)
  - Verified: a tenant admin token cannot reach the platform-admin console (403)

Run the tests anytime:
  cd backend && python tests/test_tenant_isolation.py

## 2. Evidence & attestation layer (closes the compliance gap)
Lets a framework control be satisfied THREE ways, not just by technical scans:
  - technical   — a handled finding from a connector scan
  - document    — an uploaded policy/procedure/screenshot/report
  - attestation — a person formally attesting "we do this", with a note

New: app/models/evidence.py (Evidence, ControlStatus), app/api/routes/evidence.py

Endpoints (all tenant-scoped):
  POST /api/evidence/document        — upload a document for a control
  POST /api/evidence/attestation     — record an attestation for a control
  GET  /api/evidence?framework&control_id  — list evidence
  GET  /api/evidence/{id}/download   — download a document (tenant-scoped)
  DELETE /api/evidence/{id}          — delete evidence
  GET  /api/evidence/controls/{framework}        — per-control status
  PATCH /api/evidence/controls/{fw}/{control_id} — set status/owner/notes
  GET  /api/evidence/coverage/{framework}        — readiness summary

When evidence is added/removed, the control's status + satisfied_by auto-recompute.
Open technical findings mapping to a control keep it "in_progress" until handled.

## New dependencies
- python-multipart (for file uploads)

## Apply
docker compose down -v
docker compose up --build -d
sleep 25
docker compose exec backend python seed.py

Note: evidence files are stored under EVIDENCE_DIR (default /app/data/evidence).
On EC2, make sure that path is on a persistent volume.
