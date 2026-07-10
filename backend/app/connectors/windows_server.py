"""
Windows Server Config-Assessment Connector.

COMPLIANCE POSTURE ASSESSMENT for Windows — not endpoint AV, not log monitoring.
Evaluates whether a Windows server's security *configuration* aligns with
compliance controls (password policy, account lockout, audit policy, key
security options) and turns gaps into GovernanceEvent dicts (same shape as the
other connectors), mapped to frameworks.

APPROACH: PowerShell-based. A small assessment script runs on the Windows host
(via the agent, on-prem) and emits a JSON document describing the relevant
security settings. This connector ingests that JSON and applies compliance
checks. We author the checks here (in the APE), so adding/adjusting checks never
requires touching the agent — it just collects settings; the APE judges them.

The expected JSON shape (produced by the companion PowerShell collector script,
e.g. `secops-win-assess.ps1`):
{
  "hostname": "WIN-APP01",
  "os": "Windows Server 2022",
  "password_policy": {
    "min_length": 8, "complexity": true, "max_age_days": 90,
    "history_count": 24, "min_age_days": 1
  },
  "lockout_policy": { "threshold": 5, "duration_min": 15, "window_min": 15 },
  "audit_policy": {
    "logon": "Success and Failure", "account_logon": "Success and Failure",
    "policy_change": "Success", "privilege_use": "No Auditing"
  },
  "security_options": {
    "smbv1_enabled": false, "rdp_nla_required": true, "guest_account_enabled": false,
    "anonymous_sid_enumeration": false, "lm_hash_stored": false
  },
  "services": { "telnet_running": false, "ftp_running": true },
  "firewall": { "domain_profile": true, "private_profile": true, "public_profile": false }
}

All fields are optional — the connector only checks what's present, so partial
collections still produce useful findings.
"""
from datetime import datetime
from typing import List
import json


# Each check → frameworks + representative control IDs it evidences.
CHECK_CONTROLS = {
    "pw_min_length":        {"pci_dss": ["8.3.6"], "iso27001": ["A.5.17"], "soc2": ["CC6.1"], "nist_csf": ["pr_ac_1"]},
    "pw_complexity":        {"pci_dss": ["8.3.6"], "iso27001": ["A.5.17"], "soc2": ["CC6.1"]},
    "pw_max_age":           {"pci_dss": ["8.3.9"], "iso27001": ["A.5.17"], "soc2": ["CC6.1"]},
    "pw_history":           {"pci_dss": ["8.3.7"], "iso27001": ["A.5.17"]},
    "lockout_threshold":    {"pci_dss": ["8.3.4"], "iso27001": ["A.8.5"], "soc2": ["CC6.1"], "nist_csf": ["pr_ac_7"]},
    "audit_logon":          {"pci_dss": ["10.2.1"], "iso27001": ["A.8.15"], "soc2": ["CC7.2"], "nist_csf": ["de_ae_3"]},
    "audit_policy_change":  {"pci_dss": ["10.2.1"], "iso27001": ["A.8.15"], "soc2": ["CC7.2"]},
    "smbv1":                {"pci_dss": ["2.2.5"], "iso27001": ["A.8.20"], "soc2": ["CC6.6"]},
    "rdp_nla":              {"pci_dss": ["2.2.5"], "iso27001": ["A.8.5"], "soc2": ["CC6.6"]},
    "guest_account":        {"pci_dss": ["8.2.2"], "iso27001": ["A.5.16"], "soc2": ["CC6.2"]},
    "lm_hash":              {"pci_dss": ["8.3.2"], "iso27001": ["A.8.24"], "soc2": ["CC6.1"]},
    "insecure_service":     {"pci_dss": ["2.2.4"], "iso27001": ["A.8.9"], "soc2": ["CC6.6"]},
    "firewall_profile":     {"pci_dss": ["1.2.1"], "iso27001": ["A.8.20"], "soc2": ["CC6.6"]},
}

SEVERITY = {
    "pw_min_length": "medium", "pw_complexity": "medium", "pw_max_age": "low",
    "pw_history": "low", "lockout_threshold": "medium", "audit_logon": "high",
    "audit_policy_change": "medium", "smbv1": "high", "rdp_nla": "high",
    "guest_account": "high", "lm_hash": "high", "insecure_service": "medium",
    "firewall_profile": "medium",
}

CATEGORY = {
    "pw_min_length": "identity", "pw_complexity": "identity", "pw_max_age": "identity",
    "pw_history": "identity", "lockout_threshold": "access_control",
    "audit_logon": "logging", "audit_policy_change": "logging",
    "smbv1": "network_security", "rdp_nla": "access_control",
    "guest_account": "access_control", "lm_hash": "encryption",
    "insecure_service": "network_security", "firewall_profile": "network_security",
}


def _fw_map(check_key, framework_hint=None):
    controls = CHECK_CONTROLS.get(check_key, {})
    if framework_hint and framework_hint in controls:
        return {framework_hint: controls[framework_hint]}
    return dict(controls)


def _event(tenant_id, connector_id, check_key, title, detail, framework_hint, host=""):
    return {
        "tenant_id": tenant_id,
        "connector_id": connector_id,
        "title": title if len(title) <= 120 else title[:117] + "…",
        "description": detail,
        "severity": SEVERITY.get(check_key, "medium"),
        "category": CATEGORY.get(check_key, "config"),
        "source_type": "scheduled_scan",
        "framework_mappings": _fw_map(check_key, framework_hint),
        "raw_data": {"source": "windows", "check": check_key, "host": host},
        "occurred_at": datetime.utcnow(),
        "status": "open",
    }


def assess_windows_config(data, tenant_id: int, connector_id: int,
                          framework_hint: str = None) -> List[dict]:
    """Assess a Windows settings document (dict or JSON string) and return
    GovernanceEvent dicts for each compliance gap."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Could not parse Windows assessment JSON: {e}")
    if not isinstance(data, dict):
        raise RuntimeError("Windows assessment data must be a JSON object")

    host = data.get("hostname", "windows-host")
    events = []

    # ── Password policy ──
    pp = data.get("password_policy", {})
    if "min_length" in pp and pp["min_length"] < 8:
        events.append(_event(tenant_id, connector_id, "pw_min_length",
            f"Password minimum length is {pp['min_length']} (below 8)",
            f"Minimum password length on {host} is {pp['min_length']}; compliance "
            f"baselines require at least 8.", framework_hint, host))
    if pp.get("complexity") is False:
        events.append(_event(tenant_id, connector_id, "pw_complexity",
            "Password complexity is not enforced",
            f"Password complexity requirements are disabled on {host}.",
            framework_hint, host))
    if "max_age_days" in pp and (pp["max_age_days"] == 0 or pp["max_age_days"] > 90):
        events.append(_event(tenant_id, connector_id, "pw_max_age",
            f"Password maximum age is {pp['max_age_days']} days",
            f"Password max age on {host} is {pp['max_age_days']} (0 = never expires); "
            f"baselines expect <= 90 days.", framework_hint, host))
    if "history_count" in pp and pp["history_count"] < 24:
        events.append(_event(tenant_id, connector_id, "pw_history",
            f"Password history is {pp['history_count']} (below 24)",
            f"Password history on {host} remembers {pp['history_count']} passwords; "
            f"baselines expect 24.", framework_hint, host))

    # ── Lockout ──
    lp = data.get("lockout_policy", {})
    if "threshold" in lp and (lp["threshold"] == 0 or lp["threshold"] > 10):
        events.append(_event(tenant_id, connector_id, "lockout_threshold",
            f"Account lockout threshold is {lp['threshold']}",
            f"Lockout threshold on {host} is {lp['threshold']} (0 = no lockout); "
            f"baselines expect a low non-zero value (e.g. <= 5-10).", framework_hint, host))

    # ── Audit policy ──
    ap = data.get("audit_policy", {})
    if "logon" in ap and "failure" not in ap["logon"].lower():
        events.append(_event(tenant_id, connector_id, "audit_logon",
            "Logon failure auditing is not enabled",
            f"Logon auditing on {host} is '{ap['logon']}' — failures must be audited "
            f"for the audit trail.", framework_hint, host))
    if "policy_change" in ap and ap["policy_change"].lower() in ("no auditing", "none", ""):
        events.append(_event(tenant_id, connector_id, "audit_policy_change",
            "Policy-change auditing is not enabled",
            f"Policy-change auditing on {host} is disabled.", framework_hint, host))

    # ── Security options ──
    so = data.get("security_options", {})
    if so.get("smbv1_enabled") is True:
        events.append(_event(tenant_id, connector_id, "smbv1",
            "SMBv1 is enabled (insecure legacy protocol)",
            f"SMBv1 is enabled on {host}; it is insecure and should be disabled.",
            framework_hint, host))
    if so.get("rdp_nla_required") is False:
        events.append(_event(tenant_id, connector_id, "rdp_nla",
            "RDP does not require Network Level Authentication",
            f"RDP on {host} allows connections without NLA, weakening access control.",
            framework_hint, host))
    if so.get("guest_account_enabled") is True:
        events.append(_event(tenant_id, connector_id, "guest_account",
            "Built-in Guest account is enabled",
            f"The Guest account is enabled on {host}; it should be disabled.",
            framework_hint, host))
    if so.get("lm_hash_stored") is True:
        events.append(_event(tenant_id, connector_id, "lm_hash",
            "LM password hashes are stored (weak hashing)",
            f"{host} stores LM hashes, which are cryptographically weak. Disable.",
            framework_hint, host))

    # ── Services ──
    svc = data.get("services", {})
    for key, label in (("telnet_running", "Telnet"), ("ftp_running", "FTP")):
        if svc.get(key) is True:
            events.append(_event(tenant_id, connector_id, "insecure_service",
                f"Insecure service running: {label}",
                f"{label} service is running on {host}; prefer encrypted alternatives "
                f"(SSH/SFTP/HTTPS).", framework_hint, host))

    # ── Firewall ──
    fw = data.get("firewall", {})
    for prof in ("domain_profile", "private_profile", "public_profile"):
        if fw.get(prof) is False:
            events.append(_event(tenant_id, connector_id, "firewall_profile",
                f"Windows Firewall disabled on {prof.replace('_',' ')}",
                f"Windows Firewall is off for the {prof.replace('_profile','')} profile "
                f"on {host}.", framework_hint, host))

    return events


def run_windows_scan(credentials: dict, tenant_id: int, connector_id: int) -> List[dict]:
    """
    Assess a Windows server's configuration.

    credentials may contain:
      - assessment_json : the JSON document from the PowerShell collector script
                          (uploaded for testing, or sent by the agent on-prem)
      - framework       : platform framework key to scope mappings

    On-prem, the agent runs the PowerShell collector locally and the result flows
    in as assessment_json. For testing now, paste/upload a real assessment JSON.
    """
    creds = credentials or {}
    data = creds.get("assessment_json")
    if not data:
        raise RuntimeError(
            "No Windows assessment data provided. Supply 'assessment_json' from the "
            "PowerShell collector script. On-prem this is produced by the agent."
        )
    return assess_windows_config(data, tenant_id, connector_id,
                                 framework_hint=creds.get("framework"))
