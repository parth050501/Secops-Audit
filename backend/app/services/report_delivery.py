"""
Report delivery — generates scheduled reports, emails them to opted-in
recipients (per notification preferences), and stores them in history.

Cadence math is intentionally simple and safe: a schedule is "due" when now is
past its next_run_at. After running, next_run_at is advanced. Delivery is
fail-safe — an email failure never stops the run or corrupts the schedule.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import select
from app.models.report_schedule import ReportSchedule
from app.models.tenant import Tenant

log = logging.getLogger("report.delivery")

LEVEL_MAP = {"ciso": "report_ciso", "engineer": "report_engineer", "auditor": "report_auditor"}


def compute_next_run(cadence: str, frm: datetime = None) -> datetime:
    now = frm or datetime.utcnow()
    if cadence == "weekly":
        return now + timedelta(days=7)
    if cadence == "monthly":
        return now + timedelta(days=30)
    if cadence == "quarterly":
        return now + timedelta(days=91)
    return now + timedelta(days=3650)  # "off" — far future


async def deliver_for_tenant(db, schedule: ReportSchedule, trigger: str = "scheduled") -> dict:
    """Generate + email + store the configured report levels for one tenant."""
    from app.services.reports_service import build_and_store_report, current_period_label
    from app.services.notification_service import recipients_for
    from app.services.email_service import send_email

    levels = []
    if schedule.send_ciso: levels.append("ciso")
    if schedule.send_engineer: levels.append("engineer")
    if schedule.send_auditor: levels.append("auditor")

    period = current_period_label(schedule.cadence)
    results = []
    for level in levels:
        try:
            recips = await recipients_for(db, schedule.tenant_id, LEVEL_MAP[level])
            stored = await build_and_store_report(
                db, schedule.tenant_id, level, generated_by=trigger,
                period_label=period, emailed_to=len(recips))
            # email each recipient (fail-safe; never raises)
            sent = 0
            for u in recips:
                ok = await send_email(
                    u.email,
                    f"[GRCBridge] {stored.title}",
                    f"<p>Your {level} compliance report ({period}) is attached in GRCBridge.</p>"
                    f"<p>Overall readiness: <b>{stored.overall_readiness}%</b>. "
                    f"Log in to view or download the full report.</p>",
                )
                if ok: sent += 1
            results.append({"level": level, "recipients": len(recips), "sent": sent,
                            "report_id": stored.id})
        except Exception as e:
            log.warning("delivery failed for tenant %s level %s: %s", schedule.tenant_id, level, e)
            results.append({"level": level, "error": str(e)})

    schedule.last_run_at = datetime.utcnow()
    schedule.next_run_at = compute_next_run(schedule.cadence)
    await db.commit()
    return {"tenant_id": schedule.tenant_id, "period": period, "results": results}


async def run_due_report_schedules(session_factory) -> int:
    """Called by the scheduler loop. Runs any schedules whose next_run_at has passed.
    Returns count of tenants delivered."""
    delivered = 0
    async with session_factory() as db:
        now = datetime.utcnow()
        due = (await db.execute(
            select(ReportSchedule).where(
                ReportSchedule.cadence != "off",
                ReportSchedule.next_run_at != None,
                ReportSchedule.next_run_at <= now,
            )
        )).scalars().all()
    for sched in due:
        async with session_factory() as db:
            fresh = (await db.execute(
                select(ReportSchedule).where(ReportSchedule.id == sched.id)
            )).scalar_one_or_none()
            if fresh and fresh.cadence != "off" and fresh.next_run_at and fresh.next_run_at <= datetime.utcnow():
                try:
                    await deliver_for_tenant(db, fresh, trigger="scheduled")
                    delivered += 1
                except Exception as e:
                    log.warning("schedule run failed for tenant %s: %s", fresh.tenant_id, e)
    return delivered
