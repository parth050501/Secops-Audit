"""
Framework store — seeding and access.

- seed_frameworks(db): one-time copy of the code-defined FRAMEWORKS into the DB
  (idempotent — skips any framework key already present as a built-in).
- get_frameworks(db, tenant_id): returns frameworks in the SAME dict shape the
  rest of the code already expects, so existing callers change minimally:
      { key: {name, short, description, color, controls: [{id,title,category,weight}]} }
  It includes global built-ins plus the tenant's own custom frameworks.
- get_framework(db, key, tenant_id): one framework in the same shape.

This is the bridge that lets the platform read editable DB frameworks while the
rest of the code keeps working with the familiar structure.
"""
from sqlalchemy import select
from app.models.framework import CustomFramework, FrameworkControl
from app.frameworks.definitions import FRAMEWORKS as CODE_FRAMEWORKS


async def seed_frameworks(db):
    """Copy code-defined frameworks into the DB once, so they become editable.
    Idempotent: if a built-in with the same key already exists, skip it."""
    existing_keys = set((await db.execute(
        select(CustomFramework.key).where(CustomFramework.is_builtin == True)  # noqa: E712
    )).scalars().all())

    created = 0
    for key, fw in CODE_FRAMEWORKS.items():
        if key in existing_keys:
            continue
        row = CustomFramework(
            key=key, tenant_id=None, name=fw.get("name", key),
            short=fw.get("short", key), description=fw.get("description", ""),
            color=fw.get("color", "#0F8B8D"), is_builtin=True,
        )
        db.add(row); await db.flush()
        for c in fw.get("controls", []):
            db.add(FrameworkControl(
                framework_id=row.id, control_id=c["id"], title=c["title"],
                category=c.get("category", "general"), weight=c.get("weight", "medium"),
            ))
        created += 1
    if created:
        await db.commit()
    return created


def _shape(fw_row, controls):
    return {
        "name": fw_row.name, "short": fw_row.short or fw_row.name,
        "description": fw_row.description, "color": fw_row.color,
        "is_builtin": fw_row.is_builtin, "db_id": fw_row.id,
        "tenant_id": fw_row.tenant_id,
        "controls": [
            {"id": c.control_id, "title": c.title, "category": c.category,
             "weight": c.weight, "guidance": c.guidance}
            for c in controls
        ],
    }


async def get_frameworks(db, tenant_id=None) -> dict:
    """All global built-ins + this tenant's custom frameworks, in code-dict shape."""
    q = select(CustomFramework).where(
        (CustomFramework.tenant_id.is_(None)) | (CustomFramework.tenant_id == tenant_id)
    )
    fws = (await db.execute(q)).scalars().all()
    # controls for all these frameworks
    ids = [f.id for f in fws]
    controls_by_fw = {}
    if ids:
        crows = (await db.execute(
            select(FrameworkControl).where(FrameworkControl.framework_id.in_(ids))
        )).scalars().all()
        for c in crows:
            controls_by_fw.setdefault(c.framework_id, []).append(c)
    out = {}
    for f in fws:
        out[f.key] = _shape(f, controls_by_fw.get(f.id, []))
    return out


async def get_framework(db, key, tenant_id=None):
    """One framework by key (built-in or tenant-owned), in code-dict shape, or None."""
    q = select(CustomFramework).where(
        CustomFramework.key == key,
        (CustomFramework.tenant_id.is_(None)) | (CustomFramework.tenant_id == tenant_id),
    )
    f = (await db.execute(q)).scalars().first()
    if not f:
        return None
    controls = (await db.execute(
        select(FrameworkControl).where(FrameworkControl.framework_id == f.id)
    )).scalars().all()
    return _shape(f, controls)
