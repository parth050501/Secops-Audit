"""
PostgreSQL Database Config-Assessment Connector.

COMPLIANCE POSTURE ASSESSMENT for a PostgreSQL database engine — aligned to the
CIS PostgreSQL Benchmark areas that matter for audit: logging/auditing settings,
authentication/encryption, access control, and dangerous configuration. Produces
GovernanceEvent dicts (same shape as the other connectors), mapped to frameworks.

This assesses the DATABASE ENGINE's internal configuration (distinct from the
cloud connector, which assesses managed-DB *infrastructure* like RDS encryption).

APPROACH: a read-only set of settings is collected from the database (the agent
runs read-only queries on-prem, or for a reachable DB the platform can query
directly) and this connector applies the compliance checks. The settings come
from PostgreSQL's own `SHOW`/pg_settings and a few catalog queries — all
read-only.

Expected settings document (dict or JSON), as produced by the collector:
{
  "version": "15.4",
  "settings": {
    "ssl": "off",
    "log_connections": "off",
    "log_disconnections": "off",
    "logging_collector": "on",
    "log_statement": "none",
    "password_encryption": "md5",
    "log_min_duration_statement": "-1"
  },
  "hba_allows_trust": true,            // any 'trust' auth method in pg_hba.conf
  "superuser_count": 3,                // number of roles with superuser
  "public_schema_world_writable": true
}
"""
from datetime import datetime
from typing import List
import json


CHECK_CONTROLS = {
    "ssl_disabled":         {"pci_dss": ["4.2.1"], "iso27001": ["A.8.24"], "soc2": ["CC6.7"], "nist_csf": ["pr_ds_2"]},
    "log_connections":      {"pci_dss": ["10.2.1"], "iso27001": ["A.8.15"], "soc2": ["CC7.2"]},
    "log_disconnections":   {"pci_dss": ["10.2.1"], "iso27001": ["A.8.15"], "soc2": ["CC7.2"]},
    "logging_collector":    {"pci_dss": ["10.2"], "iso27001": ["A.8.15"], "soc2": ["CC7.2"]},
    "log_statement":        {"pci_dss": ["10.2.2"], "iso27001": ["A.8.15"], "soc2": ["CC7.2"]},
    "weak_password_enc":    {"pci_dss": ["8.3.2"], "iso27001": ["A.8.24"], "soc2": ["CC6.1"]},
    "hba_trust":            {"pci_dss": ["7.2.1"], "iso27001": ["A.8.2"], "soc2": ["CC6.1"], "nist_csf": ["pr_ac_4"]},
    "excess_superusers":    {"pci_dss": ["7.2.2"], "iso27001": ["A.8.2"], "soc2": ["CC6.3"]},
    "public_writable":      {"pci_dss": ["7.2.1"], "iso27001": ["A.8.3"], "soc2": ["CC6.3"]},
}

SEVERITY = {
    "ssl_disabled": "high", "log_connections": "medium", "log_disconnections": "low",
    "logging_collector": "medium", "log_statement": "low", "weak_password_enc": "high",
    "hba_trust": "high", "excess_superusers": "medium", "public_writable": "medium",
}

CATEGORY = {
    "ssl_disabled": "encryption", "log_connections": "logging",
    "log_disconnections": "logging", "logging_collector": "logging",
    "log_statement": "logging", "weak_password_enc": "encryption",
    "hba_trust": "access_control", "excess_superusers": "access_control",
    "public_writable": "access_control",
}


def _fw_map(check_key, framework_hint=None):
    controls = CHECK_CONTROLS.get(check_key, {})
    if framework_hint and framework_hint in controls:
        return {framework_hint: controls[framework_hint]}
    return dict(controls)


def _event(tenant_id, connector_id, check_key, title, detail, framework_hint, resource="postgres"):
    return {
        "tenant_id": tenant_id,
        "connector_id": connector_id,
        "title": title if len(title) <= 120 else title[:117] + "…",
        "description": detail,
        "severity": SEVERITY.get(check_key, "medium"),
        "category": CATEGORY.get(check_key, "config"),
        "source_type": "scheduled_scan",
        "framework_mappings": _fw_map(check_key, framework_hint),
        "raw_data": {"source": "postgres", "check": check_key, "resource": resource},
        "occurred_at": datetime.utcnow(),
        "status": "open",
    }


def _is_off(val) -> bool:
    return str(val).lower() in ("off", "false", "0", "no", "")


def assess_postgres_config(data, tenant_id: int, connector_id: int,
                           framework_hint: str = None) -> List[dict]:
    """Assess a PostgreSQL settings document and return GovernanceEvent dicts."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Could not parse PostgreSQL assessment JSON: {e}")
    if not isinstance(data, dict):
        raise RuntimeError("PostgreSQL assessment data must be a JSON object")

    s = data.get("settings", {})
    events = []

    # Encryption in transit
    if "ssl" in s and _is_off(s["ssl"]):
        events.append(_event(tenant_id, connector_id, "ssl_disabled",
            "SSL/TLS is disabled on the database",
            "PostgreSQL 'ssl' is off — connections are unencrypted. Enable TLS so "
            "data in transit (including credentials) is protected.", framework_hint))

    # Logging / audit
    if "log_connections" in s and _is_off(s["log_connections"]):
        events.append(_event(tenant_id, connector_id, "log_connections",
            "Connection logging is disabled",
            "'log_connections' is off — successful/failed connections are not logged, "
            "weakening the audit trail.", framework_hint))
    if "log_disconnections" in s and _is_off(s["log_disconnections"]):
        events.append(_event(tenant_id, connector_id, "log_disconnections",
            "Disconnection logging is disabled",
            "'log_disconnections' is off.", framework_hint))
    if "logging_collector" in s and _is_off(s["logging_collector"]):
        events.append(_event(tenant_id, connector_id, "logging_collector",
            "Logging collector is disabled",
            "'logging_collector' is off — logs may not be reliably captured to disk.",
            framework_hint))
    if "log_statement" in s and str(s["log_statement"]).lower() in ("none", ""):
        events.append(_event(tenant_id, connector_id, "log_statement",
            "Statement logging is set to 'none'",
            "'log_statement' is 'none' — DDL/data-changing statements are not logged. "
            "Consider 'ddl' or 'mod' for an auditable trail.", framework_hint))

    # Password storage strength
    if "password_encryption" in s and str(s["password_encryption"]).lower() == "md5":
        events.append(_event(tenant_id, connector_id, "weak_password_enc",
            "Password encryption uses weak MD5",
            "'password_encryption' is md5 — use scram-sha-256 for stronger password "
            "hashing.", framework_hint))

    # Authentication: 'trust' in pg_hba allows passwordless access
    if data.get("hba_allows_trust") is True:
        events.append(_event(tenant_id, connector_id, "hba_trust",
            "pg_hba.conf permits 'trust' authentication",
            "A 'trust' auth method allows connections with no password. Remove trust "
            "rules except for tightly-scoped local cases.", framework_hint))

    # Excess superusers
    su = data.get("superuser_count")
    if isinstance(su, int) and su > 2:
        events.append(_event(tenant_id, connector_id, "excess_superusers",
            f"{su} roles have superuser privilege",
            f"{su} database roles hold superuser — least privilege suggests minimizing "
            f"this. Review and revoke where unnecessary.", framework_hint))

    # World-writable public schema
    if data.get("public_schema_world_writable") is True:
        events.append(_event(tenant_id, connector_id, "public_writable",
            "Public schema is world-writable",
            "The public schema grants CREATE to PUBLIC — revoke so users can't create "
            "objects in it by default.", framework_hint))

    return events


def run_postgres_scan(credentials: dict, tenant_id: int, connector_id: int) -> List[dict]:
    """
    Assess a PostgreSQL database's configuration.

    credentials may contain:
      - assessment_json : settings document from the collector (read-only queries)
      - framework       : platform framework key to scope mappings

    Live querying (connecting to the DB and running the read-only queries) is done
    by the agent on-prem and shipped as assessment_json. For testing now, paste a
    real settings document. (Direct live query support can be added where the DB
    is reachable from the platform.)
    """
    creds = credentials or {}
    data = creds.get("assessment_json")
    if not data:
        raise RuntimeError(
            "No PostgreSQL assessment data provided. Supply 'assessment_json' (the "
            "settings collected via read-only queries). On-prem the agent produces this."
        )
    return assess_postgres_config(data, tenant_id, connector_id,
                                  framework_hint=creds.get("framework"))
