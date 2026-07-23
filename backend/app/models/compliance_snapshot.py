"""
Historical compliance posture snapshots.

Each row is a point-in-time record of one framework's readiness for one tenant.
Capturing these over time lets us show trends ("posture over the last 6 months"),
answer "what was our posture on date X" (audit-period evidence), and detect when a
control started failing.

Snapshots are captured on demand ("snapshot now") and can be triggered on a
schedule so history accumulates automatically. Each snapshot also stores which
framework VERSION was in effect, tying the two versioning concepts together.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey, Index
from app.core.database import Base


class ComplianceSnapshot(Base):
    __tablename__ = "compliance_snapshots"
    id            = Column(Integer, primary_key=True)
    tenant_id     = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    framework_key = Column(String, nullable=False)
    framework_name = Column(String)
    framework_version = Column(String)          # which standard version was in effect

    readiness_pct = Column(Float, nullable=False)
    total_controls = Column(Integer, default=0)
    passing       = Column(Integer, default=0)
    failing       = Column(Integer, default=0)

    # optional per-family breakdown at snapshot time (for richer history)
    family_breakdown = Column(JSON)             # [{category,label,readiness_pct,passing,total}]

    captured_at   = Column(DateTime, default=datetime.utcnow, index=True)
    captured_by   = Column(String)              # "manual", "scheduled", user name

    __table_args__ = (
        Index("ix_snapshot_tenant_fw_time", "tenant_id", "framework_key", "captured_at"),
    )
