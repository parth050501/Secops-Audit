"""
Simulates realistic governance events from connected systems.
In production, each connector_type has a real adapter that calls the actual API.
This simulator produces realistic events for demo/dev.
"""
import random
from datetime import datetime, timedelta
from typing import List

EVENT_TEMPLATES = {
    "network": [
        {"title": "Any-to-Any firewall rule detected", "severity": "critical", "category": "network_security",
         "description": "A firewall rule permits unrestricted traffic from any source to any destination.",
         "framework_mappings": {"pci_dss": ["1.2", "1.1"], "iso27001": ["A.8.20"], "nist_csf": ["PR.PT"]}},
        {"title": "Telnet (TCP/23) permitted inbound", "severity": "high", "category": "network_security",
         "description": "Cleartext protocol Telnet is allowed through the firewall, exposing credentials.",
         "framework_mappings": {"pci_dss": ["4.2", "1.2"], "hipaa": ["164.312(e)"], "iso27001": ["A.8.20", "A.8.24"]}},
        {"title": "RDP exposed to public internet (0.0.0.0/0)", "severity": "critical", "category": "network_security",
         "description": "Remote Desktop Protocol accessible from all internet addresses — high brute-force risk.",
         "framework_mappings": {"pci_dss": ["1.2", "8.4"], "iso27001": ["A.8.20"], "nist_csf": ["PR.PT", "PR.AC"]}},
        {"title": "Unused firewall rules detected (47 rules, 90+ days)", "severity": "medium", "category": "config",
         "description": "47 firewall rules have had zero traffic in over 90 days and should be reviewed for removal.",
         "framework_mappings": {"pci_dss": ["1.1", "2.2"], "iso27001": ["A.8.20"], "nist_csf": ["PR.PT"]}},
        {"title": "SMBv1 protocol allowed on network segment", "severity": "high", "category": "network_security",
         "description": "SMBv1 is a legacy protocol vulnerable to EternalBlue/WannaCry. Should be blocked.",
         "framework_mappings": {"pci_dss": ["6.3", "1.2"], "hipaa": ["164.308(a)(1)"], "nist_csf": ["PR.PT"]}},
    ],
    "server": [
        {"title": "Missing critical security patches (15 CVEs)", "severity": "critical", "category": "patching",
         "description": "15 critical CVEs unpatched, oldest patch missing for 47 days. Includes CVSS 9.8 vulnerability.",
         "framework_mappings": {"pci_dss": ["6.3", "11.3"], "hipaa": ["164.308(a)(1)"], "iso27001": ["A.8.8", "A.12.6"], "nist_csf": ["PR.MA"]}},
        {"title": "Local administrator account used for service (Windows)", "severity": "high", "category": "identity",
         "description": "Service running under built-in Administrator account instead of a dedicated service account.",
         "framework_mappings": {"pci_dss": ["8.2", "7.2"], "sox": ["CC6.1"], "iso27001": ["A.5.16"]}},
        {"title": "Audit logging disabled on Windows Server", "severity": "critical", "category": "logging",
         "description": "Windows Security audit log is disabled — logon events, privilege use and object access not being recorded.",
         "framework_mappings": {"pci_dss": ["10.2", "10.3"], "hipaa": ["164.312(b)"], "sox": ["CC7.1"], "iso27001": ["A.8.15"]}},
        {"title": "SSH root login permitted (Linux)", "severity": "high", "category": "access_control",
         "description": "PermitRootLogin=yes in sshd_config — direct root SSH login allowed.",
         "framework_mappings": {"pci_dss": ["8.2", "7.2"], "hipaa": ["164.308(a)(3)"], "iso27001": ["A.8.5"]}},
        {"title": "Password complexity policy not enforced", "severity": "medium", "category": "identity",
         "description": "Local security policy does not enforce minimum password length or complexity requirements.",
         "framework_mappings": {"pci_dss": ["8.2"], "hipaa": ["164.312(a)"], "sox": ["CC6.1"], "iso27001": ["A.5.17"]}},
        {"title": "Antivirus definitions outdated (7 days)", "severity": "medium", "category": "endpoint",
         "description": "Antivirus/EDR definitions last updated 7 days ago — current threat signatures not applied.",
         "framework_mappings": {"pci_dss": ["5.2"], "hipaa": ["164.308(a)(1)"], "iso27001": ["A.8.7"]}},
    ],
    "identity": [
        {"title": "Privileged accounts without MFA enabled", "severity": "critical", "category": "identity",
         "description": "4 administrator accounts in Active Directory have no MFA requirement configured.",
         "framework_mappings": {"pci_dss": ["8.4"], "hipaa": ["164.312(a)"], "sox": ["CC6.1"], "iso27001": ["A.8.5"], "hitrust": ["01.q"]}},
        {"title": "Stale user accounts active (90+ days no login)", "severity": "high", "category": "identity",
         "description": "23 user accounts have not logged in for 90+ days but remain enabled with full access.",
         "framework_mappings": {"pci_dss": ["8.2"], "sox": ["CC6.3"], "hipaa": ["164.308(a)(3)"], "iso27001": ["A.5.16"]}},
        {"title": "Terminated employee accounts still active", "severity": "critical", "category": "access_control",
         "description": "3 accounts linked to employees terminated in the past 30 days remain active in directory.",
         "framework_mappings": {"pci_dss": ["8.2", "7.2"], "sox": ["CC6.3"], "hipaa": ["164.308(a)(3)"], "iso27001": ["A.5.15"]}},
        {"title": "Excessive privileged group membership", "severity": "high", "category": "access_control",
         "description": "Domain Admins group contains 18 members — recommended max is 5 for least-privilege.",
         "framework_mappings": {"pci_dss": ["7.2"], "sox": ["CC6.1"], "nist_csf": ["PR.AC"], "iso27001": ["A.5.15"]}},
        {"title": "Password never expires set on service accounts", "severity": "medium", "category": "identity",
         "description": "11 service accounts have 'password never expires' flag — violates rotation policy.",
         "framework_mappings": {"pci_dss": ["8.2"], "hipaa": ["164.312(a)"], "iso27001": ["A.5.17"]}},
    ],
    "cloud": [
        {"title": "S3 bucket with public read access", "severity": "critical", "category": "data_protection",
         "description": "S3 bucket 'prod-customer-data' has public read ACL — sensitive data potentially exposed.",
         "framework_mappings": {"pci_dss": ["3.4", "1.2"], "hipaa": ["164.312(c)"], "iso27001": ["A.8.24"], "nist_csf": ["PR.DS"]}},
        {"title": "Root AWS account used for daily operations", "severity": "critical", "category": "identity",
         "description": "CloudTrail shows root account login activity — should only be used for account management.",
         "framework_mappings": {"pci_dss": ["8.2", "7.2"], "iso27001": ["A.5.16"], "nist_csf": ["PR.AC"]}},
        {"title": "CloudTrail logging disabled in region", "severity": "critical", "category": "logging",
         "description": "AWS CloudTrail not enabled in ap-southeast-1 region — API activity not logged.",
         "framework_mappings": {"pci_dss": ["10.2"], "hipaa": ["164.312(b)"], "sox": ["CC7.1"], "nist_csf": ["DE.CM"]}},
        {"title": "Security group allows 0.0.0.0/0 on port 22", "severity": "high", "category": "network_security",
         "description": "EC2 security group permits SSH from all internet addresses.",
         "framework_mappings": {"pci_dss": ["1.2", "8.4"], "iso27001": ["A.8.20"], "nist_csf": ["PR.PT"]}},
        {"title": "IAM users with console access and no MFA", "severity": "critical", "category": "identity",
         "description": "7 IAM users have AWS console access enabled without MFA protection.",
         "framework_mappings": {"pci_dss": ["8.4"], "sox": ["CC6.1"], "iso27001": ["A.8.5"], "nist_csf": ["PR.AC"]}},
    ],
    "database": [
        {"title": "Database audit logging not enabled", "severity": "high", "category": "logging",
         "description": "SQL Server audit specification not configured — DML/DDL operations not being logged.",
         "framework_mappings": {"pci_dss": ["10.2"], "hipaa": ["164.312(b)"], "sox": ["CC7.1"], "iso27001": ["A.8.15"]}},
        {"title": "Default SA account enabled (SQL Server)", "severity": "critical", "category": "identity",
         "description": "SQL Server 'sa' (system administrator) account is enabled with a weak password.",
         "framework_mappings": {"pci_dss": ["2.2", "8.2"], "iso27001": ["A.5.16"], "nist_csf": ["PR.AC"]}},
        {"title": "Sensitive data stored unencrypted (TDE disabled)", "severity": "critical", "category": "encryption",
         "description": "Transparent Data Encryption not enabled on production database containing PII/PHI.",
         "framework_mappings": {"pci_dss": ["3.4", "4.2"], "hipaa": ["164.312(e)"], "hitrust": ["10.f"], "iso27001": ["A.8.24"]}},
    ],
    "siem": [
        {"title": "Log retention below compliance requirement (87 days)", "severity": "high", "category": "logging",
         "description": "Current log retention is 87 days. PCI DSS requires 90 days online, 12 months total.",
         "framework_mappings": {"pci_dss": ["10.3"], "hipaa": ["164.312(b)"], "sox": ["CC7.2"], "iso27001": ["A.8.15"]}},
        {"title": "Brute force attack detected — 847 failed logins", "severity": "critical", "category": "identity",
         "description": "847 failed authentication attempts in 4 minutes against WIN-DC-01 from 185.220.101.44 (Tor exit node).",
         "framework_mappings": {"pci_dss": ["8.2", "10.2"], "hipaa": ["164.308(a)(1)"], "iso27001": ["A.8.5"]}},
        {"title": "Unauthorized privileged access attempt detected", "severity": "high", "category": "access_control",
         "description": "Non-admin user attempted to access privileged share — access denied, security event logged.",
         "framework_mappings": {"pci_dss": ["7.2", "10.2"], "sox": ["CC6.1"], "iso27001": ["A.5.15"]}},
    ],
}

def simulate_events_for_connector(connector_type: str, connector_id: int, tenant_id: int, framework: str, count: int = 5) -> List[dict]:
    """Generate realistic governance events for a connector type."""
    category_map = {
        "paloalto": "network", "fortinet": "network", "checkpoint": "network",
        "cisco_asa": "network", "cisco_switch": "network", "f5": "network",
        "windows_server": "server", "linux": "server", "vmware": "server",
        "aws": "cloud", "azure": "cloud", "gcp": "cloud",
        "active_directory": "identity", "okta": "identity", "azure_ad": "identity", "cyberark": "identity",
        "splunk": "siem", "sentinel": "siem", "wazuh": "siem", "crowdstrike": "siem",
        "sql_server": "database", "postgres": "database", "oracle": "database",
        "custom_api": "server", "syslog": "siem", "agent": "server",
    }
    cat = category_map.get(connector_type, "server")
    templates = EVENT_TEMPLATES.get(cat, EVENT_TEMPLATES["server"])

    # Filter to templates relevant to the framework
    relevant = [t for t in templates if framework in t.get("framework_mappings", {})]
    if not relevant:
        relevant = templates

    chosen = random.sample(relevant, min(count, len(relevant)))
    events = []
    for tmpl in chosen:
        events.append({
            "tenant_id":    tenant_id,
            "connector_id": connector_id,
            "title":        tmpl["title"],
            "description":  tmpl["description"],
            "severity":     tmpl["severity"],
            "category":     tmpl["category"],
            "source_type":  "realtime",
            "framework_mappings": tmpl["framework_mappings"],
            "raw_data":     {"simulated": True, "connector_type": connector_type},
            "occurred_at":  datetime.utcnow() - timedelta(minutes=random.randint(0, 120)),
            "status":       "open",
        })
    return events
