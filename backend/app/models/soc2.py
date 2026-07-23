from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Boolean
from datetime import datetime
from app.core.database import Base


class SOC2Readiness(Base):
    """
    SOC 2 readiness tracking — Type I (point in time) vs Type II (period of time).
    Tracks per-criterion readiness status and evidence collection period.
    """
    __tablename__ = "soc2_readiness"
    id              = Column(Integer, primary_key=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"))
    report_type     = Column(String, default="type2")     # type1 | type2
    audit_period_start = Column(DateTime)                  # for Type II observation window
    audit_period_end   = Column(DateTime)
    target_date     = Column(DateTime)                     # planned audit date
    trust_categories= Column(JSON, default=list)           # ["security","availability","confidentiality",...]
    overall_readiness = Column(Integer, default=0)         # 0-100
    status          = Column(String, default="preparing")  # preparing | ready | in_audit | certified
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SOC2CriterionStatus(Base):
    """Per-criterion readiness state within a SOC 2 engagement."""
    __tablename__ = "soc2_criterion_status"
    id            = Column(Integer, primary_key=True)
    tenant_id     = Column(Integer, ForeignKey("tenants.id"))
    criterion_id  = Column(String)        # e.g. CC6.1
    category      = Column(String)        # security | availability | ...
    readiness     = Column(String, default="not_started")  # not_started | in_progress | ready | gap
    owner         = Column(String)
    evidence_notes= Column(Text)
    last_updated  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
