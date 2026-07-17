"""
OpenSCAP Server Connector Adapter.

Runs an OpenSCAP (oscap) scan against a Linux server using a SCAP datastream
(e.g. the SCAP Security Guide content for CIS / STIG / PCI profiles), parses the
XCCDF results, and turns each FAILED rule into a GovernanceEvent dict — the same
shape the Prowler adapters produce, so everything downstream works unchanged.

OpenSCAP is the audit-grade choice: its results map directly to recognized
benchmarks (CIS, DISA STIG, PCI-DSS profiles), which is exactly what auditors
expect.

Two modes:
  - run_openscap_scan(): runs `oscap` locally (on the host/collector where the
    target filesystem is reachable) and parses the output.
  - parse_openscap_xccdf(): parses an existing XCCDF results XML file. This is
    the part that is fully testable now — point it at real `oscap` output from a
    server you control, exactly like we tested Prowler's OCSF output.

NOTE ON DEPLOYMENT: to scan a customer's server that sits behind their firewall,
the scan must run *inside* their environment (via the collector/agent) and ship
the XCCDF results back. parse_openscap_xccdf() is the ingestion side that runs on
the platform; run_openscap_scan() is what the collector/agent will invoke.
"""
import os
import glob
import subprocess
import tempfile
from datetime import datetime
from typing import List
import xml.etree.ElementTree as ET

# Reuse severity/category conventions consistent with the Prowler adapter
SEVERITY_MAP = {
    "high": "high", "medium": "medium", "low": "low", "info": "low", "unknown": "medium",
}

# Map XCCDF rule "category" hints (from rule id / references) to our governance categories
def _categorize(rule_id: str, title: str) -> str:
    text = f"{rule_id} {title}".lower()
    if any(k in text for k in ("password", "auth", "login", "pam", "account", "sudo", "privilege")):
        return "identity"
    if any(k in text for k in ("audit", "log", "rsyslog", "journald", "accounting")):
        return "logging"
    if any(k in text for k in ("firewall", "iptables", "nftables", "network", "ssh", "tcp", "port")):
        return "network_security"
    if any(k in text for k in ("encrypt", "crypto", "tls", "ssl", "fips")):
        return "encryption"
    if any(k in text for k in ("file", "permission", "mount", "partition", "umask", "selinux", "apparmor")):
        return "data_protection"
    if any(k in text for k in ("update", "patch", "package", "yum", "dnf", "apt")):
        return "config"
    return "config"


# XCCDF XML namespaces vary by version; handle the common ones
_NS = {
    "xccdf": "http://checklists.nist.gov/xccdf/1.2",
    "xccdf11": "http://checklists.nist.gov/xccdf/1.1",
}


def _localname(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def parse_openscap_xccdf(xml_path: str, tenant_id: int, connector_id: int,
                         framework_hint: str = None) -> List[dict]:
    """Parse an OpenSCAP XCCDF results XML into GovernanceEvent dicts (failed rules).

    framework_hint: optionally tag all findings with a platform framework key
    (e.g. 'cis' profile scans → map to the tenant's active framework). XCCDF also
    carries <ident> references (CCE, etc.) we capture in raw_data.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Build a map of rule_id -> (title, severity) from the benchmark definitions,
    # then read TestResult/rule-result for pass/fail outcomes.
    rule_meta = {}
    for el in root.iter():
        if _localname(el.tag) == "Rule":
            rid = el.get("id", "")
            sev = (el.get("severity") or "unknown").lower()
            title = ""
            for child in el:
                if _localname(child.tag) == "title":
                    title = (child.text or "").strip()
                    break
            rule_meta[rid] = {"severity": sev, "title": title}

    events = []
    seen = set()

    for el in root.iter():
        if _localname(el.tag) != "rule-result":
            continue
        rid = el.get("idref", "")
        result = ""
        idents = []
        for child in el:
            ln = _localname(child.tag)
            if ln == "result":
                result = (child.text or "").strip().lower()
            elif ln == "ident":
                if child.text:
                    idents.append(child.text.strip())
        # Only failures become governance events
        if result not in ("fail",):
            continue
        if rid in seen:
            continue
        seen.add(rid)

        meta = rule_meta.get(rid, {})
        title = meta.get("title") or rid.split("_")[-1]
        severity = SEVERITY_MAP.get(meta.get("severity", "unknown"), "medium")
        category = _categorize(rid, title)
        clean_title = title if len(title) <= 120 else title[:117] + "…"

        framework_mappings = {}
        if framework_hint:
            # The scan profile (CIS/STIG/PCI) corresponds to the tenant's framework;
            # tag with the rule's CCE/ident references as the control identifiers.
            framework_mappings[framework_hint] = idents[:6] if idents else [rid.split("_")[-1]]

        events.append({
            "tenant_id":    tenant_id,
            "connector_id": connector_id,
            "title":        clean_title,
            "description":  f"OpenSCAP rule failed: {rid}",
            "severity":     severity,
            "category":     category,
            "source_type":  "scheduled_scan",
            "framework_mappings": framework_mappings,
            "raw_data": {
                "source": "openscap",
                "rule_id": rid,
                "idents": idents[:10],
                "scap_severity": meta.get("severity"),
            },
            "occurred_at":  datetime.utcnow(),
            "status":       "open",
        })

    return events


def run_openscap_scan(credentials: dict, tenant_id: int, connector_id: int) -> List[dict]:
    """
    Run an OpenSCAP scan. Intended to run where the target is reachable — on the
    host itself, or via the collector/agent inside the customer's environment.

    credentials may contain:
      - datastream   : path to a SCAP datastream file (defaults to the SSG content
                       installed at a standard location)
      - profile      : the XCCDF profile id (e.g. a CIS or PCI profile)
      - framework    : platform framework key to tag findings with (e.g. 'pci_dss')

    Returns a list of GovernanceEvent dicts (failed rules).
    """
    creds = credentials or {}
    datastream = creds.get("datastream") or _default_datastream()
    profile = creds.get("profile")
    framework = creds.get("framework")

    if not datastream or not os.path.exists(datastream):
        raise RuntimeError(
            "No SCAP datastream found. Install scap-security-guide (provides "
            "/usr/share/xml/scap/ssg/content/*.xml) or pass a 'datastream' path."
        )

    out_dir = tempfile.mkdtemp(prefix="openscap_")
    results_xml = os.path.join(out_dir, "results.xml")
    cmd = ["oscap", "xccdf", "eval", "--results", results_xml]
    if profile:
        cmd += ["--profile", profile]
    cmd += [datastream]

    try:
        # oscap returns exit code 2 when there are rule failures — that's normal,
        # not an error for us. capture output for debugging.
        result = subprocess.run(cmd, capture_output=True, timeout=1800, check=False)
    except subprocess.TimeoutExpired:
        raise RuntimeError("OpenSCAP scan timed out after 30 minutes")
    except FileNotFoundError:
        raise RuntimeError("oscap is not installed (install the 'openscap-scanner' package)")

    if not os.path.exists(results_xml):
        err = (result.stderr or b"").decode(errors="replace")[-500:]
        raise RuntimeError(f"OpenSCAP produced no results. Details: {err}")

    return parse_openscap_xccdf(results_xml, tenant_id, connector_id, framework_hint=framework)


def _default_datastream() -> str:
    """Find an installed SCAP Security Guide datastream, if present."""
    candidates = glob.glob("/usr/share/xml/scap/ssg/content/ssg-*-ds.xml")
    return candidates[0] if candidates else ""
