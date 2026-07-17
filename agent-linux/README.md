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

## Database scanning (Postgres, MySQL, MSSQL)

The one agent can scan the local OS **and** databases it can reach (local or
remote), by connecting read-only. Set `SCAN_SYSTEMS` to include the databases,
and provide connection details via environment variables.

Install the client library for each database you'll scan:
    pip install pymysql pymssql psycopg2-binary   # only those you need

Enable in the agent config (comma list):
    SCAN_SYSTEMS=linux,postgres,mysql,mssql

Connection env vars per database (read-only credentials):

  Postgres:
    PGHOST, PGPORT (5432), PGUSER, PGPASSWORD, PGDATABASE

  MySQL / MariaDB:
    MYSQL_HOST, MYSQL_PORT (3306), MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

  MSSQL (SQL Server):
    MSSQL_HOST, MSSQL_PORT (1433), MSSQL_USER, MSSQL_PASSWORD, MSSQL_DATABASE (master)

The database can be on the same host as the agent OR on a different host the
agent can reach — set the *_HOST accordingly. Use a dedicated read-only account
for scanning; the agent only runs read-only queries (settings/catalog metadata).

Findings from each database are mapped to the same compliance controls as
everything else and appear in Governance/Compliance like any other finding.
