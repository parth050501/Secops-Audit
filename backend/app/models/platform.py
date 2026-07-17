from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, JSON
from datetime import datetime
from app.core.database import Base


class PlatformAdmin(Base):
    """Platform staff accounts — the SaaS operator's internal team, NOT tenant users.

    Roles (platform layer):
      super_admin — full control, incl. billing + team management
      admin       — everything operational (onboard/delete tenants, manage team,
                    impersonate) EXCEPT billing
      analyst     — work inside tenants (scans, findings, impersonate) but cannot
                    onboard/delete tenants, manage team, or change billing
      read_only   — view everything across tenants, change nothing
    """
    __tablename__ = "platform_admins"
    id         = Column(Integer, primary_key=True)
    email      = Column(String, unique=True, nullable=False)
    name       = Column(String, nullable=False)
    hashed_pw  = Column(String, nullable=False)
    role       = Column(String, default="super_admin")  # super_admin | admin | analyst | read_only
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)


PLATFORM_ROLES = ["super_admin", "admin", "analyst", "read_only"]


class TenantBilling(Base):
    """Per-tenant subscription & billing state."""
    __tablename__ = "tenant_billing"
    id            = Column(Integer, primary_key=True)
    tenant_id     = Column(Integer, ForeignKey("tenants.id"), unique=True)
    plan          = Column(String, default="starter")   # starter | professional | enterprise
    mrr           = Column(Float, default=499.0)         # monthly recurring revenue
    status        = Column(String, default="active")     # active | trial | suspended | churned
    trial_ends    = Column(DateTime)
    seats         = Column(Integer, default=5)
    connectors_limit = Column(Integer, default=5)
    ai_credits_monthly = Column(Integer, default=10)
    billing_email = Column(String)
    started_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


PLAN_DEFAULTS = {
    "starter":      {"mrr": 499.0,  "seats": 5,   "connectors_limit": 5,   "ai_credits_monthly": 10},
    "professional": {"mrr": 1499.0, "seats": 25,  "connectors_limit": 25,  "ai_credits_monthly": 50},
    "enterprise":   {"mrr": 5000.0, "seats": 999, "connectors_limit": 999, "ai_credits_monthly": 500},
}
