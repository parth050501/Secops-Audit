"""
Email service — sends notifications/reports via the platform's SMTP config.

DESIGN PRINCIPLE: FAIL SAFE. Email is best-effort. If SMTP isn't configured, or
sending fails for any reason, this logs a warning and returns False — it NEVER
raises into the caller. So an unconfigured or misconfigured email setup can never
break report generation, ticket updates, or anything else. Email is additive.

Configuration comes from the single PlatformSettings row (managed on the platform
console). Until email_enabled is true and SMTP is set, send() is a no-op that
returns False.
"""
import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.platform_settings import PlatformSettings
from app.core.encryption import decrypt_value

log = logging.getLogger("email")


async def _get_settings():
    async with AsyncSessionLocal() as db:
        return (await db.execute(
            select(PlatformSettings).where(PlatformSettings.id == 1)
        )).scalar_one_or_none()


async def email_configured() -> bool:
    s = await _get_settings()
    return bool(s and s.email_enabled and s.smtp_host and s.smtp_user)


async def send_email(to_address: str, subject: str, body_html: str,
                     body_text: str = None) -> bool:
    """Best-effort send. Returns True on success, False otherwise. Never raises."""
    try:
        s = await _get_settings()
        if not s or not s.email_enabled:
            log.info("email not enabled; skipping send to %s", to_address)
            return False
        if not (s.smtp_host and s.smtp_user and s.smtp_password_enc):
            log.warning("email enabled but SMTP not fully configured; skipping")
            return False
        if not to_address:
            return False

        try:
            password = decrypt_value(s.smtp_password_enc)
        except Exception as e:
            log.warning("could not decrypt SMTP password: %s", e)
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{s.email_from_name} <{s.email_from}>"
        msg["To"] = to_address
        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        port = s.smtp_port or 587
        if s.smtp_use_tls:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(s.smtp_host, port, timeout=20) as server:
                server.starttls(context=ctx)
                server.login(s.smtp_user, password)
                server.sendmail(s.email_from, [to_address], msg.as_string())
        else:
            with smtplib.SMTP_SSL(s.smtp_host, port, timeout=20) as server:
                server.login(s.smtp_user, password)
                server.sendmail(s.email_from, [to_address], msg.as_string())

        log.info("email sent to %s (subject: %s)", to_address, subject)
        return True
    except Exception as e:
        # FAIL SAFE — log and swallow. Never break the caller.
        log.warning("email send failed to %s: %s", to_address, e)
        return False


async def send_test_email(to_address: str) -> tuple:
    """Send a test email; returns (ok, message) for the config UI to display."""
    ok = await send_email(
        to_address,
        "GRCBridge — test email",
        "<p>This is a test email from your GRCBridge platform. "
        "If you received it, your SMTP configuration is working.</p>",
        "This is a test email from your GRCBridge platform. "
        "If you received it, your SMTP configuration is working.",
    )
    if ok:
        return True, f"Test email sent to {to_address}."
    return False, ("Could not send. Check that email is enabled and SMTP host, "
                   "user, and password are correct.")


# ── Notification helpers (compose + send common messages) ──

async def notify_ticket_event(to_address: str, ticket_title: str, event: str,
                              tenant_name: str = "") -> bool:
    subject = f"[GRCBridge] Ticket {event}: {ticket_title}"
    html = (f"<p>A compliance ticket was <b>{event}</b>.</p>"
            f"<p><b>{ticket_title}</b></p>"
            f"{'<p>Organization: ' + tenant_name + '</p>' if tenant_name else ''}"
            f"<p>Log in to GRCBridge to view details.</p>")
    return await send_email(to_address, subject, html)


async def send_report_email(to_address: str, tenant_name: str, summary_html: str) -> bool:
    subject = f"[GRCBridge] Compliance report — {tenant_name}"
    html = (f"<p>Here is your latest compliance summary for <b>{tenant_name}</b>.</p>"
            f"{summary_html}"
            f"<p>Log in to GRCBridge for the full report.</p>")
    return await send_email(to_address, subject, html)
