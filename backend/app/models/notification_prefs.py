"""
Notification & report preferences.

Authority model (as decided): the TENANT ADMIN sets the defaults for the tenant
(what each role receives, and who gets scheduled reports). Individual USERS may
optionally set their own custom preferences, which override the role default for
that user only. If a user has no custom preference, the admin/role default applies.

Two tables:
  - NotificationDefault : one row per (tenant, role) — the admin-set baseline.
  - UserNotificationPref: optional per-user override (only exists if a user
                          customizes; absence means "use the role default").

Notification types (booleans):
  report_ciso, report_engineer, report_auditor   — which report levels to email
  ticket_assigned, ticket_status                 — ticket activity
  finding_critical                               — new critical/high findings
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, UniqueConstraint
from app.core.database import Base

NOTIFICATION_TYPES = [
    "report_ciso", "report_engineer", "report_auditor",
    "ticket_assigned", "ticket_status", "finding_critical",
]

# sensible role defaults (used when an admin hasn't customized, and as the
# starting point when the admin opens the settings)
ROLE_DEFAULTS = {
    "admin":    {"report_ciso": True,  "report_engineer": True,  "report_auditor": True,
                 "ticket_assigned": True, "ticket_status": True,  "finding_critical": True},
    "manager":  {"report_ciso": True,  "report_engineer": False, "report_auditor": False,
                 "ticket_assigned": True, "ticket_status": False, "finding_critical": True},
    "engineer": {"report_ciso": False, "report_engineer": True,  "report_auditor": False,
                 "ticket_assigned": True, "ticket_status": True,  "finding_critical": True},
    "auditor":  {"report_ciso": False, "report_engineer": False, "report_auditor": True,
                 "ticket_assigned": False,"ticket_status": False, "finding_critical": False},
}


class NotificationDefault(Base):
    """Admin-set default for a role within a tenant."""
    __tablename__ = "notification_defaults"
    id         = Column(Integer, primary_key=True)
    tenant_id  = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    role       = Column(String, nullable=False)   # admin|manager|engineer|auditor

    report_ciso     = Column(Boolean, default=False)
    report_engineer = Column(Boolean, default=False)
    report_auditor  = Column(Boolean, default=False)
    ticket_assigned = Column(Boolean, default=True)
    ticket_status   = Column(Boolean, default=False)
    finding_critical = Column(Boolean, default=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("tenant_id", "role", name="uq_notif_default_tenant_role"),)


class UserNotificationPref(Base):
    """Optional per-user override. If absent, the role default applies."""
    __tablename__ = "user_notification_prefs"
    id         = Column(Integer, primary_key=True)
    tenant_id  = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    custom     = Column(Boolean, default=False)   # if False, ignore this row and use role default

    report_ciso     = Column(Boolean, default=False)
    report_engineer = Column(Boolean, default=False)
    report_auditor  = Column(Boolean, default=False)
    ticket_assigned = Column(Boolean, default=True)
    ticket_status   = Column(Boolean, default=False)
    finding_critical = Column(Boolean, default=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def _prefs_dict(obj) -> dict:
    return {t: bool(getattr(obj, t)) for t in NOTIFICATION_TYPES}
