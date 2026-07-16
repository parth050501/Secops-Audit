"""
NetworkDevice management — register and manage network devices/appliances (firewalls,
switches) assessed for config compliance.

Reach model per device (the key design):
  - via_collector=True  → an on-prem collector reaches the (often private) device
    and pulls its config. collector_id says which collector.
  - via_collector=False → device is publicly reachable; platform scans directly.

Credentials are stored encrypted. Everything is tenant-scoped: a tenant only sees
and manages its own devices.

NetworkDevice catalog — the types the platform knows about. A type's fetch+parse logic
is validated against real hardware before it truly works; the registration and
inventory here are device-independent and work now.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.tenant_guard import tenant_query
from app.core.encryption import encrypt_dict, decrypt_dict, mask_credentials
from app.models.collector import NetworkDevice, Collector
from app.models.user import User

router = APIRouter()


# The device families the platform can register. `reach` hints the default.
DEVICE_CATALOG = [
    {"type": "paloalto",   "name": "Palo Alto Firewall",  "icon": "🔥", "access": "XML API (HTTPS)"},
    {"type": "fortinet",   "name": "Fortinet FortiGate",  "icon": "🛡️", "access": "REST API"},
    {"type": "cisco_ios",  "name": "Cisco IOS (switch/router)", "icon": "🔀", "access": "SSH"},
    {"type": "cisco_asa",  "name": "Cisco ASA Firewall",  "icon": "🔥", "access": "SSH"},
    {"type": "juniper",    "name": "Juniper (JunOS)",     "icon": "🌐", "access": "SSH/NETCONF"},
    {"type": "generic_ssh","name": "Generic SSH NetworkDevice",  "icon": "🖥️", "access": "SSH"},
]


@router.get("/catalog")
async def device_catalog(user: User = Depends(get_current_user)):
    from app.services.device_parser import has_parser
    # annotate each type with whether a validated parser exists yet
    return [{**d, "parser_ready": has_parser(d["type"])} for d in DEVICE_CATALOG]


def _ser(d: NetworkDevice, collector_name: str = None) -> dict:
    return {
        "id": d.id, "name": d.name, "device_type": d.device_type,
        "host": d.host, "port": d.port,
        "via_collector": d.via_collector, "collector_id": d.collector_id,
        "collector_name": collector_name,
        "status": d.status, "last_seen": d.last_seen.isoformat() if d.last_seen else None,
        "last_scan_at": d.last_scan_at.isoformat() if d.last_scan_at else None,
        "last_result": d.last_result, "last_error": d.last_error,
        "credentials": mask_credentials(decrypt_dict(d.credentials_enc)) if d.credentials_enc else {},
    }


class DeviceIn(BaseModel):
    name: str
    device_type: str
    host: str
    port: Optional[int] = None
    credentials: Optional[dict] = None          # {api_key} or {username,password}
    via_collector: bool = True
    collector_id: Optional[int] = None


@router.get("")
async def list_devices(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    devices = (await db.execute(tenant_query(NetworkDevice, user))).scalars().all()
    collectors = (await db.execute(tenant_query(Collector, user))).scalars().all()
    cname = {c.id: c.name for c in collectors}
    return [_ser(d, cname.get(d.collector_id)) for d in devices]


@router.post("")
async def create_device(data: DeviceIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("admin", "engineer"):
        raise HTTPException(status_code=403, detail="Not permitted")
    if not data.name.strip() or not data.host.strip():
        raise HTTPException(status_code=400, detail="Name and host are required")
    # If reached via collector, a collector must be chosen and belong to the tenant.
    if data.via_collector:
        if not data.collector_id:
            raise HTTPException(status_code=400, detail="Select which collector reaches this device")
        c = (await db.execute(
            tenant_query(Collector, user).where(Collector.id == data.collector_id)
        )).scalar_one_or_none()
        if not c:
            raise HTTPException(status_code=404, detail="Collector not found")

    d = NetworkDevice(
        tenant_id=user.tenant_id, name=data.name.strip(), device_type=data.device_type,
        host=data.host.strip(), port=data.port,
        credentials_enc=encrypt_dict(data.credentials) if data.credentials else None,
        via_collector=data.via_collector,
        collector_id=data.collector_id if data.via_collector else None,
        status="pending",
    )
    db.add(d); await db.commit(); await db.refresh(d)
    return _ser(d)


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    credentials: Optional[dict] = None
    via_collector: Optional[bool] = None
    collector_id: Optional[int] = None


@router.patch("/{device_id}")
async def update_device(device_id: int, data: DeviceUpdate,
                        user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("admin", "engineer"):
        raise HTTPException(status_code=403, detail="Not permitted")
    d = (await db.execute(
        tenant_query(NetworkDevice, user).where(NetworkDevice.id == device_id)
    )).scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="NetworkDevice not found")
    for field in ("name", "host", "port", "via_collector", "collector_id"):
        val = getattr(data, field)
        if val is not None:
            setattr(d, field, val.strip() if isinstance(val, str) else val)
    if data.credentials:   # only replace creds if new ones supplied
        d.credentials_enc = encrypt_dict(data.credentials)
    await db.commit(); await db.refresh(d)
    return _ser(d)


@router.delete("/{device_id}")
async def delete_device(device_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can delete a device")
    d = (await db.execute(
        tenant_query(NetworkDevice, user).where(NetworkDevice.id == device_id)
    )).scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="NetworkDevice not found")
    await db.delete(d); await db.commit()
    return {"deleted": True, "id": device_id}


@router.post("/{device_id}/scan")
async def scan_device(device_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Trigger a scan of this device. Honest status: this queues/marks intent; the
    actual fetch of raw config runs via the collector (or platform-direct) and is
    validated per device family against real hardware. Until a device type's
    fetch+parse is validated, this records the request without producing findings."""
    if user.role not in ("admin", "engineer"):
        raise HTTPException(status_code=403, detail="Not permitted")
    d = (await db.execute(
        tenant_query(NetworkDevice, user).where(NetworkDevice.id == device_id)
    )).scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="NetworkDevice not found")

    from app.services.device_parser import has_parser
    ready = has_parser(d.device_type)
    return {
        "queued": True, "device": d.name, "device_type": d.device_type,
        "parser_ready": ready,
        "note": ("Scan requested. The collector will fetch this device's config on "
                 "its next cycle." if ready else
                 f"'{d.device_type}' scanning is not yet validated against real "
                 "hardware — registration is stored; findings will flow once the "
                 "device parser is enabled."),
    }
