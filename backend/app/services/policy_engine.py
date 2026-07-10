"""
Custom Policy Evaluation Engine.
Evaluates company-defined policies (the '10%') in three modes:
  - manual:    human sets pass/fail
  - connector: policy fails if matching findings exist for a connector category
  - rule:      structured rule logic evaluated against collected data fields
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.custom_policy import CustomPolicy
from app.models.event import GovernanceEvent
from app.models.connector import Connector


OPERATORS = {
    "equals":      lambda a, b: str(a).lower() == str(b).lower(),
    "not_equals":  lambda a, b: str(a).lower() != str(b).lower(),
    "contains":    lambda a, b: str(b).lower() in str(a).lower(),
    "not_contains":lambda a, b: str(b).lower() not in str(a).lower(),
    "gt":          lambda a, b: _num(a) > _num(b),
    "lt":          lambda a, b: _num(a) < _num(b),
    "gte":         lambda a, b: _num(a) >= _num(b),
    "lte":         lambda a, b: _num(a) <= _num(b),
    "exists":      lambda a, b: a is not None,
    "not_exists":  lambda a, b: a is None,
}

OPERATOR_LABELS = {
    "equals": "equals", "not_equals": "does not equal",
    "contains": "contains", "not_contains": "does not contain",
    "gt": "greater than", "lt": "less than",
    "gte": "at least", "lte": "at most",
    "exists": "exists", "not_exists": "does not exist",
}


def _num(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def describe_rule(rule: dict) -> str:
    """Human-readable description of a rule for the UI."""
    if not rule:
        return "No rule defined"
    field = rule.get("field", "?")
    op = OPERATOR_LABELS.get(rule.get("operator", ""), rule.get("operator", "?"))
    value = rule.get("value", "")
    if rule.get("operator") in ("exists", "not_exists"):
        return f"FAIL if '{field}' {op}"
    return f"FAIL if '{field}' {op} '{value}'"


async def evaluate_policy(db: AsyncSession, policy: CustomPolicy) -> dict:
    """Evaluate a single policy. Returns {status, result_text}."""
    if not policy.enabled:
        return {"status": "not_assessed", "result": "Policy disabled"}

    if policy.eval_mode == "manual":
        # Manual policies keep their human-set status
        return {"status": policy.status or "not_assessed",
                "result": policy.last_result or "Awaiting manual attestation"}

    if policy.eval_mode == "connector":
        # Fail if there are open findings in the target connector category
        if not policy.target_connector_category:
            return {"status": "not_assessed", "result": "No target category set"}

        connectors = (await db.execute(
            select(Connector).where(
                Connector.tenant_id == policy.tenant_id,
                Connector.category == policy.target_connector_category,
            )
        )).scalars().all()
        conn_ids = [c.id for c in connectors]

        if not conn_ids:
            return {"status": "not_assessed",
                    "result": f"No {policy.target_connector_category} connectors configured"}

        findings = (await db.execute(
            select(GovernanceEvent).where(
                GovernanceEvent.tenant_id == policy.tenant_id,
                GovernanceEvent.connector_id.in_(conn_ids),
                GovernanceEvent.status == "open",
            )
        )).scalars().all()

        # Filter by category if the policy specifies one
        if policy.category:
            findings = [f for f in findings if f.category == policy.category]

        if findings:
            return {"status": "failing",
                    "result": f"{len(findings)} open finding(s) in {policy.target_connector_category}: "
                              + "; ".join(f.title for f in findings[:3])}
        return {"status": "passing",
                "result": f"No open findings in {policy.target_connector_category}"}

    if policy.eval_mode == "rule":
        rule = policy.rule_logic or {}
        if not rule.get("field") or not rule.get("operator"):
            return {"status": "not_assessed", "result": "Incomplete rule definition"}

        # Evaluate rule against collected event raw_data for target connectors
        connectors = (await db.execute(
            select(Connector).where(
                Connector.tenant_id == policy.tenant_id,
                Connector.category == policy.target_connector_category,
            )
        )).scalars().all() if policy.target_connector_category else []

        conn_ids = [c.id for c in connectors]
        query = select(GovernanceEvent).where(GovernanceEvent.tenant_id == policy.tenant_id)
        if conn_ids:
            query = query.where(GovernanceEvent.connector_id.in_(conn_ids))
        events = (await db.execute(query)).scalars().all()

        op_fn = OPERATORS.get(rule["operator"])
        if not op_fn:
            return {"status": "not_assessed", "result": f"Unknown operator: {rule['operator']}"}

        # A rule "fails" the policy if ANY event matches the fail condition
        matches = []
        for ev in events:
            data = ev.raw_data or {}
            # Also check top-level event fields
            field_val = data.get(rule["field"])
            if field_val is None:
                field_val = getattr(ev, rule["field"], None)
            try:
                if op_fn(field_val, rule.get("value")):
                    matches.append(ev.title)
            except Exception:
                continue

        if matches:
            return {"status": "failing",
                    "result": f"Rule matched {len(matches)} item(s): " + "; ".join(matches[:3])}
        return {"status": "passing", "result": f"Rule satisfied — no violations ({describe_rule(rule)})"}

    return {"status": "not_assessed", "result": "Unknown evaluation mode"}


async def evaluate_all_policies(db: AsyncSession, tenant_id: int) -> list:
    """Evaluate all enabled policies for a tenant and persist results."""
    policies = (await db.execute(
        select(CustomPolicy).where(CustomPolicy.tenant_id == tenant_id)
    )).scalars().all()

    results = []
    for p in policies:
        outcome = await evaluate_policy(db, p)
        if p.eval_mode != "manual":  # don't overwrite manual attestations
            p.status = outcome["status"]
        p.last_result = outcome["result"]
        p.last_evaluated = datetime.utcnow()
        results.append({"id": p.id, "title": p.title, **outcome})

    await db.commit()
    return results
