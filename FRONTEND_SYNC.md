# Frontend Sync — UI caught up to backend

This commit brings the frontend in line with backend features that previously
had no UI. Verified: `npm run build` succeeds; /evidence and /users routes build.

## Added UI
1. **Evidence & Attestations page** (`/evidence`)
   - Upload documents and record attestations against framework controls
   - Coverage summary (readiness %, controls tracked, satisfied, evidence count)
   - Framework switcher (SOC2/ISO/PCI/HIPAA/NIST)
   - Role-aware: read-only roles (auditor) see evidence but no action buttons

2. **Team / Users page** (`/users`)
   - Tenant admins add/remove users and set roles (admin/manager/engineer/auditor)
   - Non-admins see the roster read-only
   - Temporary-password-on-add (matches backend)

3. **Role-based UI hiding**
   - Sidebar filters items by role (Settings = admin only)
   - Connectors "Add Connector" hidden for read-only roles
   - Evidence + Users pages hide actions based on role
   - NOTE: this is UX polish; the BACKEND already enforces all of it (an auditor
     hitting a hidden action via API still gets 403). UI hiding ≠ security; the
     server is the source of truth.

## Still pending (UI)
- **Platform console "Team" tab** — the BACKEND for platform-staff management
  (super_admin/admin/analyst/read_only) is done + tested, but the UI tab inside
  /platform to manage internal staff is NOT built yet. For now, manage platform
  team via the API. (Tracked: row 32, UI pending.)
- Per-control coverage detail view, document template library, comprehensive
  audit report (rows 13–15).

## Build verification
cd frontend && npm install && npm run build   # succeeds; all routes compile
