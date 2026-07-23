from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import csv, io

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.custom_policy import CustomPolicy
from app.models.audit_log import AuditLog
from app.services.policy_engine import evaluate_all_policies, evaluate_policy, describe_rule

router = APIRouter()


class PolicyCreate(BaseModel):
    policy_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    category: str = "config"
    severity: str = "medium"
    framework: Optional[str] = "custom"
    mapped_control: Optional[str] = None
    eval_mode: str = "manual"   # manual | connector | rule
    target_connector_category: Optional[str] = None
    rule_logic: Optional[dict] = None


class PolicyUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None         # for manual attestation
    last_result: Optional[str] = None
    enabled: Optional[bool] = None
    rule_logic: Optional[dict] = None
    target_connector_category: Optional[str] = None


@router.get("")
async def list_policies(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(CustomPolicy).where(CustomPolicy.tenant_id == user.tenant_id)
        .order_by(CustomPolicy.created_at.desc())
    )).scalars().all()
    return [_ser(p) for p in rows]


@router.post("")
async def create_policy(data: PolicyCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    p = CustomPolicy(**data.model_dump(), tenant_id=user.tenant_id, created_by=user.id)
    db.add(p)
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                    action="policy_created", entity_type="policy",
                    details={"title": data.title, "eval_mode": data.eval_mode}))
    await db.commit(); await db.refresh(p)
    # Evaluate immediately if automated
    if p.eval_mode != "manual":
        outcome = await evaluate_policy(db, p)
        p.status = outcome["status"]; p.last_result = outcome["result"]; p.last_evaluated = datetime.utcnow()
        await db.commit(); await db.refresh(p)
    return _ser(p)


@router.get("/template", response_class=PlainTextResponse)
async def csv_template(user: User = Depends(get_current_user)):
    """Download a CSV template for bulk policy upload."""
    headers = ["policy_id", "title", "description", "category", "severity",
               "framework", "mapped_control"]
    sample = ["ACME-SEC-001", "All servers must enforce disk encryption",
              "Full-disk encryption required on all servers", "config", "high",
              "custom", "CC6.7"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerow(sample)
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=policy_template.csv"})


@router.post("/bulk-upload")
async def bulk_upload(file: UploadFile = File(...),
                      user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    """Bulk-create policies from a CSV file. Columns: policy_id, title,
    description, category, severity, framework, mapped_control.
    Only 'title' is required per row. Adding 1000s at once instead of one by one."""
    if user.role not in ("admin", "engineer"):
        raise HTTPException(status_code=403, detail="Not permitted")
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")
    try:
        text = raw.decode("utf-8-sig")  # handles Excel BOM
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 text")

    reader = csv.DictReader(io.StringIO(text))
    created, errors = 0, []
    for i, row in enumerate(reader, start=2):  # row 1 = header
        title = (row.get("title") or "").strip()
        if not title:
            errors.append(f"row {i}: missing title")
            continue
        sev = (row.get("severity") or "medium").strip().lower()
        if sev not in ("critical", "high", "medium", "low"):
            sev = "medium"
        db.add(CustomPolicy(
            tenant_id=user.tenant_id,
            policy_id=(row.get("policy_id") or "").strip() or None,
            title=title,
            description=(row.get("description") or "").strip() or None,
            category=(row.get("category") or "config").strip() or "config",
            severity=sev,
            framework=(row.get("framework") or "custom").strip() or "custom",
            mapped_control=(row.get("mapped_control") or "").strip() or None,
            eval_mode="manual",     # bulk-uploaded policies start as manual attestation
            status="not_assessed",
            enabled=True,
            created_by=user.id,
        ))
        created += 1

    if created:
        db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                        action="policies_bulk_uploaded", entity_type="policy", entity_id=0,
                        details={"count": created}))
        await db.commit()

    return {"created": created, "errors": errors[:50], "error_count": len(errors)}



async def update_policy(policy_id: int, data: PolicyUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    p = (await db.execute(
        select(CustomPolicy).where(CustomPolicy.id == policy_id, CustomPolicy.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found")

    for k, v in data.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    if data.status:  # manual attestation
        p.last_evaluated = datetime.utcnow()
        db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                        action="policy_attested", entity_type="policy", entity_id=policy_id,
                        details={"status": data.status, "notes": data.last_result}))
    await db.commit(); await db.refresh(p)
    return _ser(p)


@router.delete("/{policy_id}")
async def delete_policy(policy_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    p = (await db.execute(
        select(CustomPolicy).where(CustomPolicy.id == policy_id, CustomPolicy.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found")
    await db.delete(p); await db.commit()
    return {"message": "Policy deleted"}


@router.post("/evaluate")
async def evaluate(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Re-run all automated policy evaluations."""
    results = await evaluate_all_policies(db, user.tenant_id)
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, user_name=user.name,
                    action="policies_evaluated", entity_type="policy",
                    details={"count": len(results)}))
    await db.commit()
    return {"evaluated": len(results), "results": results}


def _ser(p: CustomPolicy):
    return {
        "id": p.id, "policy_id": p.policy_id, "title": p.title, "description": p.description,
        "category": p.category, "severity": p.severity, "framework": p.framework,
        "mapped_control": p.mapped_control, "eval_mode": p.eval_mode,
        "target_connector_category": p.target_connector_category,
        "rule_logic": p.rule_logic, "rule_description": describe_rule(p.rule_logic) if p.rule_logic else None,
        "status": p.status, "last_result": p.last_result, "enabled": p.enabled,
        "last_evaluated": p.last_evaluated.isoformat() if p.last_evaluated else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
