# Security Foundation — Setup Notes

This build adds the security floor required before hosting with real partner data.

## What changed
1. **Credential encryption at rest** (app/core/encryption.py)
   - Connector credentials (AWS keys, etc.) are encrypted with Fernet before
     storage. The DB never holds plaintext secrets.
   - The API never returns raw credentials — only a masked view (e.g. AK••••••23).

2. **Real bcrypt passwords** (app/core/security.py)
   - New passwords are bcrypt-hashed (cost 12). The plain: fallback only applies
     in ENVIRONMENT=qc if bcrypt is somehow unavailable.

## REQUIRED before hosting on EC2

### 1. Set a real encryption key (critical)
Generate once and store it safely (NOT in git):
```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Set it as an environment variable on the server:
```
SECOPS_ENCRYPTION_KEY=<the generated key>
```
**If this key is lost, stored credentials cannot be decrypted. If it changes,
existing credentials become unreadable.** Treat it like a master password.
In dev, if unset, a key is derived from JWT_SECRET (insecure — dev only).

### 2. Set a strong JWT secret
```
JWT_SECRET=<long random string>
```

### 3. Set environment to production
```
ENVIRONMENT=production
```
This enforces bcrypt (no plain: fallback) and removes the QC banner.

## Still pending (next build steps, in order)
- PostgreSQL migration (replace SQLite for durable multi-tenant storage)
- Multi-tenancy isolation hardening + tests
- Compliance gap-closure layer (evidence/attestation/documents/audit-ready report)
- Deployment config (reverse proxy, HTTPS) + EC2 provisioning guidance
