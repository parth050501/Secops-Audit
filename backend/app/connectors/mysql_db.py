"""
MySQL / MariaDB Database Config-Assessment Connector.

COMPLIANCE POSTURE ASSESSMENT for a MySQL/MariaDB engine — aligned to the CIS
MySQL Benchmark areas that matter for audit: encryption in transit, logging/
auditing, authentication, and dangerous configuration. Produces GovernanceEvent
dicts (same shape as the other connectors), mapped to frameworks.

Assesses the DATABASE ENGINE's internal configuration. Settings are collected
read-only by the agent (SHOW VARIABLES / SHOW GLOBAL VARIABLES and a few catalog
queries) and shipped here for the checks.

Expected settings document (dict or JSON):
{
  "version": "8.0.34",
  "settings": {
    "require_secure_transport": "OFF",   // TLS required for connections
    "have_ssl": "DISABLED",
    "general_log": "OFF",
    "log_error": "/var/log/mysql/error.log",
    "local_infile": "ON",                // dangerous if ON
    "skip_name_resolve": "OFF",
    "sql_mode": "",
    "default_authentication_plugin": "mysql_native_password"
  },
  "users_with_no_password": 0,           // accounts with empty authentication_string
  "users_with_wildcard_host": 2,         // accounts usable from '%' (any host)
  "anonymous_users": 1                   // '' username accounts
}
"""
from datetime import datetime
from typing import List
import json


CHECK_CONTROLS = {
    "tls_not_required":   {"pci_dss": ["4.2.1"], "iso27001": ["A.8.24"], "soc2": ["CC6.7"], "nist_csf": ["pr_ds_2"]},
    "ssl_disabled":       {"pci_dss": ["4.2.1"], "iso27001": ["A.8.24"], "soc2": ["CC6.7"]},
    "general_log_off":    {"pci_dss": ["10.2"], "iso27001": ["A.8.15"], "soc2": ["CC7.2"]},
    "local_infile_on":    {"pci_dss": ["2.2.6"], "iso27001": ["A.8.9"], "soc2": ["CC6.1"]},
    "empty_password":     {"pci_dss": ["8.3.1"], "iso27001": ["A.8.5"], "soc2": ["CC6.1"], "nist_csf": ["pr_ac_1"]},
    "anonymous_users":    {"pci_dss": ["7.2.1"], "iso27001": ["A.8.2"], "soc2": ["CC6.1"]},
    "wildcard_host":      {"pci_dss": ["7.2.1"], "iso27001": ["A.8.2"], "soc2": ["CC6.3"], "nist_csf": ["pr_ac_4"]},
    "weak_auth_plugin":   {"pci_dss": ["8.3.2"], "iso27001": ["A.8.24"], "soc2": ["CC6.1"]},
}
SEVERITY = {
    "tls_not_required": "high", "ssl_disabled": "high", "general_log_off": "low",
    "local_infile_on": "medium", "empty_password": "critical", "anonymous_users": "high",
    "wildcard_host": "medium", "weak_auth_plugin": "medium",
}
CATEGORY = {
    "tls_not_required": "encryption", "ssl_disabled": "encryption", "general_log_off": "logging",
    "local_infile_on": "config", "empty_password": "access_control", "anonymous_users": "access_control",
    "wildcard_host": "access_control", "weak_auth_plugin": "encryption",
}


def _fw_map(check_key, framework_hint=None):
    controls = CHECK_CONTROLS.get(check_key, {})
    if framework_hint and framework_hint in controls:
        return {framework_hint: controls[framework_hint]}
    return dict(controls)


def _event(tenant_id, connector_id, check_key, title, detail, framework_hint, resource="mysql"):
    return {
        "tenant_id": tenant_id, "connector_id": connector_id,
        "title": title if len(title) <= 120 else title[:117] + "…",
        "description": detail, "severity": SEVERITY.get(check_key, "medium"),
        "category": CATEGORY.get(check_key, "config"), "source_type": "scheduled_scan",
        "framework_mappings": _fw_map(check_key, framework_hint),
        "raw_data": {"source": "mysql", "check": check_key, "resource": resource},
        "occurred_at": datetime.utcnow(), "status": "open",
    }


def _is_on(val) -> bool:
    return str(val).lower() in ("on", "true", "1", "yes", "enabled")

def _is_off(val) -> bool:
    return str(val).lower() in ("off", "false", "0", "no", "disabled", "")


def assess_mysql_config(data, tenant_id: int, connector_id: int,
                        framework_hint: str = None) -> List[dict]:
    """Assess a MySQL/MariaDB settings document and return GovernanceEvent dicts."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Could not parse MySQL assessment JSON: {e}")
    if not isinstance(data, dict):
        raise RuntimeError("MySQL assessment data must be a JSON object")

    s = data.get("settings", {})
    events = []

    # Encryption in transit
    if "require_secure_transport" in s and _is_off(s["require_secure_transport"]):
        events.append(_event(tenant_id, connector_id, "tls_not_required",
            "TLS is not required for database connections",
            "'require_secure_transport' is OFF — clients may connect without TLS, "
            "exposing data and credentials in transit. Require secure transport.", framework_hint))
    if "have_ssl" in s and _is_off(s["have_ssl"]):
        events.append(_event(tenant_id, connector_id, "ssl_disabled",
            "SSL/TLS is not available on the database",
            "'have_ssl' is DISABLED — the server has no TLS configured.", framework_hint))

    # Logging
    if "general_log" in s and _is_off(s["general_log"]):
        events.append(_event(tenant_id, connector_id, "general_log_off",
            "General query logging is disabled",
            "'general_log' is OFF. Note: general_log is verbose; audit logging via "
            "the audit plugin is preferred, but some audit trail should exist.", framework_hint))

    # Dangerous config
    if "local_infile" in s and _is_on(s["local_infile"]):
        events.append(_event(tenant_id, connector_id, "local_infile_on",
            "LOCAL INFILE is enabled",
            "'local_infile' is ON — allows loading local files, a known data-exfiltration "
            "and injection risk. Disable unless explicitly required.", framework_hint))

    # Weak auth plugin
    if str(s.get("default_authentication_plugin", "")).lower() == "mysql_native_password":
        events.append(_event(tenant_id, connector_id, "weak_auth_plugin",
            "Weak default authentication plugin",
            "Default auth plugin is 'mysql_native_password'; prefer "
            "'caching_sha2_password' for stronger credential handling.", framework_hint))

    # Account hygiene
    if int(data.get("users_with_no_password", 0) or 0) > 0:
        events.append(_event(tenant_id, connector_id, "empty_password",
            f"{data['users_with_no_password']} account(s) have no password",
            "One or more MySQL accounts have an empty authentication string — a "
            "critical access-control gap. Set strong passwords or remove them.", framework_hint))
    if int(data.get("anonymous_users", 0) or 0) > 0:
        events.append(_event(tenant_id, connector_id, "anonymous_users",
            f"{data['anonymous_users']} anonymous account(s) present",
            "Anonymous (empty-username) accounts exist — they allow unauthenticated "
            "access and should be removed.", framework_hint))
    if int(data.get("users_with_wildcard_host", 0) or 0) > 0:
        events.append(_event(tenant_id, connector_id, "wildcard_host",
            f"{data['users_with_wildcard_host']} account(s) allow any host ('%')",
            "Accounts usable from any host ('%') widen the attack surface; restrict "
            "host scope to known networks.", framework_hint))

    return events
