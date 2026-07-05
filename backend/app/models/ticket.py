from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from datetime import datetime
from app.core.database import Base

class Ticket(Base):
    __tablename__ = "tickets"
    id              = Column(Integer, primary_key=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"))
    ref             = Column(String)      # SECOPS-001, SECOPS-002, ...
    title           = Column(String, nullable=False)
    description     = Column(Text)
    severity        = Column(String, default="medium")
    category        = Column(String)
    framework       = Column(String)
    control_ids     = Column(JSON, default=list)   # ["PCI-6.3.3", "PCI-8.2.1"]
    device_id       = Column(Integer, ForeignKey("devices.id"), nullable=True)
    connector_id    = Column(Integer, ForeignKey("connectors.id"), nullable=True)
    event_id        = Column(Integer, ForeignKey("governance_events.id"), nullable=True)

    # Workflow
    status          = Column(String, default="open")
    # open|assigned|in_review|accepted|rejected|remediated|suppressed
    assigned_to     = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by      = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_date        = Column(DateTime)

    # Resolution
    resolution_notes = Column(Text)
    rejection_reason = Column(Text)
    approved_by     = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at     = Column(DateTime)

    # External systems
    jira_key        = Column(String)
    jira_url        = Column(String)
    servicenow_number = Column(String)

    # Audit trail
    history         = Column(JSON, default=list)
    # [{timestamp, user, action, notes}, ...]

    # Work-done comments (free-form progress notes by the team)
    comments        = Column(JSON, default=list)
    # [{timestamp, user, text}, ...]

    # Evidence attached to this ticket (proof the work was done)
    evidence        = Column(JSON, default=list)
    # [{timestamp, user, file_name, file_path, file_size, content_type, note}, ...]

    # AI suggestion
    ai_recommendation = Column(Text)
    remediation_steps = Column(Text)

    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
