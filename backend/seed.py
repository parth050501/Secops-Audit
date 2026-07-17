"""
Seed script — creates demo users, tenant, connectors, events, and tickets.
Everything needed to see the full platform without an API key.
Run: python seed.py
"""
import asyncio, sys, random
from datetime import datetime, timedelta
sys.path.insert(0, ".")

from app.core.database import init_db, AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.tenant import Tenant
from app.models.connector import Connector
from app.models.event import GovernanceEvent
from app.models.ticket import Ticket
from app.models.audit_log import AuditLog
from sqlalchemy import select

EVENTS_DATA = [
    {"title":"Any-to-any firewall rule detected — PA-CORP rule 44","severity":"critical","category":"network_security",
     "description":"A firewall rule permits unrestricted traffic from any source to any destination across the WAN-to-LAN segment. This violates PCI DSS 1.2 and 1.1.",
     "framework_mappings":{"pci_dss":["1.2","1.1"],"iso27001":["A.8.20"],"nist_csf":["PR.PT"]},"conn_idx":0},
    {"title":"IAM users with console access and no MFA — 7 accounts","severity":"critical","category":"identity",
     "description":"CloudTrail identifies 7 IAM users with AWS console access who do not have MFA enabled. Violates PCI DSS 8.4.",
     "framework_mappings":{"pci_dss":["8.4"],"sox":["CC6.1"],"iso27001":["A.8.5"]},"conn_idx":2},
    {"title":"Terminated employee accounts still active — 3 accounts","severity":"critical","category":"access_control",
     "description":"3 accounts linked to employees terminated in the past 30 days remain active in Active Directory.",
     "framework_mappings":{"pci_dss":["8.2","7.2"],"sox":["CC6.3"],"hipaa":["164.308(a)(3)"]},"conn_idx":3},
    {"title":"Audit logging disabled — Windows Server SRV-APP-02","severity":"high","category":"logging",
     "description":"Windows Security audit log is disabled on SRV-APP-02. Logon events and privilege use not being recorded.",
     "framework_mappings":{"pci_dss":["10.2","10.3"],"hipaa":["164.312(b)"],"sox":["CC7.1"]},"conn_idx":1},
    {"title":"RDP exposed to public internet (0.0.0.0/0) — FW-PROD","severity":"high","category":"network_security",
     "description":"Remote Desktop Protocol accessible from all internet addresses. High brute-force risk.",
     "framework_mappings":{"pci_dss":["1.2","8.4"],"iso27001":["A.8.20"]},"conn_idx":0},
    {"title":"Stale user accounts — 23 accounts inactive 90+ days","severity":"high","category":"identity",
     "description":"23 user accounts have not logged in for 90+ days but remain enabled with full access in Active Directory.",
     "framework_mappings":{"pci_dss":["8.2"],"sox":["CC6.3"],"hipaa":["164.308(a)(3)"]},"conn_idx":3},
    {"title":"Missing critical patches — 15 CVEs, oldest 47 days","severity":"high","category":"patching",
     "description":"15 critical CVEs unpatched across Linux production servers. Includes CVSS 9.8 vulnerability.",
     "framework_mappings":{"pci_dss":["6.3","11.3"],"hipaa":["164.308(a)(1)"],"iso27001":["A.8.8"]},"conn_idx":1},
    {"title":"Log retention 87 days — below 90-day PCI DSS minimum","severity":"medium","category":"logging",
     "description":"Splunk retention policy is 87 days. PCI DSS 10.3.3 requires 90 days online and 12 months total.",
     "framework_mappings":{"pci_dss":["10.3"],"sox":["CC7.2"]},"conn_idx":4},
    {"title":"S3 bucket prod-customer-data has public read access","severity":"critical","category":"data_protection",
     "description":"S3 bucket contains customer PII with public-read ACL applied. Data is accessible without authentication.",
     "framework_mappings":{"pci_dss":["3.4","1.2"],"hipaa":["164.312(c)"],"iso27001":["A.8.24"]},"conn_idx":2},
    {"title":"SSH root login permitted on 4 Linux servers","severity":"high","category":"access_control",
     "description":"PermitRootLogin=yes in sshd_config on 4 production Linux hosts. Direct root SSH login allowed.",
     "framework_mappings":{"pci_dss":["8.2","7.2"],"iso27001":["A.8.5"]},"conn_idx":1},
    {"title":"Database audit logging not enabled — SQL Server PROD-DB-01","severity":"high","category":"logging",
     "description":"SQL Server audit specification not configured. DML/DDL operations not being logged on production database.",
     "framework_mappings":{"pci_dss":["10.2"],"hipaa":["164.312(b)"],"sox":["CC7.1"]},"conn_idx":5},
    {"title":"Sensitive data stored unencrypted — TDE disabled on PROD-DB-01","severity":"critical","category":"encryption",
     "description":"Transparent Data Encryption not enabled on production database containing cardholder data.",
     "framework_mappings":{"pci_dss":["3.4","4.2"],"hipaa":["164.312(e)"],"iso27001":["A.8.24"]},"conn_idx":5},
    {"title":"Unused firewall rules — 47 rules with zero traffic 90+ days","severity":"medium","category":"config",
     "description":"47 firewall rules have had zero traffic in over 90 days and should be reviewed for removal.",
     "framework_mappings":{"pci_dss":["1.1","2.2"],"iso27001":["A.8.20"]},"conn_idx":0},
    {"title":"CloudTrail logging disabled in ap-southeast-1 region","severity":"critical","category":"logging",
     "description":"AWS CloudTrail not enabled in ap-southeast-1. All API activity in this region is unlogged.",
     "framework_mappings":{"pci_dss":["10.2"],"sox":["CC7.1"],"nist_csf":["DE.CM"]},"conn_idx":2},
]

TICKETS_DATA = [
    {"ref":"SECOPS-0001","title":"Restrict any-to-any firewall rule on PA-CORP to approved flows",
     "description":"Firewall rule 44 on PA-CORP permits unrestricted traffic WAN-to-LAN. Must be replaced with specific allow rules per PCI DSS 1.2.",
     "severity":"critical","category":"network_security","framework":"pci_dss","control_ids":["1.2","1.1"],
     "status":"in_review","remediation_steps":"1. Pull 30-day traffic logs for rule 44\n2. Document all active flows with business owners\n3. Create specific allow rules per flow\n4. Schedule maintenance window\n5. Remove rule 44 and monitor 72h",
     "ai_recommendation":"Replace with least-privilege specific rules. Estimated 3-5 replacement rules based on typical traffic patterns.",
     "history":[
         {"timestamp":(datetime.utcnow()-timedelta(days=3)).isoformat(),"user":"Jordan Lee","action":"created","notes":"Ticket created from governance event"},
         {"timestamp":(datetime.utcnow()-timedelta(days=2)).isoformat(),"user":"Jordan Lee","action":"open → assigned","notes":"Taking ownership"},
         {"timestamp":(datetime.utcnow()-timedelta(days=1)).isoformat(),"user":"Jordan Lee","action":"assigned → in_review","notes":"Traffic analysis complete. 3 specific flows identified. Change drafted."},
     ],"event_idx":0},
    {"ref":"SECOPS-0002","title":"Enforce MFA on 7 AWS IAM console accounts",
     "description":"7 IAM users have console access without MFA. Violates PCI DSS 8.4. IAM SCP to be applied.",
     "severity":"critical","category":"identity","framework":"pci_dss","control_ids":["8.4","8.2"],
     "status":"assigned",
     "remediation_steps":"1. List all 7 non-MFA accounts\n2. Identify service vs human accounts\n3. Convert service accounts to programmatic-only\n4. Send MFA enrollment to humans with 24h deadline\n5. Apply SCP to deny console without MFA",
     "ai_recommendation":"Apply AWS IAM SCP at organization root to deny console access without MFA. This prevents future drift.",
     "history":[
         {"timestamp":(datetime.utcnow()-timedelta(days=2)).isoformat(),"user":"Alex Kim","action":"created","notes":""},
         {"timestamp":(datetime.utcnow()-timedelta(hours=18)).isoformat(),"user":"Jordan Lee","action":"open → assigned","notes":"Cloud team assigned"},
     ],"event_idx":1},
    {"ref":"SECOPS-0003","title":"Disable terminated employee accounts in Active Directory — 3 accounts",
     "description":"3 accounts for terminated employees remain active. Cross-referenced with HR system confirmed terminations 14-28 days ago.",
     "severity":"critical","category":"access_control","framework":"pci_dss","control_ids":["8.2","7.2"],
     "status":"accepted","approved_at":datetime.utcnow()-timedelta(hours=4),
     "remediation_steps":"1. Confirm termination dates with HR\n2. Disable accounts immediately\n3. Revoke all active sessions\n4. Move to disabled OU\n5. Document in HR ticketing system",
     "ai_recommendation":"Implement automated deprovisioning tied to HR system to prevent recurrence. This is a recurring finding.",
     "resolution_notes":"Accounts disabled. HR integration project added to Q3 roadmap.",
     "history":[
         {"timestamp":(datetime.utcnow()-timedelta(days=5)).isoformat(),"user":"Alex Kim","action":"created","notes":""},
         {"timestamp":(datetime.utcnow()-timedelta(days=4)).isoformat(),"user":"Jordan Lee","action":"open → assigned","notes":""},
         {"timestamp":(datetime.utcnow()-timedelta(days=3)).isoformat(),"user":"Jordan Lee","action":"assigned → in_review","notes":"Accounts identified, cross-referenced with HR"},
         {"timestamp":(datetime.utcnow()-timedelta(hours=4)).isoformat(),"user":"Sam Rivera","action":"in_review → accepted","notes":"Approved. Proceed with disabling accounts."},
     ],"event_idx":2},
    {"ref":"SECOPS-0004","title":"Re-enable audit logging on Windows Server SRV-APP-02",
     "description":"Security audit logging is disabled. Must be re-enabled and SIEM forwarding restored.",
     "severity":"high","category":"logging","framework":"pci_dss","control_ids":["10.2","10.3"],
     "status":"open",
     "remediation_steps":"1. Enable audit policy via Group Policy\n2. Verify Event Viewer populating\n3. Confirm Splunk forwarding active\n4. Set alert for future disablement\n5. Document root cause",
     "ai_recommendation":"Enable via GPO rather than locally to prevent bypass. Add SIEM alert for audit policy changes.",
     "history":[{"timestamp":(datetime.utcnow()-timedelta(hours=6)).isoformat(),"user":"Alex Kim","action":"created","notes":""}],
     "event_idx":3},
    {"ref":"SECOPS-0005","title":"Enable TDE encryption on production SQL Server PROD-DB-01",
     "description":"Transparent Data Encryption disabled on production database containing cardholder data. Critical PCI DSS 3.4 gap.",
     "severity":"critical","category":"encryption","framework":"pci_dss","control_ids":["3.4","4.2"],
     "status":"remediated",
     "remediation_steps":"1. Enable TDE on PROD-DB-01\n2. Backup encryption key to secure vault\n3. Verify data-at-rest encryption\n4. Document in evidence package",
     "ai_recommendation":"Also enable Always Encrypted for columns containing PANs for defense in depth.",
     "resolution_notes":"TDE enabled successfully. Encryption key backed up to CyberArk. Verified via SQL Server DMV.",
     "history":[
         {"timestamp":(datetime.utcnow()-timedelta(days=7)).isoformat(),"user":"Alex Kim","action":"created","notes":""},
         {"timestamp":(datetime.utcnow()-timedelta(days=6)).isoformat(),"user":"Jordan Lee","action":"open → assigned","notes":"DBA team"},
         {"timestamp":(datetime.utcnow()-timedelta(days=5)).isoformat(),"user":"Jordan Lee","action":"assigned → in_review","notes":"TDE tested in staging, no performance impact"},
         {"timestamp":(datetime.utcnow()-timedelta(days=4)).isoformat(),"user":"Sam Rivera","action":"in_review → accepted","notes":"Approved for production"},
         {"timestamp":(datetime.utcnow()-timedelta(days=2)).isoformat(),"user":"Jordan Lee","action":"accepted → remediated","notes":"TDE enabled on PROD-DB-01. Key stored in CyberArk vault."},
     ],"event_idx":11},
]

async def seed():
    await init_db()
    # Safety: refuse to seed demo accounts in production unless explicitly forced.
    # Demo accounts (admin@secops.ai/password etc.) must never exist on a real
    # hosted environment. To intentionally seed a production box (e.g. to create
    # the first super-admin), set ALLOW_PROD_SEED=1 and prefer changing the
    # default credentials immediately after.
    import os
    if os.environ.get("ENVIRONMENT") == "production" and os.environ.get("ALLOW_PROD_SEED") != "1":
        print("Refusing to seed demo data in production.")
        print("Set ALLOW_PROD_SEED=1 to override (and change default passwords immediately).")
        return
    async with AsyncSessionLocal() as db:

        # ── Users ──────────────────────────────────────────────────────────────
        user_records = {}
        for email, name, role, pw in [
            ("admin@secops.ai",    "Alex Kim",     "admin",    "password"),
            ("engineer@secops.ai", "Jordan Lee",   "engineer", "password"),
            ("manager@secops.ai",  "Sam Rivera",   "manager",  "password"),
            ("auditor@secops.ai",  "Taylor Chen",  "auditor",  "password"),
        ]:
            u = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if not u:
                u = User(email=email, name=name, role=role, hashed_pw=hash_password(pw))
                db.add(u)
                await db.flush()
                print(f"  ✓ {role}: {email} / {pw}")
            user_records[role] = u
        await db.commit()

        # ── Tenant ─────────────────────────────────────────────────────────────
        admin = (await db.execute(select(User).where(User.email == "admin@secops.ai"))).scalar_one()
        t = (await db.execute(select(Tenant).where(Tenant.name == "Acme Financial Inc."))).scalar_one_or_none()
        if not t:
            t = Tenant(
                name="Acme Financial Inc.",
                industry="financial",
                frameworks=["pci_dss","sox","iso27001","nist_csf"],
                active_framework="pci_dss",
                scan_schedule="realtime",
                onboarded=True,
            )
            db.add(t); await db.flush()
            print(f"  ✓ Tenant: {t.name} (PCI DSS)")
        tid = t.id

        # Link users to tenant
        for u in (await db.execute(select(User))).scalars().all():
            if not u.tenant_id:
                u.tenant_id = tid
        await db.commit()

        # ── Connectors ─────────────────────────────────────────────────────────
        connectors_data = [
            {"name":"PA-CORP","category":"network","connector_type":"paloalto","host":"10.0.0.1"},
            {"name":"SRV-APP-02 / SRV-DB-01","category":"server","connector_type":"windows_server","host":"10.10.1.0/24"},
            {"name":"AWS Production","category":"cloud","connector_type":"aws","host":"123456789012"},
            {"name":"Active Directory","category":"identity","connector_type":"active_directory","host":"dc01.acme.local"},
            {"name":"Splunk SIEM","category":"siem","connector_type":"splunk","host":"splunk.acme.local"},
            {"name":"PROD-DB-01","category":"database","connector_type":"sql_server","host":"10.10.2.50"},
        ]
        conn_records = []
        for cd in connectors_data:
            c = (await db.execute(select(Connector).where(Connector.name == cd["name"], Connector.tenant_id == tid))).scalar_one_or_none()
            if not c:
                c = Connector(**cd, tenant_id=tid, status="connected",
                              realtime=True, collection_mode="polling",
                              last_seen=datetime.utcnow()-timedelta(minutes=random.randint(1,30)))
                db.add(c); await db.flush()
                print(f"  ✓ Connector: {c.name}")
            conn_records.append(c)
        await db.commit()

        # ── Events ─────────────────────────────────────────────────────────────
        existing_ev = len((await db.execute(select(GovernanceEvent).where(GovernanceEvent.tenant_id == tid))).scalars().all())
        ev_records = []
        if not existing_ev:
            for i, ed in enumerate(EVENTS_DATA):
                conn = conn_records[ed.pop("conn_idx")]
                ev = GovernanceEvent(
                    tenant_id=tid, connector_id=conn.id,
                    source_type="realtime" if i % 3 != 0 else "scheduled_scan",
                    occurred_at=datetime.utcnow()-timedelta(hours=random.randint(1,72)),
                    status="open", **ed
                )
                db.add(ev); ev_records.append(ev)
            await db.flush()
            print(f"  ✓ Events: {len(EVENTS_DATA)} governance events")
        else:
            ev_records = (await db.execute(select(GovernanceEvent).where(GovernanceEvent.tenant_id == tid))).scalars().all()

        await db.commit()

        # ── Tickets ────────────────────────────────────────────────────────────
        existing_tk = len((await db.execute(select(Ticket).where(Ticket.tenant_id == tid))).scalars().all())
        if not existing_tk:
            admin_u = (await db.execute(select(User).where(User.email == "admin@secops.ai"))).scalar_one()
            eng_u   = (await db.execute(select(User).where(User.email == "engineer@secops.ai"))).scalar_one()
            mgr_u   = (await db.execute(select(User).where(User.email == "manager@secops.ai"))).scalar_one()

            ev_list = (await db.execute(select(GovernanceEvent).where(GovernanceEvent.tenant_id == tid))).scalars().all()

            for td in TICKETS_DATA:
                ev_idx  = td.pop("event_idx")
                ev_obj  = ev_list[ev_idx] if ev_idx < len(ev_list) else ev_list[0]
                app_at  = td.pop("approved_at", None)
                res_notes = td.pop("resolution_notes", None)

                tk = Ticket(
                    tenant_id=tid,
                    event_id=ev_obj.id,
                    connector_id=ev_obj.connector_id,
                    created_by=admin_u.id,
                    assigned_to=eng_u.id,
                    approved_by=mgr_u.id if td["status"] in ("accepted","remediated") else None,
                    approved_at=app_at,
                    resolution_notes=res_notes,
                    due_date=datetime.utcnow()+timedelta(days=30),
                    **td
                )
                db.add(tk); await db.flush()
                ev_obj.status = "ticketed"; ev_obj.ticket_id = tk.id

            print(f"  ✓ Tickets: {len(TICKETS_DATA)} tickets created")

        # ── Audit log entries ──────────────────────────────────────────────────
        existing_logs = len((await db.execute(select(AuditLog).where(AuditLog.tenant_id == tid))).scalars().all())
        if not existing_logs:
            for action, entity, details in [
                ("tenant_created",  "tenant",    {"name":"Acme Financial Inc.","frameworks":["pci_dss","sox"]}),
                ("connector_added", "connector", {"name":"PA-CORP","type":"paloalto"}),
                ("connector_added", "connector", {"name":"AWS Production","type":"aws"}),
                ("connector_added", "connector", {"name":"Active Directory","type":"active_directory"}),
                ("scan_triggered",  "connector", {"connector_name":"PA-CORP"}),
                ("ticket_created",  "ticket",    {"ref":"SECOPS-0001","severity":"critical"}),
                ("ticket_assigned", "ticket",    {"ref":"SECOPS-0001","new_status":"assigned"}),
                ("ticket_accepted", "ticket",    {"ref":"SECOPS-0003","notes":"Approved"}),
                ("ticket_remediated","ticket",   {"ref":"SECOPS-0005","notes":"TDE enabled"}),
                ("framework_changed","framework",{"framework":"pci_dss"}),
            ]:
                db.add(AuditLog(
                    tenant_id=tid, user_id=admin.id, user_name=admin.name,
                    action=action, entity_type=entity, details=details,
                    timestamp=datetime.utcnow()-timedelta(hours=random.randint(1,168))
                ))
            print("  ✓ Audit log: 10 entries")

        # ── Custom policies (the 10%) ──
        from app.models.custom_policy import CustomPolicy
        existing_pol = len((await db.execute(select(CustomPolicy).where(CustomPolicy.tenant_id == tid))).scalars().all())
        if not existing_pol:
            admin_u2 = (await db.execute(select(User).where(User.email == "admin@secops.ai"))).scalar_one()
            policies = [
                CustomPolicy(tenant_id=tid, policy_id="ACME-SEC-001", title="Quarterly privileged access review completed",
                             description="All privileged accounts must be reviewed every quarter by the security team.",
                             category="access_control", severity="high", framework="custom", mapped_control="CC6.1",
                             eval_mode="manual", status="passing", last_result="Q1 review completed and signed off",
                             created_by=admin_u2.id),
                CustomPolicy(tenant_id=tid, policy_id="ACME-SEC-002", title="No critical findings on cloud infrastructure",
                             description="Cloud connectors must have zero open critical findings.",
                             category="network_security", severity="critical", framework="custom",
                             eval_mode="connector", target_connector_category="cloud", status="not_assessed",
                             created_by=admin_u2.id),
                CustomPolicy(tenant_id=tid, policy_id="ACME-SEC-003", title="Production databases must have encryption enabled",
                             description="Rule: fail if any database event indicates TDE/encryption disabled.",
                             category="encryption", severity="critical", framework="custom", mapped_control="3.4",
                             eval_mode="rule", target_connector_category="database",
                             rule_logic={"field":"connector_type","operator":"equals","value":"sql_server"},
                             status="not_assessed", created_by=admin_u2.id),
            ]
            for p in policies:
                db.add(p)
            print(f"  \u2713 Custom policies: {len(policies)} created")

        # ── Platform admin (super-admin / SaaS operator) ──
        from app.models.platform import PlatformAdmin, TenantBilling, PLAN_DEFAULTS
        super_admin = (await db.execute(select(PlatformAdmin).where(PlatformAdmin.email == "super@secops.ai"))).scalar_one_or_none()
        if not super_admin:
            super_admin = PlatformAdmin(email="super@secops.ai", name="Platform Operator",
                                        role="super_admin",
                                        hashed_pw=hash_password("superpassword"))
            db.add(super_admin)
            print("  \u2713 Platform admin: super@secops.ai / superpassword")

        # Billing record for primary tenant
        bill = (await db.execute(select(TenantBilling).where(TenantBilling.tenant_id == tid))).scalar_one_or_none()
        if not bill:
            d = PLAN_DEFAULTS["professional"]
            db.add(TenantBilling(tenant_id=tid, plan="professional", status="active",
                                 mrr=d["mrr"], seats=d["seats"], connectors_limit=d["connectors_limit"],
                                 ai_credits_monthly=d["ai_credits_monthly"], billing_email="billing@acme.com"))
            print("  \u2713 Billing: Acme on Professional ($1499/mo)")

        # ── Second demo tenant so the platform console has multiple to manage ──
        t2 = (await db.execute(select(Tenant).where(Tenant.name == "HealthTrust Medical"))).scalar_one_or_none()
        if not t2:
            t2 = Tenant(name="HealthTrust Medical", industry="healthcare",
                        frameworks=["hipaa","soc2","hitrust"], active_framework="hipaa",
                        scan_schedule="realtime", onboarded=True)
            db.add(t2); await db.flush()
            # a couple of users
            db.add(User(email="admin@healthtrust.com", name="Dana Wells", role="admin",
                        hashed_pw=hash_password("password"), tenant_id=t2.id))
            db.add(User(email="auditor@healthtrust.com", name="Raj Patel", role="auditor",
                        hashed_pw=hash_password("password"), tenant_id=t2.id))
            d = PLAN_DEFAULTS["starter"]
            db.add(TenantBilling(tenant_id=t2.id, plan="starter", status="trial",
                                 mrr=d["mrr"], seats=d["seats"], connectors_limit=d["connectors_limit"],
                                 ai_credits_monthly=d["ai_credits_monthly"], billing_email="billing@healthtrust.com"))
            print("  \u2713 Second tenant: HealthTrust Medical (HIPAA, trial)")

        await db.commit()

    print("\n✅ Seed complete!")
    print("\nDemo accounts:")
    print("  admin@secops.ai    / password  (admin)")
    print("  engineer@secops.ai / password  (engineer)")
    print("  manager@secops.ai  / password  (manager)")
    print("  auditor@secops.ai  / password  (auditor)")
    print("\nPlatform console (manage all tenants):")
    print("  super@secops.ai / superpassword  -> http://localhost:3000/platform")
    print("\nVisit http://localhost:3000")
    print("No API key needed — demo mode active.")

asyncio.run(seed())
