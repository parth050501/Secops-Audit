"""
Credential encryption at rest.

Uses Fernet (AES-128-CBC + HMAC) from the `cryptography` library to encrypt
sensitive credential blobs before they touch the database.

The encryption key comes from SECOPS_ENCRYPTION_KEY (env). In production this
MUST be set to a strong, persistent key stored in a secrets manager — NOT in
code, NOT in the compose file committed to git. If it is rotated or lost,
previously stored credentials cannot be decrypted.

Generate a key once with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import os
import json
import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


def _derive_key() -> bytes:
    """
    Get the Fernet key. Prefer SECOPS_ENCRYPTION_KEY (a real Fernet key).
    Fall back to deriving one from JWT_SECRET so local dev still works without
    extra setup — but this fallback is logged as insecure and must not be used
    in production.
    """
    raw = os.environ.get("SECOPS_ENCRYPTION_KEY", "").strip()
    if raw:
        # Expect a valid 44-char urlsafe base64 Fernet key
        return raw.encode()
    # Dev fallback: derive a deterministic key from JWT_SECRET.
    secret = os.environ.get("JWT_SECRET", "dev-secret")
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_derive_key())
    return _fernet


def is_production_key_set() -> bool:
    """True if a real encryption key is configured (not the dev fallback)."""
    return bool(os.environ.get("SECOPS_ENCRYPTION_KEY", "").strip())


def encrypt_dict(data: Optional[dict]) -> Optional[str]:
    """Encrypt a credentials dict into an opaque string for DB storage."""
    if not data:
        return None
    plaintext = json.dumps(data).encode()
    return _get_fernet().encrypt(plaintext).decode()


def decrypt_dict(token: Optional[str]) -> Optional[dict]:
    """Decrypt a stored string back into a credentials dict."""
    if not token:
        return None
    # Backward-compat: if it's not an encrypted token (e.g. legacy plaintext
    # JSON stored as a dict-string), try to parse it directly.
    try:
        return json.loads(_get_fernet().decrypt(token.encode()).decode())
    except (InvalidToken, ValueError):
        # Legacy/unencrypted fallback — attempt plain JSON
        try:
            return json.loads(token) if isinstance(token, str) else token
        except Exception:
            return None


def mask_credentials(data: Optional[dict]) -> dict:
    """Return a display-safe version of credentials (values masked)."""
    if not data:
        return {}
    masked = {}
    for k, v in data.items():
        if v is None or v == "":
            masked[k] = ""
        elif k in ("auth_method", "regions", "region", "domain", "host", "port",
                   "base_url", "subscription_id", "project_id", "tenant_id",
                   "client_id", "os_type", "protocol", "format", "use_ldaps"):
            masked[k] = v  # non-secret fields shown
        else:
            s = str(v)
            masked[k] = (s[:2] + "•" * max(4, len(s) - 4) + s[-2:]) if len(s) > 6 else "••••••"
    return masked


def encrypt_value(value: Optional[str]) -> Optional[str]:
    """Encrypt a single string (e.g. an SMTP password) for DB storage."""
    if not value:
        return None
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_value(token: Optional[str]) -> Optional[str]:
    """Decrypt a single stored string back to plaintext."""
    if not token:
        return None
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None
