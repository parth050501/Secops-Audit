# CodeCore Windows Agent

Runs on an internal Windows system. Performs the read-only PowerShell compliance
assessment locally and submits the result to the collector (CCE), which relays it
to the platform.

    Windows Agent (assesses this host) --> Collector/CCE (relay) --> Platform

## What it scans
Runs secops-win-assess.ps1 (bundled): password policy, account lockout, audit
policy, SMBv1, RDP NLA, Guest account, LM hash, insecure services, firewall.
Read-only — makes no changes.

## Deploy inputs
- COLLECTOR_URL   collector's agent endpoint, e.g. http://10.0.0.10:8514
- ENROLL_SECRET   the shared secret configured on that collector
- AGENT_NAME      label (defaults to hostname)

## Install (run PowerShell as Administrator)
    .\install.ps1
    notepad C:\ProgramData\CodeCore\agent.conf    # set collector_url + enroll_secret
    # test once:
    cd 'C:\Program Files\CodeCoreAgent'; python -m codecore_agent.agent --once
A daily scheduled task ("CodeCoreAgent") is registered at 2 AM.

## Requirements
- Python 3 + requests (install.ps1 installs requests)
- PowerShell (built in). Run the assessment as Administrator for full coverage.

## Why not Docker
Windows containers are awkward for host-level assessment; the agent runs natively
as a small Python program driven by a scheduled task. (The Linux agent is Docker/
systemd; Windows is native — each suits its platform.)

## Security
- Read-only assessment; agent token stored under C:\ProgramData\CodeCore.
- Talks only to the collector on the internal network.

## Version 0.1.0
