"""
Email Service
=============
What:    Resend-backed email delivery service.
Does:    Sends generic emails and appointment confirmations when explicitly enabled.
Why:     Production deployments need controlled outbound email with clear disabled-state behavior.
Who:     Future follow-up jobs, appointment workflows, and admin actions.
Depends: resend, structlog, src.api.config
"""

from typing import Any

import resend
import structlog

from src.api.config import get_settings

log = structlog.get_logger()
settings = get_settings()


class EmailServiceDisabledError(RuntimeError):
    """Raised when outbound email is disabled or not configured."""


class EmailService:
    """Sends email through Resend when ENABLE_EMAIL_SENDING=true."""

    def _ensure_enabled(self) -> None:
        """Checks that email sending is explicitly enabled and configured."""
        if not settings.enable_email_sending or not settings.resend_api_key:
            raise EmailServiceDisabledError("Email sending is disabled or not configured")
        resend.api_key = settings.resend_api_key

    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        from_name: str | None = None,
    ) -> str:
        """Sends an email and returns the provider message ID."""
        self._ensure_enabled()
        sender_name = from_name or settings.resend_from_name
        response: Any = resend.Emails.send({
            "from": f"{sender_name} <{settings.resend_from_email}>",
            "to": [to],
            "subject": subject,
            "html": html,
        })
        message_id = str(response.get("id", ""))
        log.info("email.sent", provider="resend", message_id=message_id)
        return message_id

    async def send_appointment_confirmation(
        self, to: str, appointment_data: dict
    ) -> str:
        """Sends a German appointment confirmation email."""
        subject = "Ihre Beratungsanfrage bei Mein Küchenexperte"
        html = (
            "<p>Vielen Dank für Ihre Anfrage.</p>"
            "<p>Wir haben Ihren Terminwunsch erhalten und melden uns zur Bestätigung.</p>"
            f"<p><strong>Terminwunsch:</strong> {appointment_data.get('datetime', 'offen')}</p>"
        )
        return await self.send(to=to, subject=subject, html=html)
