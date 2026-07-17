"""
Evidence & attestation layer.

Closes the gap between "technical config scanning" (which the Prowler connectors
cover) and "audit-ready compliance" (which also needs documents and human
attestation). A control can be satisfied by three kinds of evidence:

  1. technical  — a passing/handled finding from a connector scan
  2. document   — an uploaded policy/procedure/screenshot/report
  3. attestation— a person formally attesting "we do this", with notes

This is what an auditor actually expects: not just "the box is checked" but
"here is the proof, who provided it, and when."
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from datetime import datetime
from app.core.database import Base


class Evidence(Base):
    """A piece of evidence attached to a framework control."""
    __tablename__ = "evidence"
    id            = Column(Integer, primary_key=True)
    tenant_id     = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    framework     = Column(String, nullable=False)       # soc2 | iso27001 | ...
    control_id    = Column(String, nullable=False)        # e.g. CC6.1, A.8.3
    evidence_type = Column(String, nullable=False)        # document | attestation | technical
    title         = Column(String, nullable=False)
    description   = Column(Text)

    # For document evidence: stored file reference
    file_name     = Column(String)
    file_path     = Column(String)        # path on disk / object store key
    file_size     = Column(Integer)
    content_type  = Column(String)

    # For attestation evidence: who attested and what they said
    attested_by   = Column(String)
    attestation_note = Column(Text)

    # Lifecycle
    status        = Column(String, default="active")      # active | superseded | expired
    valid_until   = Column(DateTime)                       # evidence can expire (e.g. annual review)
    created_by    = Column(String)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ControlStatus(Base):
    """The roll-up status of a single control for a tenant+framework.

    A control's status is derived from the evidence attached to it, but we persist
    an explicit status so reviewers can mark a control satisfied/gap and so the
    audit report has a stable source of truth.
    """
    __tablename__ = "control_status"
    id            = Column(Integer, primary_key=True)
    tenant_id     = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    framework     = Column(String, nullable=False)
    control_id    = Column(String, nullable=False)
    status        = Column(String, default="not_started")  # not_started | in_progress | satisfied | gap | not_applicable
    owner         = Column(String)
    notes         = Column(Text)
    # How this control is being satisfied (any combination)
    satisfied_by  = Column(JSON, default=list)             # ["technical","document","attestation"]
    last_reviewed = Column(DateTime)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
