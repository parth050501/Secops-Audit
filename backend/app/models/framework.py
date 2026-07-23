"""
Database-backed frameworks and controls.

Frameworks and their controls originally lived in code (definitions.py). To let
tenants VIEW, ADD, EDIT, and BULK-UPLOAD controls — and create their own custom
frameworks — the data now lives here, in the database, where it can be edited.

On first startup the code-defined frameworks are seeded into these tables (see
seed_frameworks.py) so nothing is lost; from then on they're editable.

Scope model:
- A framework with tenant_id = NULL is a GLOBAL/built-in framework (e.g. the
  seeded SOC 2, PCI DSS). Visible to everyone.
- A framework with tenant_id set is a CUSTOM framework owned by that tenant.
This lets us ship built-ins while letting each tenant add their own — and (later)
lets a tenant extend even the built-ins by adding tenant-scoped controls.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from app.core.database import Base


class CustomFramework(Base):
    __tablename__ = "frameworks"
    id           = Column(Integer, primary_key=True)
    key          = Column(String, nullable=False, index=True)   # e.g. "soc2", "sbi_internal"
    tenant_id    = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)  # NULL = global built-in
    name         = Column(String, nullable=False)               # "SOC 2"
    short        = Column(String)                               # "SOC 2"
    version      = Column(String)                               # e.g. "v4.0.1", "2022" — which standard version
    description  = Column(String)
    color        = Column(String, default="#0F8B8D")
    is_builtin   = Column(Boolean, default=False)               # seeded from code
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FrameworkControl(Base):
    __tablename__ = "framework_controls"
    id           = Column(Integer, primary_key=True)
    framework_id = Column(Integer, ForeignKey("frameworks.id"), nullable=False, index=True)
    control_id   = Column(String, nullable=False)               # "CC6.1"
    title        = Column(String, nullable=False)
    category     = Column(String, default="general")
    weight       = Column(String, default="medium")             # critical|high|medium|low
    guidance     = Column(Text)                                 # optional extra guidance
    created_at   = Column(DateTime, default=datetime.utcnow)
