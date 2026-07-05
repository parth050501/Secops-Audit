"""
AI service with demo mode fallback.
If ANTHROPIC_API_KEY is missing/placeholder, all functions return
realistic pre-written responses so the full platform works without a key.
"""
import random
from app.core.config import settings

def _is_demo():
    key = settings.anthropic_api_key or ""
    return not key or key.startswith("sk-ant-your") or len(key) < 20

# ── Demo responses ─────────────────────────────────────────────────────────────

DEMO_ENRICHMENTS = [
    {
        "risk_summary": "This finding represents a critical control failure that directly violates the principle of least privilege. Unrestricted network access exposes sensitive systems to lateral movement and data exfiltration.",
        "business_impact": "A breach exploiting this exposure could result in regulatory fines, customer data loss, and audit failure. PCI DSS non-compliance carries fines of $5,000-$100,000 per month.",
        "recommendation": "Immediately restrict the rule to specific source/destination pairs. Replace any-to-any rules with explicit allow rules based on documented business need.",
        "remediation_steps": ["Identify all traffic currently using this rule via firewall logs", "Document legitimate business flows that require this access", "Create specific rules for each approved flow", "Remove the any-to-any rule and monitor for breakage", "Verify no alerts trigger within 48h and close the ticket"],
        "effort": "medium",
        "priority": "immediate"
    },
    {
        "risk_summary": "Privileged accounts without MFA are a primary attack vector for credential-based intrusions. Attackers with stolen credentials gain immediate admin access with no secondary verification barrier.",
        "business_impact": "Admin account compromise could result in full environment takeover and data exfiltration. Average breach cost in financial services exceeds $5.9M.",
        "recommendation": "Enable MFA on all privileged accounts within 24 hours. Use authenticator apps — SMS-based MFA is not compliant with PCI DSS 8.4.",
        "remediation_steps": ["Enumerate all admin accounts missing MFA", "Enforce MFA policy at the directory level", "Notify affected users with a 24-hour deadline", "Verify MFA enrollment for each account", "Block console access for any account still non-compliant after deadline"],
        "effort": "low",
        "priority": "immediate"
    },
    {
        "risk_summary": "Disabled audit logging creates a blind spot that prevents detection of unauthorized access and makes forensic investigation impossible after an incident.",
        "business_impact": "Without audit logs the organization cannot demonstrate compliance with PCI DSS Requirement 10, HIPAA 164.312(b), or SOX CC7.1. This is an automatic audit failure point.",
        "recommendation": "Re-enable audit logging immediately and verify log forwarding to the central SIEM. Implement log integrity monitoring to detect future tampering.",
        "remediation_steps": ["Enable Windows Security Audit Policy via Group Policy", "Configure log forwarding to SIEM", "Set retention to minimum 90 days online", "Test log collection by generating test events", "Add alerting for future audit log disablement"],
        "effort": "low",
        "priority": "immediate"
    },
    {
        "risk_summary": "Stale accounts represent a significant access control risk — former employees or unused service accounts may still hold valid credentials that could be exploited.",
        "business_impact": "Unauthorized access via stale accounts violates PCI DSS 8.2 and SOX CC6.3. Failure to remove terminated employee access is one of the most common audit findings.",
        "recommendation": "Disable all accounts inactive for 90+ days immediately. Implement an automated provisioning/deprovisioning process tied to HR systems.",
        "remediation_steps": ["Export list of accounts with last logon > 90 days", "Cross-reference with HR termination records", "Disable (do not delete) accounts pending review", "Notify account owners for legitimate inactive accounts", "Implement automated 90-day inactivity policy"],
        "effort": "medium",
        "priority": "this_week"
    },
    {
        "risk_summary": "Unpatched critical CVEs expose systems to known exploits actively used in the wild. At 47 days without patching the risk of exploitation is significantly elevated.",
        "business_impact": "Critical CVEs with CVSS 9.8 scores have public exploit code. Systems in the cardholder data environment must be patched within 30 days of release per PCI DSS.",
        "recommendation": "Apply all critical patches within 24 hours for in-scope systems. Implement automated patch management to prevent recurrence.",
        "remediation_steps": ["Prioritize patches for systems in compliance scope", "Schedule maintenance window for patch deployment", "Test patches in staging before production rollout", "Deploy patches and verify installation", "Run vulnerability scan to confirm remediation"],
        "effort": "medium",
        "priority": "this_week"
    },
]

DEMO_TICKET_DATA = [
    {
        "ticket_title": "Restrict any-to-any firewall rule to specific approved flows",
        "ticket_description": "A firewall rule permits unrestricted traffic from any source to any destination. This violates PCI DSS Requirements 1.2 and 1.1 which mandate that network access controls deny all traffic not explicitly required. This ticket tracks review and replacement with specific documented allow rules.",
        "acceptance_criteria": "The any-to-any rule is removed. Replacement rules exist for all legitimate flows. No connectivity incidents reported within 72 hours. Change signed off by security manager.",
        "remediation_steps": ["Pull 30-day traffic logs to identify all active flows", "Document each flow with business owner and justification", "Create specific allow rules for each approved flow", "Implement in maintenance window and remove the broad rule", "Monitor for 72 hours and confirm no business impact"],
        "estimated_effort": "medium",
        "suggested_owner": "network_team"
    },
    {
        "ticket_title": "Enforce MFA on all privileged accounts without multi-factor authentication",
        "ticket_description": "Multiple privileged accounts have been identified without MFA enabled. This violates PCI DSS Requirement 8.4 and ISO 27001 A.8.5. This ticket tracks enforcement of MFA across all affected accounts.",
        "acceptance_criteria": "All affected accounts have MFA enabled or console access removed. IAM policy updated to deny access without MFA. Evidence screenshots attached.",
        "remediation_steps": ["List all non-MFA privileged accounts", "Identify human users vs service accounts", "Convert service accounts to programmatic access only", "Send MFA enrollment instructions to human account owners", "Apply policy to deny access without MFA"],
        "estimated_effort": "low",
        "suggested_owner": "identity_team"
    },
    {
        "ticket_title": "Re-enable security audit logging and restore SIEM forwarding",
        "ticket_description": "Security event auditing is disabled on a production system. Logon events, privilege use, and policy changes are not being recorded. This violates PCI DSS Requirement 10.2 and HIPAA 164.312(b). Root cause under investigation.",
        "acceptance_criteria": "Audit policy re-enabled for all required categories. Logs forwarding to SIEM confirmed. Log integrity alert configured. Root cause documented.",
        "remediation_steps": ["Enable full audit policy on the affected system", "Verify security events populating in Event Viewer", "Confirm SIEM forwarding is active", "Set alert for future audit policy changes", "Document why logging was disabled"],
        "estimated_effort": "low",
        "suggested_owner": "sysadmin"
    },
]

DEMO_AUDIT_SUMMARY = """The compliance assessment for {name} under {framework} reveals a posture that requires immediate attention in several key control areas, while demonstrating strength in foundational security processes.

The most significant risk areas are identity and access management, where privileged accounts lack multi-factor authentication, and network security, where broad firewall rules expose the environment to unrestricted lateral movement. These findings represent critical control failures and should be treated as the highest remediation priority before the upcoming audit period.

On a positive note, the organization demonstrates strong evidence collection practices with {connectors} integrated data sources providing continuous visibility. The ticket resolution rate shows active engagement from the security team, with {resolved} findings remediated and documented with full chain of custody. Core logging infrastructure is operational across the majority of in-scope systems.

For the next audit period, the recommended focus areas are: completing MFA rollout for all privileged accounts, implementing a formal firewall rule review process on a quarterly cadence, and extending log retention to meet the 90-day minimum threshold. Addressing these three areas would bring the compliance score from the current {score}% to an estimated 88-92%, representing a strong audit posture."""

DEMO_CHAT_RESPONSES = [
    "Based on your current posture, the most critical action is addressing the open critical findings — particularly the any-to-any firewall rule and accounts without MFA. These are automatic audit findings. I'd recommend creating tickets for both today and targeting resolution within 72 hours.",
    "Your compliance score is below the recommended 80% threshold for audit readiness. The primary drivers are identity control failures and network security gaps. Resolving the critical findings would bring your score to approximately 83%.",
    "For your upcoming audit, auditors will focus heavily on audit logs, authentication controls, and network segmentation. Your current gaps in all three areas mean you should plan remediation at least 30 days before the audit date to allow evidence collection time.",
    "The stale account finding is common and straightforward to fix. The key is having a documented process — auditors want to see an automated or semi-automated deprovisioning workflow, not just a one-time cleanup.",
    "Evidence collection looks good across your connected systems. I can generate a formatted audit package with configs, log retention confirmation, access reviews, and the full ticket history showing your remediation activity.",
]


async def _call_claude(prompt: str, max_tokens: int = 1000) -> str:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    msg = await client.messages.create(
        model="claude-opus-4-5", max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


async def _parse_json(text: str) -> dict:
    import json
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:-1])
    return json.loads(text)


async def enrich_event(event: dict, framework_key: str) -> dict:
    if _is_demo():
        return random.choice(DEMO_ENRICHMENTS)
    from app.frameworks.definitions import FRAMEWORKS
    fw = FRAMEWORKS.get(framework_key, {})
    controls = event.get("framework_mappings", {}).get(framework_key, [])
    prompt = f"""Compliance expert. Framework: {fw.get('name')}. Controls: {', '.join(controls)}.
Finding: {event.get('title')} | {event.get('description')} | Severity: {event.get('severity')}
Return JSON only:
{{"risk_summary":"2 sentences","business_impact":"specific impact","recommendation":"concrete steps",
"remediation_steps":["s1","s2","s3"],"effort":"low|medium|high","priority":"immediate|this_week|this_month"}}"""
    return await _parse_json(await _call_claude(prompt))


async def generate_ticket_description(event: dict, framework_key: str) -> dict:
    if _is_demo():
        base = random.choice(DEMO_TICKET_DATA)
        return {**base, "ticket_title": f"Remediate: {event.get('title', base['ticket_title'])}"}
    from app.frameworks.definitions import FRAMEWORKS
    fw = FRAMEWORKS.get(framework_key, {})
    controls = event.get("framework_mappings", {}).get(framework_key, [])
    prompt = f"""Create a governance ticket. Framework: {fw.get('name')}. Controls: {', '.join(controls)}.
Finding: {event.get('title')} | {event.get('description')} | Severity: {event.get('severity')}
Return JSON only:
{{"ticket_title":"action title","ticket_description":"full description",
"acceptance_criteria":"done-when","remediation_steps":["s1","s2","s3"],
"estimated_effort":"low|medium|high","suggested_owner":"security_team|sysadmin|network_team|cloud_team|identity_team|dba"}}"""
    return await _parse_json(await _call_claude(prompt))


async def generate_audit_summary(tenant: dict, stats: dict, framework_key: str) -> str:
    if _is_demo():
        from app.frameworks.definitions import FRAMEWORKS
        fw = FRAMEWORKS.get(framework_key, {})
        return DEMO_AUDIT_SUMMARY.format(
            name=tenant.get("name", "your organization"),
            framework=fw.get("name", framework_key.upper()),
            connectors=stats.get("connectors", 6),
            resolved=stats.get("resolved", 5),
            score=stats.get("score", 74),
        )
    from app.frameworks.definitions import FRAMEWORKS
    fw = FRAMEWORKS.get(framework_key, {})
    prompt = f"""Professional executive audit summary.
Org: {tenant.get('name')} | Industry: {tenant.get('industry')} | Framework: {fw.get('name')}
Score: {stats.get('score')}% | Critical: {stats.get('critical')} | High: {stats.get('high')}
Open tickets: {stats.get('open_tickets')} | Resolved: {stats.get('resolved')} | Connectors: {stats.get('connectors')}
Write 3-4 paragraphs: overall posture, key risks, positive controls, recommendations."""
    return await _call_claude(prompt, max_tokens=1200)


async def chat_with_context(messages: list, tenant: dict, framework_key: str, stats: dict) -> str:
    if _is_demo():
        last = (messages[-1].get("content", "") if messages else "").lower()
        if any(w in last for w in ["score", "percent", "%"]): return DEMO_CHAT_RESPONSES[1]
        if any(w in last for w in ["audit", "auditor", "upcoming"]): return DEMO_CHAT_RESPONSES[2]
        if any(w in last for w in ["stale", "account", "user"]): return DEMO_CHAT_RESPONSES[3]
        if any(w in last for w in ["evidence", "export", "report"]): return DEMO_CHAT_RESPONSES[4]
        return DEMO_CHAT_RESPONSES[0]
    from app.frameworks.definitions import FRAMEWORKS
    fw = FRAMEWORKS.get(framework_key, {})
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    msg = await client.messages.create(
        model="claude-opus-4-5", max_tokens=1500,
        system=f"You are SecOps AI. Org: {tenant.get('name')} ({tenant.get('industry')}). Framework: {fw.get('name')}. Score: {stats.get('score')}%.",
        messages=messages,
    )
    return msg.content[0].text
