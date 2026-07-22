from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, ForeignKey
from datetime import datetime
from app.core.database import Base

class AuditLog(Base):
    """Immutable log of every action — shown to auditors for chain of custody."""
    __tablename__ = "audit_logs"
    id          = Column(Integer, primary_key=True)
    tenant_id   = Column(Integer, ForeignKey("tenants.id"))
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_name   = Column(String)
    action      = Column(String, nullable=False)
    # ticket_created|ticket_accepted|ticket_rejected|ticket_remediated
    # connector_added|scan_triggered|framework_changed|evidence_collected
    entity_type = Column(String)  # ticket|connector|device|framework
    entity_id   = Column(Integer)
    details     = Column(JSON)
    ip_address  = Column(String)
    timestamp   = Column(DateTime, default=datetime.utcnow)
