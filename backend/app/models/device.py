from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey
from datetime import datetime
from app.core.database import Base

class Device(Base):
    __tablename__ = "devices"
    id           = Column(Integer, primary_key=True)
    tenant_id    = Column(Integer, ForeignKey("tenants.id"))
    connector_id = Column(Integer, ForeignKey("connectors.id"))
    name         = Column(String, nullable=False)
    device_type  = Column(String)   # firewall|server|workstation|switch|router|vm|container|db|app
    os           = Column(String)   # Windows Server 2022, Ubuntu 22.04, etc.
    ip_address   = Column(String)
    hostname     = Column(String)
    environment  = Column(String)   # production|staging|dev|dmz|cardholder
    owner        = Column(String)
    tags         = Column(JSON, default=list)
    compliance_scope = Column(JSON, default=list)  # which frameworks this device is in scope for
    risk_score   = Column(Integer, default=0)      # 0-100
    last_seen    = Column(DateTime)
    metadata_    = Column("metadata", JSON, default=dict)
    created_at   = Column(DateTime, default=datetime.utcnow)
