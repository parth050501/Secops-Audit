"""
Collector authentication.

A collector authenticates with a bearer token issued at registration. The token
is shown ONCE at registration and only its bcrypt hash is stored. On every
collector request we resolve the token → the owning Collector → its tenant_id,
and that derived tenant_id is what all downstream operations use. The collector
never supplies a tenant id itself.
"""
import secrets
from datetime import datetime
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.models.collector import Collector

collector_bearer = HTTPBearer()


def generate_collector_token() -> str:
    """A long random token. Format: 'cce_<random>'. Shown once; only hash stored."""
    return "cce_" + secrets.token_urlsafe(36)


def hash_token(token: str) -> str:
    return hash_password(token)


async def authenticate_collector(
    creds: HTTPAuthorizationCredentials = Depends(collector_bearer),
    db: AsyncSession = Depends(get_db),
) -> Collector:
    """Resolve the bearer token to its Collector. The token determines the
    tenant — the collector cannot assert one. Updates last_seen as a side effect
    so any authenticated call doubles as a liveness signal."""
    token = creds.credentials or ""
    if not token.startswith("cce_"):
        raise HTTPException(status_code=401, detail="Invalid collector token")

    # We can't look up by hash directly (bcrypt salts differ), so match by prefix
    # then verify. Prefix is the first 12 chars of the token, stored at register.
    prefix = token[:12]
    candidates = (await db.execute(
        select(Collector).where(Collector.token_prefix == prefix)
    )).scalars().all()

    matched = None
    for c in candidates:
        if verify_password(token, c.token_hash):
            matched = c
            break
    if not matched:
        raise HTTPException(status_code=401, detail="Invalid collector token")

    # Liveness: any authenticated request updates last_seen + marks connected
    matched.last_seen = datetime.utcnow()
    matched.status = "connected"
    await db.commit()
    return matched
