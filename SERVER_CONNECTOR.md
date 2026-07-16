# Linux Server Connector (OpenSCAP)

Audit-grade server compliance scanning via OpenSCAP — maps directly to recognized
benchmarks (CIS, DISA STIG, PCI-DSS profiles), which is what auditors expect.

## How it works
- The connector runs `oscap xccdf eval` against a Linux server using a SCAP
  datastream (SCAP Security Guide content), producing XCCDF results.
- Each FAILED rule becomes a GovernanceEvent, mapped to your active framework,
  with the rule's CCE/ident references as control identifiers.
- Same provider-agnostic pattern as the Prowler cloud connectors — everything
  downstream (tickets, evidence, reports) works unchanged.

## What's testable NOW (no agent needed)
The detection + parsing + mapping is fully testable today, the same way we
tested AWS:
1. On any Linux box you control (a VM, or a cheap cloud server), install:
   `apt-get install openscap-scanner ssg-debderived`  (Debian/Ubuntu)
   or `yum install openscap-scanner scap-security-guide`  (RHEL/CentOS)
2. Run a real scan:
   `oscap xccdf eval --profile <profile> --results results.xml <datastream>`
3. The adapter's `parse_openscap_xccdf()` turns that real results.xml into
   mapped governance events. Point it at your real output and verify — exactly
   like we did with Prowler's OCSF output.

Tested in development against representative XCCDF output: failed rules parse,
severities map, categories derive, CCE idents captured, passing rules skipped.

## What needs the COLLECTOR/AGENT (later)
To scan a customer's server that sits BEHIND THEIR FIREWALL, the scan has to run
INSIDE their environment. That's the collector/agent's job: it runs `oscap`
locally on the target and ships the XCCDF results back to the platform, where
`parse_openscap_xccdf()` ingests them.
- `run_openscap_scan()` is what the agent will invoke.
- `parse_openscap_xccdf()` is the platform-side ingestion (runs on your server).
So: the detection/mapping is built and testable now; the behind-firewall
delivery is the agent, which is the next major build for real customer testing.

## In the Docker image
The backend Dockerfile now installs `openscap-scanner` + SCAP content, so the
platform can run scans directly (useful for hosts the platform can reach, and as
the basis the agent reuses).

## Connector fields (in the UI)
Linux connector now asks for: scan target (local/agent vs remote SSH), SCAP
profile (CIS L1/L2, PCI-DSS, STIG), and remote SSH details when applicable.

## Next on the "beyond cloud" path
- Network device connectors (Palo Alto / Fortinet / Cisco) — per-vendor config
  parsing + control mapping. You'll arrange real appliances to test against.
- The collector/agent — unlocks behind-firewall server + network scanning for
  real customer environments. This is the keystone for the live demos.
