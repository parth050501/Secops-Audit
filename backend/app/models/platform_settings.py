"""
Platform-wide settings — a single row holding global configuration that the
super-admin manages from the platform console (not per-tenant).

Currently holds the email/SMTP configuration used to send notifications and
reports to clients from a central address (e.g. alerts@codecoresystems.in).

The SMTP password is stored encrypted (Fernet), like other secrets.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.core.database import Base


class PlatformSettings(Base):
    __tablename__ = "platform_settings"
    id            = Column(Integer, primary_key=True)   # always a single row (id=1)

    # Email / SMTP (e.g. Amazon SES SMTP)
    smtp_host     = Column(String)                       # e.g. email-smtp.us-east-2.amazonaws.com
    smtp_port     = Column(Integer, default=587)
    smtp_user     = Column(String)                       # SES SMTP username
    smtp_password_enc = Column(String)                   # encrypted SES SMTP password
    smtp_use_tls  = Column(Boolean, default=True)
    email_from    = Column(String, default="alerts@codecoresystems.in")
    email_from_name = Column(String, default="GRCBridge")
    email_enabled = Column(Boolean, default=False)       # master switch; off until configured

    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
