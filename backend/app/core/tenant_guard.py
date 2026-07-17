"""
Tenant isolation guards.

Multi-tenancy safety in this codebase rests on every data query being scoped to
the caller's tenant. Doing that by hand on every query is error-prone — one
forgotten filter is a cross-tenant data leak. These helpers make the scoping
explicit and hard to get wrong, and give us a single place to reason about
isolation.

Usage:
    from app.core.tenant_guard import tenant_query, get_owned_or_404

    # Scoped list query — tenant filter is applied for you:
    events = (await db.execute(tenant_query(GovernanceEvent, user))).scalars().all()

    # Scoped by-id fetch that 404s if the row isn't in the caller's tenant:
    ticket = await get_owned_or_404(db, Ticket, ticket_id, user)
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def tenant_query(model, user):
    """Return a SELECT for `model` pre-filtered to the user's tenant.

    `model` must have a `tenant_id` column. Raises if it doesn't, so we never
    silently return un-scoped data.
    """
    if not hasattr(model, "tenant_id"):
        raise RuntimeError(
            f"{model.__name__} has no tenant_id — refusing to build an unscoped "
            f"tenant query. Use a plain select() only for genuinely global tables."
        )
    return select(model).where(model.tenant_id == user.tenant_id)


async def get_owned_or_404(db: AsyncSession, model, row_id: int, user, detail: str = None):
    """Fetch one row by id, but only if it belongs to the user's tenant.

    Returns the row, or raises 404 if it doesn't exist OR belongs to another
    tenant. Crucially, a row owned by another tenant is indistinguishable from
    a non-existent one to the caller — we never reveal that it exists.
    """
    if not hasattr(model, "tenant_id"):
        raise RuntimeError(f"{model.__name__} has no tenant_id column")
    row = (await db.execute(
        select(model).where(model.id == row_id, model.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=detail or f"{model.__name__} not found")
    return row


def assert_same_tenant(obj, user):
    """Defensive check: confirm an already-loaded object belongs to the user's tenant.
    Use when an object arrives from somewhere and you want a belt-and-braces check
    before acting on it."""
    obj_tenant = getattr(obj, "tenant_id", None)
    if obj_tenant is None or obj_tenant != user.tenant_id:
        raise HTTPException(status_code=404, detail="Not found")
    return obj


# ── Tenant role-based action guards ──
# Capability matrix for tenant-layer roles. The auditor is strictly read-only;
# engineers work findings/tickets; managers approve; admins do everything.
TENANT_CAPABILITIES = {
    "manage_tenant":   {"admin"},                          # tenant settings, users
    "manage_connectors": {"admin", "engineer"},            # add/remove/scan connectors
    "work_tickets":    {"admin", "manager", "engineer"},   # create/update tickets
    "approve_tickets": {"admin", "manager"},               # approve/reject
    "manage_evidence": {"admin", "manager", "engineer"},   # upload/attest evidence
    "view":            {"admin", "manager", "engineer", "auditor"},  # everyone incl auditor
}


def tenant_can(user, capability: str) -> bool:
    return user.role in TENANT_CAPABILITIES.get(capability, set())


def require_tenant_capability(capability: str):
    """FastAPI dependency: allow only tenant roles that hold `capability`.
    Enforces, e.g., that an auditor (read-only) cannot mutate data server-side,
    regardless of what the UI shows."""
    from fastapi import Depends, HTTPException
    from app.core.security import get_current_user

    allowed = TENANT_CAPABILITIES.get(capability, set())

    async def _checker(user=Depends(get_current_user)):
        if user.role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Your role ({user.role}) cannot perform this action",
            )
        return user

    return _checker
