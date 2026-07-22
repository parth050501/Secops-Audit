from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

bearer = HTTPBearer()

# Use bcrypt by default. In QC/demo (ENVIRONMENT=qc) we still allow the
# plain: fallback so the existing demo seed works without re-hashing, but
# any NEW password is always bcrypt-hashed.

def _bcrypt_available() -> bool:
    try:
        import bcrypt  # noqa
        return True
    except Exception:
        return False


def hash_password(password: str) -> str:
    """Always hash with bcrypt when available. Falls back to plain: only if bcrypt
    is genuinely unavailable AND we're in qc (so local demos never break)."""
    if _bcrypt_available():
        import bcrypt
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt).decode()
    if settings.environment == "qc":
        return f"plain:{password}"
    raise RuntimeError("bcrypt is required in production but is not installed")


def verify_password(plain: str, stored: str) -> bool:
    if not stored:
        return False
    if stored.startswith("plain:"):
        return plain == stored[6:]
    if stored.startswith("$2"):  # bcrypt hash
        try:
            import bcrypt
            return bcrypt.checkpw(plain.encode(), stored.encode())
        except Exception:
            return False
    return False


def create_token(user_id: int, email: str, role: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "email": email, "role": role, "exp": exp},
        settings.jwt_secret, algorithm=settings.jwt_algorithm,
    )


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
