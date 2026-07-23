"""
Microsoft SQL Server Database Config-Assessment Connector.

COMPLIANCE POSTURE ASSESSMENT for a SQL Server engine — aligned to the CIS
Microsoft SQL Server Benchmark areas that matter for audit: surface-area
configuration, authentication, encryption, and auditing. Produces GovernanceEvent
dicts (same shape as the other connectors), mapped to frameworks.

Settings are collected read-only by the agent (sys.configurations, sys.databases,
server properties) and shipped here for the checks.

Expected settings document (dict or JSON):
{
  "version": "15.0.2000",
  "settings": {
    "xp_cmdshell": 1,                 // dangerous: OS command execution
    "ole_automation_procedures": 0,
    "remote_admin_connections": 0,
    "cross_db_ownership_chaining": 0,
    "contained_database_authentication": 0,
    "clr_enabled": 1
  },
  "sa_account_enabled": true,          // built-in 'sa' account enabled
  "sa_account_renamed": false,
  "authentication_mode": "mixed",      // "windows" | "mixed"
  "force_encryption": false,           // ForceEncryption for connections
  "databases_without_tde": 3,          // user DBs without Transparent Data Encryption
  "login_auditing": "failed_only"      // "none"|"failed_only"|"success_and_failed"
}
"""
from datetime import datetime
from typing import List
import json


CHECK_CONTROLS = {
    "xp_cmdshell":         {"pci_dss": ["2.2.6"], "iso27001": ["A.8.9"], "soc2": ["CC6.1"], "nist_csf": ["pr_ip_1"]},
    "ole_automation":      {"pci_dss": ["2.2.6"], "iso27001": ["A.8.9"], "soc2": ["CC6.1"]},
    "clr_enabled":         {"pci_dss": ["2.2.6"], "iso27001": ["A.8.9"], "soc2": ["CC6.1"]},
    "cross_db_chaining":   {"pci_dss": ["7.2.1"], "iso27001": ["A.8.3"], "soc2": ["CC6.3"]},
    "sa_enabled":          {"pci_dss": ["8.3.1"], "iso27001": ["A.8.2"], "soc2": ["CC6.1"], "nist_csf": ["pr_ac_1"]},
    "sa_not_renamed":      {"pci_dss": ["8.3.1"], "iso27001": ["A.8.2"], "soc2": ["CC6.1"]},
    "mixed_auth":          {"pci_dss": ["8.3.1"], "iso27001": ["A.8.5"], "soc2": ["CC6.1"]},
    "no_force_encryption": {"pci_dss": ["4.2.1"], "iso27001": ["A.8.24"], "soc2": ["CC6.7"], "nist_csf": ["pr_ds_2"]},
    "no_tde":              {"pci_dss": ["3.4.1"], "iso27001": ["A.8.24"], "soc2": ["CC6.7"]},
    "login_auditing_weak": {"pci_dss": ["10.2.1"], "iso27001": ["A.8.15"], "soc2": ["CC7.2"]},
}
SEVERITY = {
    "xp_cmdshell": "critical", "ole_automation": "high", "clr_enabled": "medium",
    "cross_db_chaining": "medium", "sa_enabled": "high", "sa_not_renamed": "low",
    "mixed_auth": "medium", "no_force_encryption": "high", "no_tde": "high",
    "login_auditing_weak": "medium",
}
CATEGORY = {
    "xp_cmdshell": "config", "ole_automation": "config", "clr_enabled": "config",
    "cross_db_chaining": "access_control", "sa_enabled": "access_control",
    "sa_not_renamed": "access_control", "mixed_auth": "access_control",
    "no_force_encryption": "encryption", "no_tde": "encryption", "login_auditing_weak": "logging",
}


def _fw_map(check_key, framework_hint=None):
    controls = CHECK_CONTROLS.get(check_key, {})
    if framework_hint and framework_hint in controls:
        return {framework_hint: controls[framework_hint]}
    return dict(controls)


def _event(tenant_id, connector_id, check_key, title, detail, framework_hint, resource="mssql"):
    return {
        "tenant_id": tenant_id, "connector_id": connector_id,
        "title": title if len(title) <= 120 else title[:117] + "…",
        "description": detail, "severity": SEVERITY.get(check_key, "medium"),
        "category": CATEGORY.get(check_key, "config"), "source_type": "scheduled_scan",
        "framework_mappings": _fw_map(check_key, framework_hint),
        "raw_data": {"source": "mssql", "check": check_key, "resource": resource},
        "occurred_at": datetime.utcnow(), "status": "open",
    }


def _is_on(val) -> bool:
    return str(val).lower() in ("1", "on", "true", "yes", "enabled")


def assess_mssql_config(data, tenant_id: int, connector_id: int,
                        framework_hint: str = None) -> List[dict]:
    """Assess a SQL Server settings document and return GovernanceEvent dicts."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Could not parse SQL Server assessment JSON: {e}")
    if not isinstance(data, dict):
        raise RuntimeError("SQL Server assessment data must be a JSON object")

    s = data.get("settings", {})
    events = []

    # Surface-area / dangerous features
    if _is_on(s.get("xp_cmdshell", 0)):
        events.append(_event(tenant_id, connector_id, "xp_cmdshell",
            "xp_cmdshell is enabled",
            "'xp_cmdshell' allows OS command execution from SQL Server — a critical "
            "surface-area risk. Disable it unless absolutely required.", framework_hint))
    if _is_on(s.get("ole_automation_procedures", 0)):
        events.append(_event(tenant_id, connector_id, "ole_automation",
            "OLE Automation Procedures are enabled",
            "'Ole Automation Procedures' expand the attack surface; disable if unused.", framework_hint))
    if _is_on(s.get("clr_enabled", 0)):
        events.append(_event(tenant_id, connector_id, "clr_enabled",
            "CLR integration is enabled",
            "'clr enabled' allows managed code execution in the engine; disable unless needed.", framework_hint))
    if _is_on(s.get("cross_db_ownership_chaining", 0)):
        events.append(_event(tenant_id, connector_id, "cross_db_chaining",
            "Cross-database ownership chaining is enabled",
            "Cross-DB ownership chaining can bypass access controls between databases; disable.", framework_hint))

    # Authentication
    if data.get("sa_account_enabled") is True:
        events.append(_event(tenant_id, connector_id, "sa_enabled",
            "Built-in 'sa' account is enabled",
            "The 'sa' account is a well-known target. Disable it, or at minimum rename "
            "it and enforce a strong password.", framework_hint))
    if data.get("sa_account_renamed") is False:
        events.append(_event(tenant_id, connector_id, "sa_not_renamed",
            "Built-in 'sa' account has not been renamed",
            "The 'sa' account still uses its default name, easing brute-force targeting.", framework_hint))
    if str(data.get("authentication_mode", "")).lower() == "mixed":
        events.append(_event(tenant_id, connector_id, "mixed_auth",
            "Mixed-mode authentication is enabled",
            "SQL Server is in Mixed Mode; Windows Authentication is preferred where "
            "possible to reduce credential exposure.", framework_hint))

    # Encryption
    if data.get("force_encryption") is False:
        events.append(_event(tenant_id, connector_id, "no_force_encryption",
            "Force Encryption is not enabled",
            "Connections are not forced to use encryption — data in transit may be "
            "unprotected. Enable ForceEncryption.", framework_hint))
    if int(data.get("databases_without_tde", 0) or 0) > 0:
        events.append(_event(tenant_id, connector_id, "no_tde",
            f"{data['databases_without_tde']} database(s) without Transparent Data Encryption",
            "User databases lack TDE — data at rest is unencrypted. Enable TDE where "
            "the data sensitivity requires encryption at rest.", framework_hint))

    # Auditing
    if str(data.get("login_auditing", "")).lower() in ("none", ""):
        events.append(_event(tenant_id, connector_id, "login_auditing_weak",
            "Login auditing is not capturing failed logins",
            "Login auditing is set to 'none' — failed logins aren't recorded, weakening "
            "the audit trail. Audit at least failed logins.", framework_hint))

    return events
