"""
Report scheduling + history.

ReportSchedule : per-tenant config for automatic report delivery — cadence
                 (off/weekly/monthly/quarterly) and which levels to send. The
                 tenant admin controls this; each level is emailed to whoever
                 opted into that level (via notification preferences).

GeneratedReport: a stored record of a report that was generated (scheduled or
                 manual "save"), so past reports can be listed, viewed, and
                 re-downloaded. The PDF bytes are stored so the exact document is
                 preserved (point-in-time evidence — important for audits).
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, LargeBinary, Float
from app.core.database import Base


class ReportSchedule(Base):
    __tablename__ = "report_schedules"
    id          = Column(Integer, primary_key=True)
    tenant_id   = Column(Integer, ForeignKey("tenants.id"), nullable=False, unique=True, index=True)

    cadence     = Column(String, default="off")     # off|weekly|monthly|quarterly
    send_ciso     = Column(Boolean, default=True)
    send_engineer = Column(Boolean, default=False)
    send_auditor  = Column(Boolean, default=False)

    last_run_at = Column(DateTime)                   # when delivery last fired
    next_run_at = Column(DateTime)                   # computed next fire time
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GeneratedReport(Base):
    __tablename__ = "generated_reports"
    id          = Column(Integer, primary_key=True)
    tenant_id   = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    level       = Column(String, nullable=False)     # ciso|engineer|auditor
    title       = Column(String)                     # e.g. "Executive Report — 2026-Q1"
    period_label = Column(String)                    # "2026-Q1", "March 2026", "as of 2026-07-22"

    overall_readiness = Column(Float)                # headline number for the list view
    pdf_bytes   = Column(LargeBinary)                # the stored PDF
    generated_by = Column(String)                    # "scheduled" | user name
    emailed_to  = Column(Integer, default=0)         # how many recipients it was sent to
    created_at  = Column(DateTime, default=datetime.utcnow, index=True)
