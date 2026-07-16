# Phase 2 — Platform Admin Console + SOC 2 Readiness

## 1. Platform Admin Console (manage all tenants)
A separate super-admin layer above tenants — for you, the SaaS operator.

**Access two ways:**
- Separate portal at **/platform** (super-admin login)
- Role-gated link in the sidebar for tenant admins ("Platform Console")

**Capabilities:**
- **MRR / ARR dashboard** — live recurring revenue, plan distribution, totals across all tenants
- **Tenant table** — every org with plan, MRR, status, usage (users/connectors/events)
- **Change plans** — starter / professional / enterprise (auto-updates MRR, seats, limits)
- **Change status** — active / trial / suspended / churned (trials excluded from MRR)
- **Impersonate for support** — one click issues a support session into a tenant, logged in their audit trail
- **Delete tenant** — cascade-removes all tenant data

Platform login: **super@secops.ai / superpassword**

## 2. SOC 2 Readiness Workflow (full Trust Services Criteria)
- **47 criteria** across all 5 Trust Service Categories:
  Security (33 Common Criteria CC1-CC9), Availability, Confidentiality,
  Processing Integrity, Privacy
- **Type I vs Type II** selection with observation period for Type II
- **Trust category picker** — Security mandatory, others optional add-ons
- **Auto-gap detection** — open governance findings are automatically mapped to the
  criteria they affect and flagged as gaps at setup
- **Per-criterion readiness tracking** — not started / in progress / ready / gap
- **Readiness scoring** — overall % + breakdown by trust category
- Accessible from the **SOC 2** sidebar item

## New backend
- models/platform.py (PlatformAdmin, TenantBilling, PLAN_DEFAULTS)
- models/soc2.py (SOC2Readiness, SOC2CriterionStatus)
- core/platform_security.py (separate super-admin JWT scope)
- frameworks/soc2_criteria.py (full TSC)
- api/routes/platform.py, api/routes/soc2.py

## New frontend
- app/platform/page.tsx (console + login)
- app/(app)/soc2/page.tsx (readiness workflow)

## Apply this update
docker compose down -v
docker compose up --build -d
sleep 25
docker compose exec backend python seed.py

The seed now creates: the platform admin, billing records, and a 2nd demo tenant
(HealthTrust Medical) so the platform console has multiple tenants to manage.
