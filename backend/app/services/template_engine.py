"""
Template Engine — zero-cost, rule-based ticket & enrichment generation.
This is the DEFAULT path. AI is only invoked via explicit pay-as-you-go calls.

Templates are keyed by (category, severity) with framework-specific control text.
~50 templates covering all event categories.
"""
from datetime import datetime

# ── Template library ───────────────────────────────────────────────────────────
# Each template: risk_summary, business_impact, remediation_steps, owner, effort

TEMPLATES = {
    # ── NETWORK SECURITY ──
    ("network_security", "critical"): {
        "risk_summary": "A critical network exposure permits unrestricted or dangerous traffic flows. This creates a direct path for attackers to reach sensitive systems and move laterally across the environment.",
        "business_impact": "Unrestricted network access violates segmentation requirements in all major frameworks. A breach via this exposure would likely be classified as a control failure during audit, and could result in regulatory penalties.",
        "remediation_steps": [
            "Review the flagged rule/configuration and identify all traffic currently using it",
            "Document legitimate business flows with named owners and justification",
            "Create specific least-privilege replacement rules for each approved flow",
            "Remove or disable the offending rule in a scheduled maintenance window",
            "Monitor for 72 hours and confirm no business disruption",
        ],
        "suggested_owner": "network_team",
        "estimated_effort": "medium",
        "priority": "immediate",
    },
    ("network_security", "high"): {
        "risk_summary": "An insecure protocol or excessive network exposure was detected. While not immediately exploitable in all cases, this materially increases the attack surface.",
        "business_impact": "Insecure protocols (Telnet, SMBv1, exposed RDP) are explicitly flagged in PCI DSS, ISO 27001, and NIST assessments. Auditors treat these as priority findings.",
        "remediation_steps": [
            "Identify systems and users relying on the insecure protocol or exposure",
            "Plan migration to a secure alternative (SSH, SMBv3, VPN-gated access)",
            "Update firewall rules to block the insecure protocol",
            "Verify replacement connectivity works for all affected users",
            "Document the change for audit evidence",
        ],
        "suggested_owner": "network_team",
        "estimated_effort": "medium",
        "priority": "this_week",
    },
    ("network_security", "medium"): {
        "risk_summary": "A network hygiene issue was detected that increases complexity and audit risk without immediate exploitability.",
        "business_impact": "Unused or overly broad rules accumulate over time and make audits slower and riskier. Cleanup demonstrates active governance to auditors.",
        "remediation_steps": [
            "Export the list of flagged rules with last-hit timestamps",
            "Confirm with rule owners that the rules are no longer needed",
            "Disable rules (do not delete) for a 30-day observation period",
            "Delete confirmed-unused rules after observation",
            "Update firewall documentation",
        ],
        "suggested_owner": "network_team",
        "estimated_effort": "low",
        "priority": "this_month",
    },

    # ── IDENTITY & AUTH ──
    ("identity", "critical"): {
        "risk_summary": "A critical identity control failure was detected — privileged access without adequate authentication safeguards. This is the single most common entry point in real-world breaches.",
        "business_impact": "Missing MFA on privileged accounts is an automatic audit finding under PCI DSS 8.4, SOX CC6.1, and HIPAA 164.312(a). Account takeover could lead to full environment compromise.",
        "remediation_steps": [
            "Enumerate all affected accounts from the identity provider",
            "Separate human accounts from service accounts",
            "Convert service accounts to non-interactive/programmatic access",
            "Enforce MFA enrollment for human accounts with a 24-hour deadline",
            "Apply a directory-level policy to prevent future non-MFA privileged access",
        ],
        "suggested_owner": "identity_team",
        "estimated_effort": "low",
        "priority": "immediate",
    },
    ("identity", "high"): {
        "risk_summary": "Identity lifecycle hygiene issues detected — stale, orphaned, or improperly configured accounts that retain valid credentials.",
        "business_impact": "Stale and orphaned accounts violate access review requirements (PCI DSS 8.2, SOX CC6.3). They are among the top 5 most common audit findings across all industries.",
        "remediation_steps": [
            "Export flagged accounts with last-logon timestamps",
            "Cross-reference against HR records for terminated employees",
            "Disable (do not delete) all confirmed stale accounts",
            "Notify managers of accounts pending review",
            "Implement an automated inactivity policy to prevent recurrence",
        ],
        "suggested_owner": "identity_team",
        "estimated_effort": "medium",
        "priority": "this_week",
    },
    ("identity", "medium"): {
        "risk_summary": "Password or authentication policy weaknesses detected that fall below framework baselines.",
        "business_impact": "Weak password policies are flagged in every framework assessment. Low effort to fix, high audit visibility.",
        "remediation_steps": [
            "Review current password/authentication policy settings",
            "Align policy with framework requirements (length, complexity, rotation)",
            "Apply updated policy via directory group policy",
            "Communicate change to affected users",
            "Capture policy screenshot for audit evidence",
        ],
        "suggested_owner": "identity_team",
        "estimated_effort": "low",
        "priority": "this_month",
    },

    # ── ACCESS CONTROL ──
    ("access_control", "critical"): {
        "risk_summary": "A critical access control violation — credentials or access rights exist that should have been revoked. Terminated employee access is a severe and time-sensitive exposure.",
        "business_impact": "Active terminated-employee accounts are an automatic audit failure (SOX CC6.3, PCI DSS 8.2, HIPAA 164.308(a)(3)) and a leading cause of insider-threat incidents.",
        "remediation_steps": [
            "Immediately disable all flagged accounts",
            "Revoke active sessions and tokens for those accounts",
            "Cross-check building access, VPN, and SaaS apps for the same identities",
            "Document termination dates vs. access removal dates for audit",
            "Add automated HR-to-IT deprovisioning workflow to roadmap",
        ],
        "suggested_owner": "identity_team",
        "estimated_effort": "low",
        "priority": "immediate",
    },
    ("access_control", "high"): {
        "risk_summary": "Excessive or improperly scoped access rights detected — more users or systems have privileged access than business need justifies.",
        "business_impact": "Least-privilege violations (oversized admin groups, root login enabled) are core audit checkpoints in every framework.",
        "remediation_steps": [
            "Export current privileged group membership",
            "Confirm business need for each member with their manager",
            "Remove members without documented justification",
            "Configure secure alternatives (sudo, JIT elevation) where needed",
            "Schedule quarterly privileged access reviews",
        ],
        "suggested_owner": "security_team",
        "estimated_effort": "medium",
        "priority": "this_week",
    },

    # ── LOGGING ──
    ("logging", "critical"): {
        "risk_summary": "A critical logging failure — audit trails are disabled or not being collected on an in-scope system. This blinds detection and makes forensics impossible.",
        "business_impact": "Disabled audit logging is an automatic failure of PCI DSS Requirement 10, HIPAA 164.312(b), and SOX CC7.1. It is among the first things auditors verify.",
        "remediation_steps": [
            "Re-enable audit logging on the affected system immediately",
            "Verify events are being generated and collected",
            "Confirm forwarding to the central SIEM is active",
            "Configure alerting for any future audit policy changes",
            "Investigate and document why logging was disabled",
        ],
        "suggested_owner": "sysadmin",
        "estimated_effort": "low",
        "priority": "immediate",
    },
    ("logging", "high"): {
        "risk_summary": "Logging coverage or configuration gaps detected — logs exist but are incomplete, unprotected, or missing key event types.",
        "business_impact": "Partial logging undermines incident response and weakens audit evidence. Frameworks require specific event types (auth, privilege use, data access) to be captured.",
        "remediation_steps": [
            "Compare current log coverage against framework requirements",
            "Enable missing event categories on affected systems",
            "Verify log integrity protection (append-only, restricted access)",
            "Test that new events appear in the SIEM",
            "Update logging standard documentation",
        ],
        "suggested_owner": "security_team",
        "estimated_effort": "medium",
        "priority": "this_week",
    },
    ("logging", "medium"): {
        "risk_summary": "Log retention or storage configuration falls below the framework-required threshold.",
        "business_impact": "Retention shortfalls (e.g. 87 vs 90 days) are easy audit findings. Fix is typically a configuration change plus storage budget.",
        "remediation_steps": [
            "Confirm the framework-required retention period for in-scope systems",
            "Update retention configuration in the log platform",
            "Verify storage capacity supports the new retention",
            "Document the new retention policy",
            "Capture configuration screenshot for audit evidence",
        ],
        "suggested_owner": "security_team",
        "estimated_effort": "low",
        "priority": "this_month",
    },

    # ── PATCHING ──
    ("patching", "critical"): {
        "risk_summary": "Critical vulnerabilities remain unpatched beyond acceptable timeframes. Known CVEs with public exploits represent immediate exploitation risk.",
        "business_impact": "PCI DSS requires critical patches within 30 days. Systems with CVSS 9+ vulnerabilities and public exploit code are high-probability breach vectors.",
        "remediation_steps": [
            "Prioritize patches for systems in compliance scope",
            "Schedule an emergency maintenance window within 48 hours",
            "Test critical patches in staging where possible",
            "Deploy patches and verify installation success",
            "Run a vulnerability scan to confirm remediation",
        ],
        "suggested_owner": "sysadmin",
        "estimated_effort": "medium",
        "priority": "immediate",
    },
    ("patching", "high"): {
        "risk_summary": "Patch currency gaps detected — systems are behind on security updates beyond policy thresholds.",
        "business_impact": "Patch management is a core control in every framework. Consistent gaps signal process failure to auditors, not just point-in-time risk.",
        "remediation_steps": [
            "Generate full patch-gap report for affected systems",
            "Schedule patching in the next maintenance window",
            "Deploy and verify patches",
            "Review patch automation configuration to prevent recurrence",
            "Document completion for audit evidence",
        ],
        "suggested_owner": "sysadmin",
        "estimated_effort": "medium",
        "priority": "this_week",
    },

    # ── DATA PROTECTION ──
    ("data_protection", "critical"): {
        "risk_summary": "Sensitive data is exposed or inadequately protected — public access to data stores or missing protection on regulated data classes.",
        "business_impact": "Public data exposure is a reportable incident in most jurisdictions and an automatic critical audit finding. Direct regulatory and reputational consequences.",
        "remediation_steps": [
            "Immediately remove public access from the affected data store",
            "Audit access logs to determine if data was accessed externally",
            "Apply least-privilege access policy to the resource",
            "Enable access logging and alerting on the data store",
            "Assess breach notification obligations with legal/compliance",
        ],
        "suggested_owner": "cloud_team",
        "estimated_effort": "low",
        "priority": "immediate",
    },

    # ── ENCRYPTION ──
    ("encryption", "critical"): {
        "risk_summary": "Regulated data is stored or transmitted without required encryption. This is a direct violation of data protection requirements.",
        "business_impact": "Unencrypted cardholder data (PCI DSS 3.4) or PHI (HIPAA 164.312(e)) is among the most severe findings possible. Breach of unencrypted data removes safe-harbor protections.",
        "remediation_steps": [
            "Enable encryption at rest (TDE or equivalent) on the affected store",
            "Back up encryption keys to a secure vault",
            "Verify encryption is active via platform-native validation",
            "Plan column-level encryption for highest-sensitivity fields",
            "Capture verification evidence for the audit package",
        ],
        "suggested_owner": "dba",
        "estimated_effort": "medium",
        "priority": "immediate",
    },

    # ── CONFIG ──
    ("config", "high"): {
        "risk_summary": "Insecure or non-standard configuration detected that deviates from hardening baselines.",
        "business_impact": "Configuration drift from hardening standards (CIS, vendor baselines) is a recurring audit theme under PCI DSS 2.2 and ISO 27001.",
        "remediation_steps": [
            "Compare current configuration against the hardening baseline",
            "Document each deviation and its justification (if any)",
            "Remediate unjustified deviations",
            "Re-scan to confirm compliance with baseline",
            "Add configuration to drift monitoring",
        ],
        "suggested_owner": "sysadmin",
        "estimated_effort": "medium",
        "priority": "this_week",
    },
    ("config", "medium"): {
        "risk_summary": "Configuration hygiene issues detected — accumulation of unused or undocumented settings that increase audit complexity.",
        "business_impact": "Configuration sprawl slows audits and obscures real risks. Cleanup is low-effort, high-signal governance work.",
        "remediation_steps": [
            "Inventory flagged configuration items",
            "Confirm with owners whether items are still required",
            "Remove or document each item",
            "Update configuration management records",
        ],
        "suggested_owner": "sysadmin",
        "estimated_effort": "low",
        "priority": "this_month",
    },

    # ── ENDPOINT ──
    ("endpoint", "high"): {
        "risk_summary": "Endpoint protection gaps detected — missing, outdated, or misconfigured anti-malware/EDR coverage.",
        "business_impact": "Anti-malware coverage is explicitly required by PCI DSS 5.2 and HIPAA. Gaps are quick audit findings with straightforward fixes.",
        "remediation_steps": [
            "Identify all endpoints with missing or outdated protection",
            "Push agent installation/update via management console",
            "Verify definition updates are applying automatically",
            "Configure alerting for agents that go stale",
            "Document coverage percentage for audit evidence",
        ],
        "suggested_owner": "security_team",
        "estimated_effort": "low",
        "priority": "this_week",
    },
}

# Fallback template when no specific match
DEFAULT_TEMPLATE = {
    "risk_summary": "A governance finding was detected that requires review against your active compliance framework.",
    "business_impact": "Unresolved findings accumulate audit risk and may indicate control gaps requiring remediation before the next assessment.",
    "remediation_steps": [
        "Review the finding details and affected system",
        "Assess actual risk in your environment context",
        "Plan and execute remediation",
        "Verify the issue is resolved",
        "Document the resolution for audit evidence",
    ],
    "suggested_owner": "security_team",
    "estimated_effort": "medium",
    "priority": "this_week",
}


def get_template(category: str, severity: str) -> dict:
    """Lookup with graceful fallback: exact → category+high → default."""
    return (TEMPLATES.get((category, severity))
            or TEMPLATES.get((category, "high"))
            or TEMPLATES.get((category, "critical"))
            or DEFAULT_TEMPLATE)


def enrich_event_from_template(event: dict, framework_key: str) -> dict:
    """Zero-cost enrichment using the template library."""
    t = get_template(event.get("category", ""), event.get("severity", "medium"))
    controls = (event.get("framework_mappings") or {}).get(framework_key, [])
    ctrl_text = f" Mapped controls: {', '.join(controls)}." if controls else ""
    return {
        "risk_summary": t["risk_summary"] + ctrl_text,
        "business_impact": t["business_impact"],
        "recommendation": " → ".join(t["remediation_steps"][:3]),
        "remediation_steps": t["remediation_steps"],
        "effort": t["estimated_effort"],
        "priority": t["priority"],
        "source": "template",  # tells the UI this was free
    }


def generate_ticket_from_template(event: dict, framework_key: str) -> dict:
    """Zero-cost ticket generation using the template library."""
    t = get_template(event.get("category", ""), event.get("severity", "medium"))
    controls = (event.get("framework_mappings") or {}).get(framework_key, [])
    title = event.get("title", "Governance finding")

    description = (
        f"{event.get('description', '')}\n\n"
        f"RISK: {t['risk_summary']}\n\n"
        f"IMPACT: {t['business_impact']}"
    )
    if controls:
        description += f"\n\nMAPPED CONTROLS ({framework_key.upper().replace('_',' ')}): {', '.join(controls)}"

    return {
        "ticket_title": f"Remediate: {title}",
        "ticket_description": description,
        "acceptance_criteria": "The finding is remediated, verified by re-scan or manual confirmation, and evidence is attached for the audit package.",
        "remediation_steps": t["remediation_steps"],
        "estimated_effort": t["estimated_effort"],
        "suggested_owner": t["suggested_owner"],
        "source": "template",
    }


def generate_audit_summary_from_template(tenant: dict, stats: dict, framework_name: str) -> str:
    """Zero-cost audit summary with live numbers filled in."""
    score = stats.get("score", 0)
    critical = stats.get("critical", 0)
    high = stats.get("high", 0)
    resolved = stats.get("resolved", 0)
    connectors = stats.get("connectors", 0)
    open_tickets = stats.get("open_tickets", 0)

    posture = ("strong" if score >= 85 else
               "moderate, with focused remediation required" if score >= 70 else
               "below audit-ready thresholds and requires immediate attention")

    risk_line = ""
    if critical > 0:
        risk_line = (f"The assessment identified {critical} critical finding{'s' if critical != 1 else ''} "
                     f"that represent automatic audit failure points and should be remediated before the next assessment period. ")
    if high > 0:
        risk_line += (f"An additional {high} high-severity finding{'s' if high != 1 else ''} "
                      f"require remediation within standard SLA windows. ")

    return (
        f"Compliance posture for {tenant.get('name', 'the organization')} under {framework_name} "
        f"currently stands at {score}%, which is {posture}.\n\n"
        f"{risk_line}"
        f"There are {open_tickets} open remediation tickets in the governance workflow, "
        f"with {resolved} findings resolved and documented this period — each with full chain of custody.\n\n"
        f"Continuous evidence collection is active across {connectors} connected systems, "
        f"providing real-time visibility into control status. All remediation decisions are tracked through "
        f"the human-in-the-loop approval workflow with timestamped, attributed audit trails.\n\n"
        f"Recommended focus for the next period: resolve all critical findings, "
        f"maintain the current remediation velocity, and review control coverage quarterly as the environment evolves."
    )
