from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from datetime import datetime
from app.core.database import Base


class AIUsage(Base):
    """Tracks every AI call for pay-as-you-go billing."""
    __tablename__ = "ai_usage"
    id           = Column(Integer, primary_key=True)
    tenant_id    = Column(Integer, ForeignKey("tenants.id"))
    user_id      = Column(Integer, ForeignKey("users.id"))
    user_name    = Column(String)
    operation    = Column(String)   # enhance_ticket | enhance_event | audit_summary | chat
    entity_type  = Column(String)   # ticket | event | report
    entity_id    = Column(Integer)
    input_tokens = Column(Integer, default=0)
    output_tokens= Column(Integer, default=0)
    cost_usd     = Column(Float, default=0.0)
    credits_used = Column(Integer, default=1)
    timestamp    = Column(DateTime, default=datetime.utcnow)


class AICreditsBalance(Base):
    """Per-tenant AI credit balance for pay-as-you-go."""
    __tablename__ = "ai_credits"
    id            = Column(Integer, primary_key=True)
    tenant_id     = Column(Integer, ForeignKey("tenants.id"), unique=True)
    credits_total = Column(Integer, default=10)    # free starter credits
    credits_used  = Column(Integer, default=0)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
