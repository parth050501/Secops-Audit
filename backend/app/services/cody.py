"""
Cody integration (platform side).

Cody is the AI compliance assistant, hosted as a SEPARATE service. The platform
is responsible for the security boundary: it authenticates the user, determines
their tenant (their own, or the tenant a CodeCore operator has impersonated
into), gathers ONLY that tenant's compliance data, and sends it to Cody. Cody
answers from that data and never touches the database.

Configuration (set when you deploy Cody):
  CODY_SERVICE_URL    e.g. https://cody.codecoresystems.in   (your subdomain)
  CODY_SHARED_SECRET  a strong secret shared between platform and Cody, so only
                      the platform can call Cody (Cody rejects calls without it)

If CODY_SERVICE_URL is not set, the chat endpoint returns a clear "not configured"
message instead of failing.
"""
import os
import json
import logging
import urllib.request
import urllib.error

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.event import GovernanceEvent

log = logging.getLogger("cody")

CODY_SERVICE_URL = os.environ.get("CODY_SERVICE_URL", "").rstrip("/")
CODY_SHARED_SECRET = os.environ.get("CODY_SHARED_SECRET", "")


class CodyNotConfigured(Exception):
    pass


class CodyUnreachable(Exception):
    pass


async def build_tenant_posture(db: AsyncSession, tenant_id: int) -> dict:
    """Assemble the compliance posture for ONE tenant. Every query is scoped to
    tenant_id — this is the isolation boundary. Cody only ever receives this."""
    tenant = (await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )).scalar_one_or_none()
    if not tenant:
        raise ValueError("tenant not found")

    # Open findings for THIS tenant only
    events = (await db.execute(
        select(GovernanceEvent).where(
            GovernanceEvent.tenant_id == tenant_id,
            GovernanceEvent.status != "resolved",
        )
    )).scalars().all()

    selected_frameworks = tenant.frameworks or [tenant.active_framework]

    # Severity tallies
    sev_counts = {"high": 0, "medium": 0, "low": 0}
    findings = []
    controls_hit = set()
    for e in events:
        sev = (e.severity or "medium").lower()
        if sev in sev_counts:
            sev_counts[sev] += 1
        # framework_mappings: {framework: [control ids]} — keep only SELECTED frameworks
        fmap = e.framework_mappings or {}
        relevant = {fw: ctrls for fw, ctrls in fmap.items() if fw in selected_frameworks}
        for ctrls in relevant.values():
            for c in ctrls:
                controls_hit.add(c)
        findings.append({
            "title": e.title,
            "severity": sev,
            "system": (e.raw_data or {}).get("source", "unknown") if isinstance(e.raw_data, dict) else "unknown",
            "controls": sorted({c for ctrls in relevant.values() for c in ctrls}),
            "frameworks": sorted(relevant.keys()),
            "status": e.status or "open",
        })

    posture = {
        "organization": tenant.name,
        "active_framework": tenant.active_framework,
        "selected_frameworks": selected_frameworks,
        "summary": {
            "total_open_findings": len(events),
            "high_severity": sev_counts["high"],
            "medium_severity": sev_counts["medium"],
            "low_severity": sev_counts["low"],
            "controls_with_open_findings": len(controls_hit),
        },
        "findings": findings[:100],   # cap to keep the prompt bounded
    }
    return posture


async def ask_cody(db: AsyncSession, tenant_id: int, message: str, history: list) -> str:
    """Scope data to tenant_id, call the Cody service, return the answer."""
    if not CODY_SERVICE_URL:
        raise CodyNotConfigured(
            "Cody is not configured yet. Set CODY_SERVICE_URL (and CODY_SHARED_SECRET) "
            "to your deployed Cody service."
        )

    posture = await build_tenant_posture(db, tenant_id)

    body = json.dumps({
        "message": message,
        "history": history[-8:] if history else [],
        "posture": posture,           # the ONLY data Cody sees — this one tenant's
    }).encode()

    req = urllib.request.Request(
        f"{CODY_SERVICE_URL}/api/chat",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Cody-Secret": CODY_SHARED_SECRET,   # authenticates platform -> Cody
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:200]
        raise CodyUnreachable(f"Cody returned {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise CodyUnreachable(f"Could not reach Cody: {e}")

    return data.get("answer", "(no answer)")
