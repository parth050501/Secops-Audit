from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Text, ForeignKey
from datetime import datetime
from app.core.database import Base

class GovernanceEvent(Base):
    """A real-time or scanned governance finding from any connected system."""
    __tablename__ = "governance_events"
    id             = Column(Integer, primary_key=True)
    tenant_id      = Column(Integer, ForeignKey("tenants.id"))
    connector_id   = Column(Integer, ForeignKey("connectors.id"), nullable=True)
    device_id      = Column(Integer, ForeignKey("devices.id"), nullable=True)

    # What happened
    title          = Column(String, nullable=False)
    description    = Column(Text)
    raw_data       = Column(JSON)          # original payload from source system

    # Classification
    severity       = Column(String, default="medium")   # critical|high|medium|low|info
    category       = Column(String)   # access_control|encryption|logging|patching|config|
                                      # network_security|identity|data_protection|availability
    source_type    = Column(String)   # realtime|scheduled_scan|manual

    # Framework mapping — which controls this event touches
    framework_mappings = Column(JSON, default=dict)
    # e.g. {"pci_dss": ["6.3.3","8.2.1"], "hipaa": ["164.312(a)"], "iso27001": ["A.12.6"]}

    # AI enrichment
    ai_analysis    = Column(Text)
    ai_risk        = Column(Text)
    ai_recommendation = Column(Text)
    enriched_at    = Column(DateTime)

    # Ticket link
    ticket_id      = Column(Integer, ForeignKey("tickets.id"), nullable=True)

    status         = Column(String, default="open")  # open|ticketed|resolved|suppressed
    occurred_at    = Column(DateTime, default=datetime.utcnow)
    created_at     = Column(DateTime, default=datetime.utcnow)
