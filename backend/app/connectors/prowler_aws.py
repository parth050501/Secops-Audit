"""
Prowler AWS Connector Adapter.
Runs Prowler against a real AWS account (using credentials from the connector),
parses its OCSF JSON output, and translates each FAILED finding into a
GovernanceEvent dict — the same shape the simulator produces, so everything
downstream (control mapping, tickets, reports) works unchanged.

Prowler: https://github.com/prowler-cloud/prowler  (Apache-2.0)
"""
import os
import json
import glob
import tempfile
import subprocess
from datetime import datetime
from typing import List

# Map Prowler's OCSF severity strings to our severities
SEVERITY_MAP = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "informational": "low",
}

# Map Prowler's category tags to our governance categories
CATEGORY_MAP = {
    "identity-access": "identity",
    "trust-boundaries": "access_control",
    "logging": "logging",
    "encryption": "encryption",
    "data-protection": "data_protection",
    "network-security": "network_security",
    "configuration": "config",
    "secrets-management": "data_protection",
    "incident-response": "logging",
    "threat-detection": "logging",
    "backup": "availability",
    "resilience": "availability",
}

# Map Prowler's compliance framework KEYS → our platform framework keys.
# Prowler emits many; we map the ones our platform supports.
PROWLER_FRAMEWORK_MAP = {
    "PCI-4.0":          "pci_dss",
    "PCI-3.2.1":        "pci_dss",
    "HIPAA":            "hipaa",
    "ISO27001-2022":    "iso27001",
    "ISO27001-2013":    "iso27001",
    "NIST-CSF-2.0":     "nist_csf",
    "NIST-CSF-1.1":     "nist_csf",
    "SOC2":             "soc2",
    "SOC2-2017":        "soc2",
}


def _service_to_category(event_code: str, categories: list) -> str:
    """Derive our governance category from Prowler categories or check name."""
    for c in categories or []:
        if c in CATEGORY_MAP:
            return CATEGORY_MAP[c]
    # Fall back to inferring from the check's service prefix
    code = (event_code or "").lower()
    if code.startswith(("iam", "accessanalyzer")): return "identity"
    if code.startswith(("cloudtrail", "cloudwatch", "config")): return "logging"
    if code.startswith(("ec2", "vpc", "networkfirewall", "elb")): return "network_security"
    if code.startswith(("s3", "rds", "dynamodb")): return "data_protection"
    if code.startswith(("kms",)): return "encryption"
    if code.startswith(("backup",)): return "availability"
    return "config"


def _extract_framework_mappings(compliance: dict) -> dict:
    """Translate Prowler's compliance dict into our {framework_key: [control_ids]} form."""
    result = {}
    for prowler_key, control_ids in (compliance or {}).items():
        our_key = PROWLER_FRAMEWORK_MAP.get(prowler_key)
        if our_key and control_ids:
            # Merge if multiple Prowler keys map to same framework (e.g. ISO 2013 + 2022)
            existing = set(result.get(our_key, []))
            existing.update(control_ids)
            result[our_key] = sorted(existing)
    return result


def _extract_resource(finding: dict) -> str:
    """Pull the affected resource identifier from an OCSF finding."""
    resources = finding.get("resources") or []
    if resources and isinstance(resources, list):
        r = resources[0]
        return r.get("uid") or r.get("name") or r.get("type") or ""
    # Some versions nest under 'resource'
    res = finding.get("resource") or {}
    return res.get("uid") or res.get("name") or ""


def parse_prowler_ocsf(json_path: str, tenant_id: int, connector_id: int) -> List[dict]:
    """Parse a Prowler OCSF JSON file into GovernanceEvent dicts (FAILED findings only).

    Dedup strategy: collapse on (check_id, resource). When the same check appears
    multiple times (Prowler emits one record per compliance framework it maps to),
    we merge all framework mappings into a single event and keep the highest severity,
    so each real finding appears exactly once.
    """
    with open(json_path) as f:
        findings = json.load(f)

    SEV_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    by_key = {}  # (check_id, resource) -> event dict

    for finding in findings:
        if str(finding.get("status_code", "")).upper() != "FAIL":
            continue

        meta = finding.get("metadata", {}) or {}
        event_code = meta.get("event_code", "")
        unmapped = finding.get("unmapped", {}) or {}
        categories = unmapped.get("categories", [])
        compliance = unmapped.get("compliance", {})

        title = finding.get("status_detail") or finding.get("message") or event_code
        resource = _extract_resource(finding)
        key = (event_code, resource)

        severity = SEVERITY_MAP.get(str(finding.get("severity", "medium")).lower(), "medium")
        category = _service_to_category(event_code, categories)
        framework_mappings = _extract_framework_mappings(compliance)
        clean_title = title if len(title) <= 120 else title[:117] + "…"

        if key in by_key:
            # Merge into the existing event for this check+resource
            existing = by_key[key]
            # Keep the higher severity
            if SEV_RANK.get(severity, 0) > SEV_RANK.get(existing["severity"], 0):
                existing["severity"] = severity
            # Merge framework mappings (union of control IDs per framework)
            for fw, ctrls in framework_mappings.items():
                merged = set(existing["framework_mappings"].get(fw, []))
                merged.update(ctrls)
                existing["framework_mappings"][fw] = sorted(merged)
            continue

        by_key[key] = {
            "tenant_id":    tenant_id,
            "connector_id": connector_id,
            "title":        clean_title,
            "description":  finding.get("status_detail") or finding.get("message") or "",
            "severity":     severity,
            "category":     category,
            "source_type":  "scheduled_scan",
            "framework_mappings": framework_mappings,
            "raw_data": {
                "source": "prowler",
                "check_id": event_code,
                "resource": resource,
                "prowler_severity": finding.get("severity"),
                "remediation_urls": unmapped.get("additional_urls", [])[:3],
            },
            "occurred_at":  datetime.utcnow(),
            "status":       "open",
        }

    return list(by_key.values())


def run_prowler_scan(credentials: dict, tenant_id: int, connector_id: int) -> List[dict]:
    """
    Run Prowler against a real AWS account using the connector's credentials,
    then parse the output into GovernanceEvent dicts.

    credentials may contain:
      - access_key_id, secret_access_key   (Access Key auth)
      - regions  (comma-separated, optional)
    Returns a list of event dicts. Raises RuntimeError on scan failure.
    """
    creds = credentials or {}
    env = os.environ.copy()

    access_key = creds.get("access_key_id")
    secret_key = creds.get("secret_access_key")
    if access_key and secret_key:
        env["AWS_ACCESS_KEY_ID"] = access_key
        env["AWS_SECRET_ACCESS_KEY"] = secret_key
    # If neither provided, Prowler will use the host's default credential chain
    # (useful in dev when AWS_* env vars are already set).

    region = (creds.get("regions") or "").split(",")[0].strip() or "us-east-1"
    env["AWS_DEFAULT_REGION"] = region

    out_dir = tempfile.mkdtemp(prefix="prowler_")
    cmd = ["prowler", "aws", "-M", "json-ocsf", "--output-directory", out_dir,
           "--ignore-exit-code-3"]
    # Optional: scope to specific regions to speed up scans
    region_list = [r.strip() for r in (creds.get("regions") or "").split(",") if r.strip()]
    if region_list:
        cmd += ["-f"] + region_list

    try:
        # Prowler can take several minutes; cap at 20 to avoid hanging forever
        result = subprocess.run(cmd, env=env, capture_output=True, timeout=1200, check=False)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Prowler scan timed out after 20 minutes")
    except FileNotFoundError:
        raise RuntimeError("Prowler is not installed in this environment")

    # Find the OCSF JSON Prowler wrote
    matches = glob.glob(os.path.join(out_dir, "*.ocsf.json"))
    if not matches:
        # Surface Prowler's own error output so the failure is debuggable
        err = (result.stderr or b"").decode(errors="replace")[-500:]
        out = (result.stdout or b"").decode(errors="replace")[-300:]
        raise RuntimeError(
            f"Prowler produced no output (exit {result.returncode}). "
            f"Likely bad credentials or insufficient permissions. Details: {err or out}"
        )

    return parse_prowler_ocsf(matches[0], tenant_id, connector_id)
