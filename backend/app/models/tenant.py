from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from datetime import datetime
from app.core.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id           = Column(Integer, primary_key=True)
    name         = Column(String, nullable=False)
    industry     = Column(String)   # financial|healthcare|retail|government|technology
    frameworks   = Column(JSON, default=list)   # ["pci_dss","hipaa","iso27001",...]
    active_framework = Column(String, default="pci_dss")  # primary display framework
    logo_url     = Column(String)
    timezone     = Column(String, default="UTC")
    scan_schedule = Column(String, default="daily")  # realtime|daily|weekly
    jira_url     = Column(String)
    jira_token   = Column(String)
    servicenow_url = Column(String)
    servicenow_token = Column(String)
    custom_domain = Column(String)   # e.g. client.codecoresystems.in (routing wired later)
    onboarded    = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)
