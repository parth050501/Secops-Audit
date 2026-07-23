# Access Model — Platform & Tenant Roles

Two independent role systems.

## Platform layer (your MSSP team — /platform console)
| Capability | super_admin | admin | analyst | read_only |
|---|---|---|---|---|
| View all tenants & data | yes | yes | yes | yes |
| Work inside tenants (scans/findings/tickets) | yes | yes | yes | no |
| Impersonate tenant for support | yes | yes | yes | no |
| Onboard / delete tenants | yes | yes | no | no |
| Manage internal team | yes | yes | no | no |
| Change billing / plans | yes | no | no | no |

- Only a super_admin can create or promote another super_admin.
- The last super_admin cannot be removed or demoted (safety guard).
- New team members get a temporary password (set by whoever adds them) and
  should change it on first login. (Email invites = later, needs email service.)

Enforcement: app/core/platform_security.py (capability matrix + require_capability).
Endpoints: GET/POST/PATCH/DELETE /api/platform/team
Tested: tests/test_platform_roles.py (18 checks, all passing).

## Tenant layer (each client's own team — scoped to their tenant)
| Role | Access |
|---|---|
| admin | full access in their tenant, incl. managing their users |
| manager | review/approve tickets, compliance workflow |
| engineer | work on findings/tickets |
| auditor | READ-ONLY access to that tenant's compliance data & reports |

- Only a tenant admin can add/remove/change users in their tenant.
- The client decides whether to add an auditor user — it's their choice.
- Last admin cannot be removed/demoted.
- All operations strictly tenant-scoped (a tenant admin can never touch another
  tenant's users) — enforced via tenant_guard.

Endpoints: GET/POST/PATCH/DELETE /api/users

## Your super-user
Seeded: super@secops.ai / superpassword (role: super_admin)
From the platform console you can onboard tenants and add internal team members
with their roles. Inside each tenant, that tenant's admin manages their own team.

## Pending (UI)
The backend + enforcement + tests are done. Still to build:
- Platform console "Team" tab (add/remove internal staff, set roles)
- Tenant "Users" tab (client admin manages their team, incl. auditor)
