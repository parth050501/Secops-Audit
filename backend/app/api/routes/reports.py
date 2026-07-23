"""
Reporting endpoints — audience-level compliance reports (CISO / engineer / auditor).

Reports render from live compliance data. View as JSON (for the dashboard) or
download as PDF. Emailed/scheduled delivery is a later build (email now works).
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.reports_service import build_report, BUILDERS

router = APIRouter()

LEVELS = [
    {"key": "ciso",     "label": "Executive / CISO",     "desc": "High-level posture, scores, and trends for leadership."},
    {"key": "engineer", "label": "Engineering",          "desc": "Failing controls, findings, and remediation detail."},
    {"key": "auditor",  "label": "Auditor / Evidence",   "desc": "Control-by-control status and evidence sources."},
]


@router.get("/levels")
async def report_levels(user: User = Depends(get_current_user)):
    return LEVELS


@router.get("/{level}")
async def get_report(level: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if level not in BUILDERS:
        raise HTTPException(status_code=404, detail="Unknown report level")
    return await build_report(db, user.tenant_id, level)


@router.get("/{level}/pdf")
async def get_report_pdf(level: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if level not in BUILDERS:
        raise HTTPException(status_code=404, detail="Unknown report level")
    report = await build_report(db, user.tenant_id, level)
    from app.services.report_generator import generate_leveled_pdf
    pdf = generate_leveled_pdf(report)
    tenant_name = report.get("tenant", {}).get("name", "report").replace(" ", "_")
    fname = f"{tenant_name}_{level}_report.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={fname}"})


# ── Scheduling + history ──
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from fastapi.responses import Response as _Resp
from sqlalchemy import select, desc
from app.models.report_schedule import ReportSchedule, GeneratedReport


def _ser_sched(s: ReportSchedule) -> dict:
    return {
        "cadence": s.cadence, "send_ciso": s.send_ciso,
        "send_engineer": s.send_engineer, "send_auditor": s.send_auditor,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
    }


async def _get_or_create_sched(db, tenant_id):
    s = (await db.execute(select(ReportSchedule).where(ReportSchedule.tenant_id == tenant_id))).scalar_one_or_none()
    if not s:
        s = ReportSchedule(tenant_id=tenant_id, cadence="off")
        db.add(s); await db.commit(); await db.refresh(s)
    return s


class ScheduleIn(BaseModel):
    cadence: Optional[str] = None            # off|weekly|monthly|quarterly
    send_ciso: Optional[bool] = None
    send_engineer: Optional[bool] = None
    send_auditor: Optional[bool] = None


@router.get("/schedule/config")
async def get_schedule(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    s = await _get_or_create_sched(db, user.tenant_id)
    return _ser_sched(s)


@router.patch("/schedule/config")
async def set_schedule(data: ScheduleIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only a tenant admin can configure report scheduling")
    from app.services.report_delivery import compute_next_run
    s = await _get_or_create_sched(db, user.tenant_id)
    if data.cadence is not None:
        if data.cadence not in ("off", "weekly", "monthly", "quarterly"):
            raise HTTPException(status_code=400, detail="Invalid cadence")
        s.cadence = data.cadence
        s.next_run_at = compute_next_run(data.cadence) if data.cadence != "off" else None
    for f in ("send_ciso", "send_engineer", "send_auditor"):
        v = getattr(data, f)
        if v is not None:
            setattr(s, f, v)
    await db.commit(); await db.refresh(s)
    return _ser_sched(s)


@router.post("/schedule/send-now")
async def send_now(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Generate + email the configured report levels immediately (respects
    notification preferences for recipients). Also stores them in history."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only a tenant admin can trigger delivery")
    from app.services.report_delivery import deliver_for_tenant
    s = await _get_or_create_sched(db, user.tenant_id)
    if s.cadence == "off" and not (s.send_ciso or s.send_engineer or s.send_auditor):
        raise HTTPException(status_code=400, detail="Enable at least one report level first")
    result = await deliver_for_tenant(db, s, trigger=user.name or "manual")
    return result


@router.get("/history/list")
async def report_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(GeneratedReport).where(GeneratedReport.tenant_id == user.tenant_id)
        .order_by(desc(GeneratedReport.created_at)).limit(100)
    )).scalars().all()
    return [{
        "id": r.id, "level": r.level, "title": r.title, "period_label": r.period_label,
        "overall_readiness": r.overall_readiness, "generated_by": r.generated_by,
        "emailed_to": r.emailed_to, "created_at": r.created_at.isoformat(),
    } for r in rows]


@router.post("/history/save/{level}")
async def save_report(level: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Manually save a snapshot of a report into history (point-in-time evidence)."""
    if level not in BUILDERS:
        raise HTTPException(status_code=404, detail="Unknown report level")
    from app.services.reports_service import build_and_store_report
    row = await build_and_store_report(db, user.tenant_id, level, generated_by=user.name or "manual")
    return {"id": row.id, "title": row.title}


@router.get("/history/{report_id}/pdf")
async def download_stored(report_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = (await db.execute(
        select(GeneratedReport).where(GeneratedReport.id == report_id,
                                      GeneratedReport.tenant_id == user.tenant_id)
    )).scalar_one_or_none()
    if not r or not r.pdf_bytes:
        raise HTTPException(status_code=404, detail="Report not found")
    fname = (r.title or "report").replace(" ", "_").replace("—", "-") + ".pdf"
    return _Resp(content=r.pdf_bytes, media_type="application/pdf",
                 headers={"Content-Disposition": f"attachment; filename={fname}"})
