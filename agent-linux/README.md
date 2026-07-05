# CodeCore Linux Agent

Runs on an internal Linux system. Performs read-only compliance scans locally
and submits raw results to the collector (CCE), which relays them to the platform.

    Linux Agent (scans this host) --> Collector/CCE (relay) --> Platform (parse+map)

## What it scans
- linux    : OpenSCAP (oscap) CIS/STIG/PCI benchmark -> results XML
- postgres : a Postgres on/reachable from this host (read-only settings)
Add more by registering scanners in codecore_agent/scanners/.

## Deploy inputs
- COLLECTOR_URL   the collector's agent endpoint, e.g. http://10.0.0.10:8514
- ENROLL_SECRET   the shared secret configured on that collector
- AGENT_NAME      label (defaults to hostname)
- SCAN_SYSTEMS    comma list, e.g. "linux" or "linux,postgres"

## Install
    sudo ./install.sh
    sudo nano /etc/codecore/agent.conf      # set collector_url + enroll_secret
    # run once now:
    sudo python3 -m codecore_agent.agent --once
    # or schedule daily:
    sudo systemctl daemon-reload && sudo systemctl enable --now codecore-agent.timer

## Requirements
- Python 3 + requests (installed by install.sh)
- For linux scans: oscap + scap-security-guide
      Ubuntu/Debian:  sudo apt-get install libopenscap8 ssg-debian ssg-applications
      RHEL/Rocky:     sudo dnf install openscap-scanner scap-security-guide
  Pick the benchmark with OSCAP_PROFILE / OSCAP_DATASTREAM if needed.
- For postgres scans: pip3 install psycopg2-binary, and set
      PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE  (use a read-only role)

## How it works
1. First run: enrolls with the collector using ENROLL_SECRET, receives an agent
   token, stores it at /var/lib/codecore-agent/state.json (0600).
2. Each run: executes the configured scans, submits raw output to the collector.
3. The collector forwards to the platform; findings appear in the tenant.

## Security
- Read-only scans; least-privilege.
- Agent token stored 0600; never logged.
- Talks only to the collector on the internal network — no direct internet needed.

## Modes
- `--once`  : run once and exit (used by the systemd timer / cron)
- default   : loop on SCAN_INTERVAL seconds (default 86400 = daily)

## Version 0.1.0
