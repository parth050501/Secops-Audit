from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Boolean
from datetime import datetime
from app.core.database import Base


class CustomPolicy(Base):
    """
    Company-defined policy (the '10%') layered on top of mandated framework controls.
    Supports manual attestation OR automated rule logic against collected data.
    """
    __tablename__ = "custom_policies"
    id            = Column(Integer, primary_key=True)
    tenant_id     = Column(Integer, ForeignKey("tenants.id"))

    # Identity
    policy_id     = Column(String)        # company's own ref, e.g. "ACME-SEC-001"
    title         = Column(String, nullable=False)
    description   = Column(Text)
    category      = Column(String)        # reuses CATEGORY_LABELS
    severity      = Column(String, default="medium")  # critical|high|medium|low

    # Framework linkage — optional, maps custom policy to a framework control
    framework     = Column(String)        # which framework this supports (or "custom")
    mapped_control= Column(String)        # e.g. "CC6.1" — links to a standard control

    # Evaluation mode
    eval_mode     = Column(String, default="manual")  # manual | connector | rule
    # manual    = human attests pass/fail
    # connector = applies to a connector category, finding presence = fail
    # rule      = custom rule logic evaluated against collected data

    target_connector_category = Column(String)  # for connector/rule modes: network|server|cloud|...

    # Rule logic (for eval_mode == "rule")
    # Structured as: {"field": "...", "operator": "equals|not_equals|contains|gt|lt|exists", "value": "..."}
    # e.g. {"field":"mfa_enabled","operator":"equals","value":"false"} → fails if MFA disabled
    rule_logic    = Column(JSON)

    # Current status
    status        = Column(String, default="not_assessed")  # passing | failing | not_assessed
    last_result   = Column(Text)
    last_evaluated= Column(DateTime)

    enabled       = Column(Boolean, default=True)
    created_by    = Column(Integer, ForeignKey("users.id"))
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
