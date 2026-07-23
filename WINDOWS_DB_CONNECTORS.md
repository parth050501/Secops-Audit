# Windows + PostgreSQL Config-Assessment Connectors

Both are COMPLIANCE POSTURE assessment (not monitoring/SIEM), same pattern as the
others: collect read-only settings → APE applies checks → map to controls →
governance events. Both work standalone now (testable in your lab) and will be
delivered by the agent for on-prem systems later.

## Windows Server  (connector type: windows_server)
- app/connectors/windows_server.py — assess_windows_config() + run_windows_scan()
- Companion collector: app/connectors/secops-win-assess.ps1 (read-only PowerShell)
- Checks: password policy (length/complexity/age/history), account lockout,
  audit policy (logon failures, policy change), SMBv1, RDP NLA, Guest account,
  LM hash storage, insecure services (Telnet/FTP), Windows Firewall profiles.
- Mapped to PCI/ISO/SOC2/NIST control IDs.
- TEST NOW: run secops-win-assess.ps1 on a real Windows box (as admin), it emits
  JSON; feed that JSON to the connector (paste in the UI or via assessment_json).
- Approach: PowerShell-based (free, in our control). The script only COLLECTS;
  all compliance logic is in the APE, so checks change without touching agents.

## PostgreSQL  (connector type: postgres)
- app/connectors/postgres_db.py — assess_postgres_config() + run_postgres_scan()
- Checks (CIS PostgreSQL areas): SSL/TLS enabled, connection/disconnection/
  statement logging, logging_collector, password_encryption (md5 vs scram),
  pg_hba 'trust' auth, excess superusers, world-writable public schema.
- Assesses the DATABASE ENGINE config (distinct from cloud RDS infra checks).
- TEST NOW: collect settings via read-only queries (SHOW / pg_settings) into the
  expected JSON shape (see file docstring), feed to the connector.

## Wired into scan dispatch
REAL_SERVER now includes windows_server; REAL_DB includes postgres. Both produce
the standard GovernanceEvent shape, so tickets/evidence/reports work unchanged.

## Still pending (honest)
- Live direct querying for postgres (connect + run queries from platform) — for
  on-prem this is the agent's job; direct mode can be added where DB is reachable.
- Other DB engines (SQL Server, Oracle, MySQL) — build on demand per buyer need.
- macOS / AIX servers — build on demand.
- These connectors need the AGENT for behind-firewall delivery (the logic is done
  and testable now; delivery to customer-internal systems is the collector/agent).
