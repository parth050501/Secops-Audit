"""
Production seed — creates ONLY the platform super-admin, no demo data.

Use this on a real hosted environment instead of seed.py. It reads the
super-admin credentials from environment variables so no password is ever
hardcoded, and it creates nothing else (no demo tenants, no demo users).

Required env vars:
  SUPERADMIN_EMAIL     e.g. you@codecoresystems.in
  SUPERADMIN_PASSWORD  a strong password you choose
  SUPERADMIN_NAME      (optional) display name; defaults to "Platform Owner"

Run (inside the backend container):
  docker compose -f docker-compose.yml -f docker-compose.prod.yml exec \
    -e SUPERADMIN_EMAIL=you@codecoresystems.in \
    -e SUPERADMIN_PASSWORD='your-strong-password' \
    backend python prod_seed.py

Safe to run more than once — if a super-admin with that email already exists,
it does nothing.
"""
import asyncio
import os
import sys

sys.path.insert(0, ".")

from sqlalchemy import select
from app.core.database import init_db, AsyncSessionLocal
from app.core.security import hash_password
from app.models.platform import PlatformAdmin


async def prod_seed():
    email = os.environ.get("SUPERADMIN_EMAIL")
    password = os.environ.get("SUPERADMIN_PASSWORD")
    name = os.environ.get("SUPERADMIN_NAME", "Platform Owner")

    if not email or not password:
        print("ERROR: set SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD environment variables.")
        print("Example:")
        print("  docker compose -f docker-compose.yml -f docker-compose.prod.yml exec \\")
        print("    -e SUPERADMIN_EMAIL=you@codecoresystems.in \\")
        print("    -e SUPERADMIN_PASSWORD='your-strong-password' \\")
        print("    backend python prod_seed.py")
        sys.exit(1)

    if len(password) < 10:
        print("ERROR: choose a password of at least 10 characters.")
        sys.exit(1)

    await init_db()
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(
            select(PlatformAdmin).where(PlatformAdmin.email == email)
        )).scalar_one_or_none()
        if existing:
            print(f"Super-admin {email} already exists — nothing to do.")
            return
        admin = PlatformAdmin(
            email=email, name=name, role="super_admin",
            hashed_pw=hash_password(password),
        )
        db.add(admin)
        await db.commit()
        print(f"Created super-admin: {email}")
        print("Log in at  https://YOUR_DOMAIN/platform")
        print("No demo data was created. You can now onboard your first tenant.")


if __name__ == "__main__":
    asyncio.run(prod_seed())
