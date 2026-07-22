"""
Palo Alto Firewall Config-Assessment Connector.

COMPLIANCE POSTURE ASSESSMENT — not a SIEM, not log ingestion. This evaluates
whether a Palo Alto firewall is *configured* in line with compliance controls,
and turns gaps into GovernanceEvent dicts (same shape as the cloud/server
connectors), mapped to frameworks.

Input: a Palo Alto running-config XML export (from "Export named configuration
version" in the UI, or `show config running` via the API). On-prem, this runs
where the device config is reachable — i.e. on the collector inside the
customer's network — and ships the findings out. The parser here is the
compliance "brain"; the collector is the delivery mechanism (built separately).

The checks below are configuration-hygiene controls that auditors care about:
  - Security rules that are overly permissive (any/any) — segmentation/least-priv
  - Rules without logging enabled — audit logging requirement
  - Rules allowing 'any' application or service — least privilege
  - Management access not restricted to specific IPs — secure admin access
  - Insecure management services enabled (HTTP/Telnet) — secure transport
  - No security profiles on allow rules — threat-prevention posture
  - Default/weak settings

Each finding maps to common control areas across SOC2/ISO/PCI/NIST. Control IDs
here are representative; tune against the customer's active framework.
"""
from datetime import datetime
from typing import List
import xml.etree.ElementTree as ET


# Map each check to the frameworks + representative control IDs it supports.
# These are the controls a firewall *configuration* commonly evidences.
CHECK_CONTROLS = {
    "permissive_any_any": {
        "pci_dss": ["1.2.1", "1.3"], "iso27001": ["A.8.20", "A.8.22"],
        "nist_csf": ["pr_ac_5"], "soc2": ["CC6.1", "CC6.6"],
    },
    "rule_no_logging": {
        "pci_dss": ["10.2", "10.3"], "iso27001": ["A.8.15", "A.8.16"],
        "nist_csf": ["de_ae_3"], "soc2": ["CC7.2"],
    },
    "rule_any_application": {
        "pci_dss": ["1.2.1"], "iso27001": ["A.8.20"], "soc2": ["CC6.6"],
    },
    "mgmt_not_restricted": {
        "pci_dss": ["1.3.1", "7.2"], "iso27001": ["A.8.2"], "soc2": ["CC6.1"],
        "nist_csf": ["pr_ac_4"],
    },
    "insecure_mgmt_service": {
        "pci_dss": ["2.2.5", "4.2.1"], "iso27001": ["A.8.20"], "soc2": ["CC6.7"],
    },
    "rule_no_security_profile": {
        "pci_dss": ["1.2.1"], "iso27001": ["A.8.7"], "nist_csf": ["pr_ip_1"],
        "soc2": ["CC6.8"],
    },
}

SEVERITY = {
    "permissive_any_any": "high",
    "rule_no_logging": "medium",
    "rule_any_application": "medium",
    "mgmt_not_restricted": "high",
    "insecure_mgmt_service": "high",
    "rule_no_security_profile": "medium",
}

CATEGORY = {
    "permissive_any_any": "network_security",
    "rule_no_logging": "logging",
    "rule_any_application": "network_security",
    "mgmt_not_restricted": "access_control",
    "insecure_mgmt_service": "network_security",
    "rule_no_security_profile": "network_security",
}


def _members(el) -> list:
    """Read <member> children (Palo Alto uses these for lists)."""
    if el is None:
        return []
    return [m.text for m in el.findall("member") if m.text]


def _framework_map(check_key: str, framework_hint: str = None) -> dict:
    controls = CHECK_CONTROLS.get(check_key, {})
    if framework_hint and framework_hint in controls:
        return {framework_hint: controls[framework_hint]}
    return dict(controls)


def _event(tenant_id, connector_id, check_key, title, detail, framework_hint, resource=""):
    return {
        "tenant_id": tenant_id,
        "connector_id": connector_id,
        "title": title if len(title) <= 120 else title[:117] + "…",
        "description": detail,
        "severity": SEVERITY.get(check_key, "medium"),
        "category": CATEGORY.get(check_key, "network_security"),
        "source_type": "scheduled_scan",
        "framework_mappings": _framework_map(check_key, framework_hint),
        "raw_data": {"source": "paloalto", "check": check_key, "resource": resource},
        "occurred_at": datetime.utcnow(),
        "status": "open",
    }


def assess_paloalto_config(xml_text: str, tenant_id: int, connector_id: int,
                           framework_hint: str = None) -> List[dict]:
    """Parse a Palo Alto running-config XML and return GovernanceEvent dicts for
    each configuration gap. `framework_hint` scopes mappings to one framework."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise RuntimeError(f"Could not parse Palo Alto config XML: {e}")

    events = []

    # ── Security rules assessment ──
    # Rules live under devices/.../vsys/.../rulebase/security/rules/entry
    for rule in root.iter("entry"):
        # Heuristic: a security rule has <from>/<to>/<action> children
        action_el = rule.find("action")
        from_el = rule.find("from")
        to_el = rule.find("to")
        if action_el is None or from_el is None or to_el is None:
            continue
        name = rule.get("name", "unnamed")
        action = (action_el.text or "").lower()
        if action != "allow":
            continue  # only allow-rules carry posture risk

        src = _members(rule.find("source"))
        dst = _members(rule.find("destination"))
        apps = _members(rule.find("application"))
        svcs = _members(rule.find("service"))
        from_zones = _members(from_el)
        to_zones = _members(to_el)

        # any/any permissive rule
        if ("any" in src or not src) and ("any" in dst or not dst) and \
           ("any" in from_zones) and ("any" in to_zones):
            events.append(_event(tenant_id, connector_id, "permissive_any_any",
                f"Firewall rule '{name}' allows any source to any destination",
                f"Security rule '{name}' permits any-to-any traffic, violating "
                f"network segmentation / least-privilege.", framework_hint, name))

        # any application
        if "any" in apps:
            events.append(_event(tenant_id, connector_id, "rule_any_application",
                f"Firewall rule '{name}' allows any application",
                f"Rule '{name}' permits 'any' application — not least-privilege.",
                framework_hint, name))

        # logging disabled (no log-end / log-start)
        log_end = rule.find("log-end")
        if log_end is None or (log_end.text or "").lower() != "yes":
            events.append(_event(tenant_id, connector_id, "rule_no_logging",
                f"Firewall rule '{name}' has session logging disabled",
                f"Rule '{name}' does not log at session end — audit logging gap.",
                framework_hint, name))

        # no security profiles on an allow rule
        prof = rule.find("profile-setting")
        if prof is None:
            events.append(_event(tenant_id, connector_id, "rule_no_security_profile",
                f"Firewall rule '{name}' has no security profiles",
                f"Allow rule '{name}' has no threat/AV/URL security profiles applied.",
                framework_hint, name))

    # ── Management access assessment ──
    # permitted-ip restricts management; absence = open management
    found_permitted_ip = any(True for _ in root.iter("permitted-ip"))
    if not found_permitted_ip:
        events.append(_event(tenant_id, connector_id, "mgmt_not_restricted",
            "Management access is not restricted to specific IPs",
            "No permitted-ip list found — device management may be reachable from "
            "any address. Restrict to admin networks.", framework_hint, "mgmt"))

    # Insecure management services (HTTP/Telnet enabled)
    for svc in root.iter("service"):
        for proto in ("http", "telnet"):
            el = svc.find(proto)
            if el is not None and (el.text or "").lower() == "yes":
                events.append(_event(tenant_id, connector_id, "insecure_mgmt_service",
                    f"Insecure management service '{proto.upper()}' is enabled",
                    f"Management service {proto.upper()} is enabled — use HTTPS/SSH "
                    f"instead for encrypted management.", framework_hint, proto))

    # Dedupe identical (check, resource) pairs
    seen, deduped = set(), []
    for e in events:
        k = (e["raw_data"]["check"], e["raw_data"]["resource"])
        if k in seen:
            continue
        seen.add(k)
        deduped.append(e)
    return deduped


def run_paloalto_scan(credentials: dict, tenant_id: int, connector_id: int) -> List[dict]:
    """
    Assess a Palo Alto firewall's configuration.

    credentials may contain:
      - config_xml : the running-config XML (as text) — e.g. uploaded export, or
                     fetched by the collector from the device API
      - framework  : platform framework key to scope mappings

    On-prem, the collector fetches the config locally (device API: type=config&
    action=show) and passes config_xml here. For testing now, you can paste a
    real exported config.
    """
    creds = credentials or {}
    xml_text = creds.get("config_xml")
    if not xml_text:
        raise RuntimeError(
            "No Palo Alto config provided. Supply 'config_xml' (a running-config "
            "export). On-prem this is fetched by the collector from the device."
        )
    return assess_paloalto_config(xml_text, tenant_id, connector_id,
                                  framework_hint=creds.get("framework"))
