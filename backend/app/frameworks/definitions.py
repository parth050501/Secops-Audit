"""
Framework definitions.
Each framework has: controls, categories, and a UI theme.
Controls map to event categories so any event from any device can be automatically mapped.
"""

FRAMEWORKS = {
    "pci_dss": {
        "name": "PCI DSS v4.0",
        "short": "PCI DSS",
        "industry": ["financial", "retail"],
        "color": "#1a56db",
        "description": "Payment Card Industry Data Security Standard",
        "controls": [
            {"id": "1.1", "title": "Network security controls established",       "category": "network_security",  "weight": "high"},
            {"id": "1.2", "title": "Network access controls configured",           "category": "network_security",  "weight": "high"},
            {"id": "2.2", "title": "System components configured securely",        "category": "config",            "weight": "high"},
            {"id": "3.4", "title": "Primary account numbers protected at rest",    "category": "data_protection",   "weight": "critical"},
            {"id": "4.2", "title": "PAN protected in transit with encryption",     "category": "encryption",        "weight": "critical"},
            {"id": "5.2", "title": "Anti-malware solution deployed",               "category": "endpoint",          "weight": "high"},
            {"id": "6.3", "title": "Security vulnerabilities managed",             "category": "patching",          "weight": "high"},
            {"id": "7.2", "title": "Access to system components restricted",       "category": "access_control",    "weight": "critical"},
            {"id": "8.2", "title": "User identification and authentication managed","category": "identity",          "weight": "critical"},
            {"id": "8.4", "title": "Multi-factor authentication implemented",      "category": "identity",          "weight": "critical"},
            {"id": "10.2","title": "Audit logs implemented",                        "category": "logging",           "weight": "high"},
            {"id": "10.3","title": "Audit logs protected from destruction",        "category": "logging",           "weight": "high"},
            {"id": "11.3","title": "External and internal vulnerabilities managed","category": "patching",          "weight": "high"},
            {"id": "12.3","title": "Risks identified and managed",                 "category": "risk",              "weight": "medium"},
        ],
    },
    "hipaa": {
        "name": "HIPAA Security Rule",
        "short": "HIPAA",
        "industry": ["healthcare"],
        "color": "#057a55",
        "description": "Health Insurance Portability and Accountability Act",
        "controls": [
            {"id": "164.308(a)(1)", "title": "Security management process",        "category": "risk",             "weight": "critical"},
            {"id": "164.308(a)(3)", "title": "Workforce access management",        "category": "access_control",   "weight": "high"},
            {"id": "164.308(a)(4)", "title": "Information access management",      "category": "access_control",   "weight": "critical"},
            {"id": "164.308(a)(5)", "title": "Security awareness training",        "category": "identity",         "weight": "medium"},
            {"id": "164.310(a)(2)", "title": "Physical access controls",           "category": "config",           "weight": "high"},
            {"id": "164.310(d)",    "title": "Device and media controls",          "category": "endpoint",         "weight": "high"},
            {"id": "164.312(a)",    "title": "Access control",                     "category": "identity",         "weight": "critical"},
            {"id": "164.312(b)",    "title": "Audit controls",                     "category": "logging",          "weight": "high"},
            {"id": "164.312(c)",    "title": "Integrity controls",                 "category": "data_protection",  "weight": "high"},
            {"id": "164.312(e)",    "title": "Transmission security",              "category": "encryption",       "weight": "critical"},
        ],
    },
    "sox": {
        "name": "SOX ITGC",
        "short": "SOX",
        "industry": ["financial"],
        "color": "#9f580a",
        "description": "Sarbanes-Oxley IT General Controls",
        "controls": [
            {"id": "CC6.1",  "title": "Logical and physical access controls",      "category": "access_control",   "weight": "critical"},
            {"id": "CC6.2",  "title": "New access provisioning",                   "category": "identity",         "weight": "high"},
            {"id": "CC6.3",  "title": "Access removal for terminated users",       "category": "identity",         "weight": "critical"},
            {"id": "CC7.1",  "title": "Detection and monitoring controls",         "category": "logging",          "weight": "high"},
            {"id": "CC7.2",  "title": "Security incidents monitored",              "category": "logging",          "weight": "high"},
            {"id": "CC8.1",  "title": "Change management process",                 "category": "config",           "weight": "critical"},
            {"id": "A1.2",   "title": "Environmental protections",                 "category": "availability",     "weight": "medium"},
        ],
    },
    "iso27001": {
        "name": "ISO/IEC 27001:2022",
        "short": "ISO 27001",
        "industry": ["financial", "healthcare", "retail", "government", "technology"],
        "color": "#5521b5",
        "description": "Information Security Management System",
        "controls": [
            {"id": "A.5.15",  "title": "Access control policy",                   "category": "access_control",   "weight": "high"},
            {"id": "A.5.16",  "title": "Identity management",                     "category": "identity",         "weight": "high"},
            {"id": "A.5.17",  "title": "Authentication information",              "category": "identity",         "weight": "high"},
            {"id": "A.8.5",   "title": "Secure authentication",                   "category": "identity",         "weight": "critical"},
            {"id": "A.8.7",   "title": "Protection against malware",              "category": "endpoint",         "weight": "high"},
            {"id": "A.8.8",   "title": "Management of technical vulnerabilities", "category": "patching",         "weight": "high"},
            {"id": "A.8.15",  "title": "Logging",                                 "category": "logging",          "weight": "high"},
            {"id": "A.8.20",  "title": "Networks security",                       "category": "network_security", "weight": "high"},
            {"id": "A.8.24",  "title": "Use of cryptography",                     "category": "encryption",       "weight": "high"},
            {"id": "A.12.6",  "title": "Management of technical vulnerabilities", "category": "patching",         "weight": "high"},
        ],
    },
    "nist_csf": {
        "name": "NIST CSF 2.0",
        "short": "NIST CSF",
        "industry": ["government", "financial", "technology"],
        "color": "#1f2937",
        "description": "NIST Cybersecurity Framework",
        "controls": [
            {"id": "ID.AM",  "title": "Asset management",                         "category": "config",           "weight": "high"},
            {"id": "ID.RA",  "title": "Risk assessment",                          "category": "risk",             "weight": "high"},
            {"id": "PR.AC",  "title": "Identity management and access control",   "category": "access_control",   "weight": "critical"},
            {"id": "PR.DS",  "title": "Data security",                            "category": "data_protection",  "weight": "high"},
            {"id": "PR.IP",  "title": "Information protection processes",         "category": "config",           "weight": "high"},
            {"id": "PR.MA",  "title": "Maintenance",                              "category": "patching",         "weight": "medium"},
            {"id": "PR.PT",  "title": "Protective technology",                    "category": "network_security", "weight": "high"},
            {"id": "DE.CM",  "title": "Security continuous monitoring",           "category": "logging",          "weight": "high"},
            {"id": "DE.DP",  "title": "Detection processes",                      "category": "logging",          "weight": "high"},
            {"id": "RS.RP",  "title": "Response planning",                        "category": "risk",             "weight": "medium"},
        ],
    },
    "hitrust": {
        "name": "HITRUST CSF r9.4",
        "short": "HITRUST",
        "industry": ["healthcare"],
        "color": "#c81e1e",
        "description": "Health Information Trust Alliance",
        "controls": [
            {"id": "01.a",  "title": "Access control policy",                     "category": "access_control",   "weight": "high"},
            {"id": "01.b",  "title": "User registration and de-registration",     "category": "identity",         "weight": "high"},
            {"id": "01.d",  "title": "User password management",                  "category": "identity",         "weight": "high"},
            {"id": "01.q",  "title": "User authentication for external connections","category":"identity",         "weight": "critical"},
            {"id": "09.aa", "title": "Audit logging",                             "category": "logging",          "weight": "high"},
            {"id": "09.ab", "title": "Monitoring system use",                     "category": "logging",          "weight": "high"},
            {"id": "09.s",  "title": "Information system audit controls",         "category": "logging",          "weight": "high"},
            {"id": "10.f",  "title": "Policy on the use of cryptography",         "category": "encryption",       "weight": "critical"},
        ],
    },
    "soc2": {
        "name": "SOC 2 (Trust Services Criteria)",
        "short": "SOC 2",
        "industry": ["technology", "financial", "retail"],
        "color": "#0891b2",
        "description": "AICPA SOC 2 Trust Services Criteria — Security, Availability, Confidentiality",
        "controls": [
            {"id": "CC6.1", "title": "Logical and physical access controls restrict access",   "category": "access_control",   "weight": "critical"},
            {"id": "CC6.2", "title": "User registration and authorization before access",       "category": "identity",         "weight": "high"},
            {"id": "CC6.3", "title": "Access removal upon termination or role change",          "category": "identity",         "weight": "critical"},
            {"id": "CC6.6", "title": "Logical access security measures protect against threats", "category": "network_security", "weight": "high"},
            {"id": "CC6.7", "title": "Data transmission is restricted and encrypted",           "category": "encryption",       "weight": "critical"},
            {"id": "CC6.8", "title": "Controls prevent or detect unauthorized software",        "category": "endpoint",         "weight": "high"},
            {"id": "CC7.1", "title": "Detection and monitoring of configuration changes",       "category": "config",           "weight": "high"},
            {"id": "CC7.2", "title": "Security events are monitored and analyzed",              "category": "logging",          "weight": "high"},
            {"id": "CC7.3", "title": "Security incidents are evaluated and responded to",       "category": "logging",          "weight": "high"},
            {"id": "CC7.4", "title": "Incident response program is in place",                   "category": "risk",             "weight": "medium"},
            {"id": "CC8.1", "title": "Change management process for infrastructure",            "category": "config",           "weight": "critical"},
            {"id": "A1.1",  "title": "Capacity is monitored to meet availability commitments",  "category": "availability",     "weight": "medium"},
            {"id": "A1.2",  "title": "Environmental protections and backup processes",          "category": "availability",     "weight": "high"},
            {"id": "C1.1",  "title": "Confidential information is identified and protected",    "category": "data_protection",  "weight": "high"},
            {"id": "C1.2",  "title": "Confidential information is disposed of securely",        "category": "data_protection",  "weight": "medium"},
        ],
    },
}

CATEGORY_LABELS = {
    "access_control":   "Access Control",
    "identity":         "Identity & Authentication",
    "encryption":       "Encryption",
    "logging":          "Audit Logging",
    "network_security": "Network Security",
    "config":           "Secure Configuration",
    "patching":         "Vulnerability & Patching",
    "data_protection":  "Data Protection",
    "endpoint":         "Endpoint Security",
    "availability":     "Availability",
    "risk":             "Risk Management",
}

INDUSTRY_FRAMEWORKS = {
    "financial":   ["pci_dss", "sox", "soc2", "iso27001", "nist_csf"],
    "healthcare":  ["hipaa",   "hitrust", "iso27001", "nist_csf"],
    "retail":      ["pci_dss", "soc2", "iso27001", "nist_csf"],
    "government":  ["nist_csf","iso27001","fedramp"],
    "technology":  ["soc2","iso27001","nist_csf"],
}

CONNECTOR_CATALOG = [
    # Network
    {"type":"paloalto",       "category":"network",   "name":"Palo Alto Networks",     "icon":"🔥", "collection":["config","logs","threats"]},
    {"type":"fortinet",       "category":"network",   "name":"Fortinet FortiGate",      "icon":"🛡️", "collection":["config","logs"]},
    {"type":"checkpoint",     "category":"network",   "name":"Check Point",             "icon":"✅", "collection":["config","logs"]},
    {"type":"cisco_asa",      "category":"network",   "name":"Cisco ASA",               "icon":"🔵", "collection":["config","logs"]},
    {"type":"cisco_switch",   "category":"network",   "name":"Cisco Switch",            "icon":"🔌", "collection":["config","syslog"]},
    {"type":"f5",             "category":"network",   "name":"F5 BIG-IP",               "icon":"⚖️", "collection":["config","logs"]},
    # Servers
    {"type":"windows_server", "category":"server",    "name":"Windows Server",          "icon":"🪟", "collection":["events","config","users","patches"]},
    {"type":"linux",          "category":"server",    "name":"Linux (any distro)",       "icon":"🐧", "collection":["syslog","config","users","patches"]},
    {"type":"vmware",         "category":"server",    "name":"VMware vSphere",           "icon":"☁️", "collection":["config","events"]},
    # Cloud
    {"type":"aws",            "category":"cloud",     "name":"Amazon Web Services",      "icon":"🟠", "collection":["cloudtrail","config","iam","s3"]},
    {"type":"azure",          "category":"cloud",     "name":"Microsoft Azure",          "icon":"🔷", "collection":["activitylog","config","aad","defender"]},
    {"type":"gcp",            "category":"cloud",     "name":"Google Cloud Platform",    "icon":"🟡", "collection":["auditlog","config","iam"]},
    # Identity
    {"type":"active_directory","category":"identity", "name":"Active Directory",         "icon":"🏢", "collection":["users","groups","policies","events"]},
    {"type":"okta",           "category":"identity",  "name":"Okta",                     "icon":"🔑", "collection":["users","mfa","logs","policies"]},
    {"type":"azure_ad",       "category":"identity",  "name":"Azure Active Directory",   "icon":"🔐", "collection":["users","mfa","conditionalaccess","logs"]},
    {"type":"cyberark",       "category":"identity",  "name":"CyberArk PAM",             "icon":"🔒", "collection":["sessions","users","vaults"]},
    # SIEM / Monitoring
    {"type":"splunk",         "category":"siem",      "name":"Splunk",                   "icon":"📊", "collection":["alerts","searches","logs"]},
    {"type":"sentinel",       "category":"siem",      "name":"Microsoft Sentinel",       "icon":"🛡️", "collection":["incidents","alerts","logs"]},
    {"type":"wazuh",          "category":"siem",      "name":"Wazuh",                    "icon":"👁️", "collection":["alerts","agents","config"]},
    {"type":"crowdstrike",    "category":"siem",      "name":"CrowdStrike Falcon",       "icon":"🦅", "collection":["alerts","devices","vuln"]},
    # Databases
    {"type":"sql_server",     "category":"database",  "name":"Microsoft SQL Server",     "icon":"🗄️", "collection":["audit","config","users","access"]},
    {"type":"postgres",       "category":"database",  "name":"PostgreSQL",               "icon":"🐘", "collection":["audit","config","users"]},
    {"type":"oracle",         "category":"database",  "name":"Oracle Database",          "icon":"🔴", "collection":["audit","config","users","access"]},
    # Custom
    {"type":"custom_api",     "category":"custom",    "name":"Custom REST API",          "icon":"🔧", "collection":["custom"]},
    {"type":"syslog",         "category":"custom",    "name":"Syslog / CEF / LEEF",      "icon":"📝", "collection":["logs"]},
    {"type":"agent",          "category":"custom",    "name":"SecOps Agent (any OS)",    "icon":"🤖", "collection":["events","config","users"]},
]


# Per-connector connection field definitions.
# Each field: name, label, type, placeholder, required, help, options (for select)
CONNECTOR_FIELDS = {
    # ── Cloud ──
    "aws": [
        {"name":"auth_method","label":"Authentication method","type":"select","required":True,
         "options":["IAM Role (recommended)","Access Key"],
         "help":"IAM Role is more secure — no long-lived keys stored."},
        {"name":"role_arn","label":"IAM Role ARN","type":"text","required":False,
         "placeholder":"arn:aws:iam::123456789012:role/SecOpsAuditRole",
         "help":"Read-only role with the SecurityAudit policy attached."},
        {"name":"external_id","label":"External ID","type":"text","required":False,
         "placeholder":"unique-external-id","help":"Shared secret to prevent confused-deputy attacks."},
        {"name":"access_key_id","label":"Access Key ID","type":"text","required":False,
         "placeholder":"AKIA...","help":"Only if using Access Key auth."},
        {"name":"secret_access_key","label":"Secret Access Key","type":"password","required":False,
         "placeholder":"••••••••","help":"Only if using Access Key auth. Stored encrypted."},
        {"name":"regions","label":"Regions","type":"text","required":False,
         "placeholder":"us-east-1,us-west-2","help":"Comma-separated, or leave blank for all."},
    ],
    "azure": [
        {"name":"tenant_id","label":"Directory (tenant) ID","type":"text","required":True,"placeholder":"00000000-0000-..."},
        {"name":"client_id","label":"Application (client) ID","type":"text","required":True,"placeholder":"00000000-0000-..."},
        {"name":"client_secret","label":"Client Secret","type":"password","required":True,"placeholder":"••••••••","help":"Stored encrypted."},
        {"name":"subscription_id","label":"Subscription ID","type":"text","required":True,"placeholder":"00000000-0000-..."},
    ],
    "gcp": [
        {"name":"project_id","label":"Project ID","type":"text","required":True,"placeholder":"my-project-123"},
        {"name":"service_account_json","label":"Service Account Key (JSON)","type":"password","required":True,
         "placeholder":"Paste the full JSON key","help":"Read-only service account. Stored encrypted."},
    ],
    # ── Identity ──
    "okta": [
        {"name":"domain","label":"Okta Domain","type":"text","required":True,"placeholder":"your-org.okta.com"},
        {"name":"api_token","label":"API Token","type":"password","required":True,"placeholder":"••••••••","help":"Read-only API token. Stored encrypted."},
    ],
    "azure_ad": [
        {"name":"tenant_id","label":"Tenant ID","type":"text","required":True,"placeholder":"00000000-0000-..."},
        {"name":"client_id","label":"Client ID","type":"text","required":True,"placeholder":"00000000-0000-..."},
        {"name":"client_secret","label":"Client Secret","type":"password","required":True,"placeholder":"••••••••"},
    ],
    "active_directory": [
        {"name":"domain","label":"Domain","type":"text","required":True,"placeholder":"corp.example.local"},
        {"name":"dc_host","label":"Domain Controller","type":"text","required":True,"placeholder":"dc01.corp.example.local"},
        {"name":"bind_user","label":"Service Account (read-only)","type":"text","required":True,"placeholder":"svc-secops@corp.example.local"},
        {"name":"bind_password","label":"Service Account Password","type":"password","required":True,"placeholder":"••••••••"},
        {"name":"use_ldaps","label":"Use LDAPS (secure)","type":"select","required":False,"options":["Yes","No"]},
    ],
    "cyberark": [
        {"name":"base_url","label":"PVWA URL","type":"text","required":True,"placeholder":"https://cyberark.example.com"},
        {"name":"username","label":"Username","type":"text","required":True,"placeholder":"svc-secops"},
        {"name":"password","label":"Password","type":"password","required":True,"placeholder":"••••••••"},
    ],
    # ── Network (appliance — IP based) ──
    "paloalto":   [
        {"name":"assess_mode","label":"Assessment source","type":"select","required":True,
         "options":["Upload config export","Collector fetches via API"],
         "help":"Compliance posture assessment of the firewall configuration (not log monitoring)."},
        {"name":"config_xml","label":"Running-config XML (paste/export)","type":"textarea","required":False,
         "placeholder":"Paste the exported running-config XML…",
         "help":"Export from the firewall: 'Export named configuration version'. On-prem, the collector fetches this automatically."},
        {"name":"host","label":"Management IP / Hostname (collector mode)","type":"text","required":False,"placeholder":"10.0.0.1"},
        {"name":"api_key","label":"API Key (collector mode)","type":"password","required":False,"placeholder":"••••••••","help":"Read-only admin API key, used by the collector inside the network."},
    ],
    "fortinet":   [
        {"name":"host","label":"Management IP / Hostname","type":"text","required":True,"placeholder":"10.0.0.1"},
        {"name":"api_token","label":"API Token","type":"password","required":True,"placeholder":"••••••••"},
    ],
    "checkpoint": [
        {"name":"host","label":"Management Server IP","type":"text","required":True,"placeholder":"10.0.0.1"},
        {"name":"username","label":"Username","type":"text","required":True},
        {"name":"password","label":"Password","type":"password","required":True},
    ],
    "cisco_asa":  [
        {"name":"host","label":"Management IP","type":"text","required":True,"placeholder":"10.0.0.1"},
        {"name":"username","label":"Username","type":"text","required":True},
        {"name":"password","label":"Password","type":"password","required":True},
    ],
    "cisco_switch":[
        {"name":"host","label":"Management IP","type":"text","required":True,"placeholder":"10.0.0.1"},
        {"name":"username","label":"Username","type":"text","required":True},
        {"name":"password","label":"Password","type":"password","required":True},
    ],
    "f5":         [
        {"name":"host","label":"Management IP","type":"text","required":True,"placeholder":"10.0.0.1"},
        {"name":"username","label":"Username","type":"text","required":True},
        {"name":"password","label":"Password","type":"password","required":True},
    ],
    # ── Servers ──
    "windows_server": [
        {"name":"assess_mode","label":"Assessment source","type":"select","required":True,
         "options":["Agent runs PowerShell collector","Upload assessment JSON"],
         "help":"Compliance posture assessment of Windows security settings (password/audit/lockout/hardening). The agent runs the read-only PowerShell collector on-prem; for testing you can upload its JSON output."},
        {"name":"assessment_json","label":"Assessment JSON (paste/upload)","type":"textarea","required":False,
         "placeholder":"Paste the output of secops-win-assess.ps1…",
         "help":"Output of the PowerShell collector script. On-prem the agent produces this automatically."},
        {"name":"host","label":"Hostname / IP (agent mode)","type":"text","required":False,"placeholder":"srv01 or 10.0.1.5"},
    ],
    "linux": [
        {"name":"scan_mode","label":"Scan target","type":"select","required":True,
         "options":["This host (local/agent)","Remote via SSH"],
         "help":"OpenSCAP runs where the server is reachable. For servers behind a firewall, the collector/agent runs it locally."},
        {"name":"profile","label":"SCAP profile","type":"select","required":False,
         "options":["CIS Level 1","CIS Level 2","PCI-DSS","STIG","Standard"],
         "help":"Which benchmark to evaluate against. Maps to your active framework."},
        {"name":"host","label":"Hostname / IP (remote only)","type":"text","required":False,"placeholder":"10.0.1.5"},
        {"name":"ssh_user","label":"SSH User (remote only)","type":"text","required":False,"placeholder":"secops"},
        {"name":"ssh_key","label":"SSH Private Key (remote only)","type":"password","required":False,"placeholder":"Paste private key","help":"Read-only user. Stored encrypted."},
        {"name":"ssh_port","label":"SSH Port (remote only)","type":"number","required":False,"placeholder":"22"},
    ],
    "vmware": [
        {"name":"host","label":"vCenter Host","type":"text","required":True,"placeholder":"vcenter.example.com"},
        {"name":"username","label":"Username","type":"text","required":True},
        {"name":"password","label":"Password","type":"password","required":True},
    ],
    # ── SIEM ──
    "splunk": [
        {"name":"host","label":"Splunk Host","type":"text","required":True,"placeholder":"splunk.example.com"},
        {"name":"port","label":"Management Port","type":"number","required":False,"placeholder":"8089"},
        {"name":"token","label":"Auth Token","type":"password","required":True,"placeholder":"••••••••"},
    ],
    "sentinel": [
        {"name":"tenant_id","label":"Tenant ID","type":"text","required":True},
        {"name":"workspace_id","label":"Log Analytics Workspace ID","type":"text","required":True},
        {"name":"client_id","label":"Client ID","type":"text","required":True},
        {"name":"client_secret","label":"Client Secret","type":"password","required":True},
    ],
    "wazuh": [
        {"name":"base_url","label":"Wazuh API URL","type":"text","required":True,"placeholder":"https://wazuh.example.com:55000"},
        {"name":"username","label":"Username","type":"text","required":True},
        {"name":"password","label":"Password","type":"password","required":True},
    ],
    "crowdstrike": [
        {"name":"client_id","label":"API Client ID","type":"text","required":True},
        {"name":"client_secret","label":"API Client Secret","type":"password","required":True},
        {"name":"base_url","label":"API Base URL","type":"text","required":False,"placeholder":"https://api.crowdstrike.com"},
    ],
    # ── Databases ──
    "sql_server": [
        {"name":"host","label":"Server Host / IP","type":"text","required":True,"placeholder":"10.0.2.50"},
        {"name":"port","label":"Port","type":"number","required":False,"placeholder":"1433"},
        {"name":"username","label":"Username (read-only)","type":"text","required":True},
        {"name":"password","label":"Password","type":"password","required":True},
        {"name":"database","label":"Database","type":"text","required":False,"placeholder":"master"},
    ],
    "postgres": [
        {"name":"assess_mode","label":"Assessment source","type":"select","required":True,
         "options":["Agent runs read-only queries","Upload assessment JSON"],
         "help":"Compliance assessment of the PostgreSQL engine config (SSL, logging, auth, privileges). The agent runs read-only queries on-prem; for testing you can upload the settings JSON."},
        {"name":"assessment_json","label":"Assessment JSON (paste/upload)","type":"textarea","required":False,
         "placeholder":"Paste the collected settings document…"},
        {"name":"host","label":"Host / IP (agent mode)","type":"text","required":False,"placeholder":"10.0.2.51"},
        {"name":"port","label":"Port","type":"number","required":False,"placeholder":"5432"},
    ],
    "oracle": [
        {"name":"host","label":"Host / IP","type":"text","required":True},
        {"name":"port","label":"Port","type":"number","required":False,"placeholder":"1521"},
        {"name":"service_name","label":"Service Name","type":"text","required":True,"placeholder":"ORCL"},
        {"name":"username","label":"Username (read-only)","type":"text","required":True},
        {"name":"password","label":"Password","type":"password","required":True},
    ],
    # ── Custom ──
    "custom_api": [
        {"name":"base_url","label":"API Base URL","type":"text","required":True,"placeholder":"https://api.example.com"},
        {"name":"api_key","label":"API Key / Token","type":"password","required":False},
        {"name":"auth_header","label":"Auth Header Name","type":"text","required":False,"placeholder":"Authorization"},
    ],
    "syslog": [
        {"name":"listen_port","label":"Listen Port","type":"number","required":True,"placeholder":"514"},
        {"name":"protocol","label":"Protocol","type":"select","required":True,"options":["UDP","TCP","TLS"]},
        {"name":"format","label":"Format","type":"select","required":True,"options":["CEF","LEEF","RFC5424","RFC3164"]},
    ],
    "agent": [
        {"name":"agent_name","label":"Agent Name","type":"text","required":True,"placeholder":"prod-server-fleet"},
        {"name":"os_type","label":"OS Type","type":"select","required":True,"options":["Windows","Linux","macOS"]},
        {"name":"_note","label":"","type":"note","required":False,
         "help":"After creating, you'll receive an install command to run on the target. The agent connects outbound — no inbound firewall rules needed."},
    ],
}


def fields_for_connector(connector_type: str) -> list:
    """Return the connection-field schema for a connector type."""
    return CONNECTOR_FIELDS.get(connector_type, [
        {"name":"host","label":"Host / IP","type":"text","required":True},
        {"name":"api_key","label":"API Key","type":"password","required":False},
    ])
