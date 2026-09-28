"""Opt-in SMTP notifications and confirmed customer summaries for Anna."""

from __future__ import annotations

import asyncio
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from dotenv import dotenv_values

SMTP_SECRET_PATH = "/run/secrets/anna_smtp"
OWNER_MAILBOX = "kontakt@mein-kuechenexperte.de"


class SMTPDeliveryError(RuntimeError):
    """A sanitized SMTP failure that never contains credentials or server replies."""


def _configuration() -> dict[str, str]:
    if os.environ.get("ANNA_DIRECT_SMTP", "").lower() != "true":
        raise SMTPDeliveryError("smtp_not_enabled")
    try:
        values = dotenv_values(SMTP_SECRET_PATH, interpolate=False)
    except (OSError, ValueError):
        raise SMTPDeliveryError("smtp_not_configured") from None
    required = {
        "SMTP_HOST": "ssl0.ovh.net",
        "SMTP_PORT": "587",
        "SMTP_SECURITY": "starttls",
        "SMTP_USER": OWNER_MAILBOX,
        "SMTP_FROM_EMAIL": OWNER_MAILBOX,
        "CONTACT_EMAIL": OWNER_MAILBOX,
    }
    if any(values.get(key) != expected for key, expected in required.items()):
        raise SMTPDeliveryError("smtp_invalid_configuration")
    password = values.get("SMTP_PASS")
    if not password:
        raise SMTPDeliveryError("smtp_not_configured")
    return {**required, "SMTP_PASS": password}


def _text(value: object, limit: int) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit]


def validate_customer_email(email: str) -> str:
    """Accept one ASCII dot-atom mailbox, never a display name or address list."""
    if not isinstance(email, str) or not email.isascii() or len(email) > 254:
        raise SMTPDeliveryError("smtp_invalid_recipient")
    parts = email.split("@")
    if len(parts) != 2:
        raise SMTPDeliveryError("smtp_invalid_recipient")
    local, domain = parts
    atom = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
    labels = domain.split(".")
    if (
        len(local) > 64
        or re.fullmatch(rf"{atom}(?:\.{atom})*", local) is None
        or len(labels) < 2
        or any(
            re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
            is None
            for label in labels
        )
    ):
        raise SMTPDeliveryError("smtp_invalid_recipient")
    return email


def _deliver(message: EmailMessage | None, recipient: str = OWNER_MAILBOX) -> bool:
    recipient = validate_customer_email(recipient)
    config = _configuration()
    try:
        with smtplib.SMTP(config["SMTP_HOST"], 587, timeout=20) as client:
            client.ehlo()
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
            client.login(config["SMTP_USER"], config["SMTP_PASS"])
            if message is not None:
                refused = client.send_message(
                    message, from_addr=OWNER_MAILBOX, to_addrs=[recipient]
                )
                if refused:
                    raise SMTPDeliveryError("smtp_delivery_failed")
    except SMTPDeliveryError:
        raise
    except (smtplib.SMTPException, OSError, ValueError, UnicodeError):
        raise SMTPDeliveryError("smtp_delivery_failed") from None
    return True


def check_smtp_connection() -> bool:
    """Authenticate over verified STARTTLS without sending a message."""
    return _deliver(None)


async def send_phone_notification(
    *, summary: str, contact: dict, session_id: str
) -> bool:
    """Send a bounded summary to the fixed owner; success means SMTP acceptance."""
    safe_summary = _text(summary, 2400)
    if not safe_summary:
        raise SMTPDeliveryError("smtp_summary_required")
    name = _text(contact.get("full_name"), 160) or _text(
        f"{contact.get('first_name', '')} {contact.get('last_name', '')}", 160
    )
    message = EmailMessage()
    message["From"] = f"Mein Küchenexperte <{OWNER_MAILBOX}>"
    message["To"] = OWNER_MAILBOX
    message["Subject"] = "Anna: Neues Telefonanliegen"
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid(domain="mein-kuechenexperte.de")
    message.set_content(
        "Anna hat ein Telefonanliegen aufgenommen.\n\n"
        f"Name: {name or 'Nicht angegeben'}\n"
        f"Telefon: {_text(contact.get('phone'), 80) or 'Nicht angegeben'}\n"
        f"E-Mail: {_text(contact.get('email'), 254) or 'Nicht angegeben'}\n\n"
        f"Kontaktweg: {_text(contact.get('preferred_channel'), 20) or 'Nicht angegeben'}\n"
        f"Erreichbarkeit: {_text(contact.get('best_reachability'), 160) or 'Nicht angegeben'}\n"
        f"Weitere Hinweise: {_text(contact.get('additional_notes'), 1600) or 'Keine'}\n\n"
        f"Anliegen: {safe_summary}\n\n"
        f"Gesprächsreferenz: {_text(session_id, 160)}\n"
    )
    return await asyncio.to_thread(_deliver, message)


async def send_customer_summary(
    *, summary: str, full_name: str, email: str, consent_confirmed: bool,
    email_confirmed: bool, session_id: str,
) -> bool:
    """Send only an agreed summary; success means SMTP acceptance, not inbox delivery."""
    if consent_confirmed is not True or email_confirmed is not True:
        raise SMTPDeliveryError("smtp_customer_confirmation_required")
    recipient = validate_customer_email(email)
    safe_summary = _text(summary, 2400)
    name = _text(full_name, 160)
    if not safe_summary:
        raise SMTPDeliveryError("smtp_summary_required")
    if not name:
        raise SMTPDeliveryError("smtp_customer_name_required")
    message = EmailMessage()
    message["From"] = f"Mein Küchenexperte <{OWNER_MAILBOX}>"
    message["To"] = recipient
    message["Reply-To"] = OWNER_MAILBOX
    message["Subject"] = "Ihre Gesprächszusammenfassung – Mein Küchenexperte"
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid(domain="mein-kuechenexperte.de")
    message.set_content(
        f"Guten Tag {name},\n\n"
        "vielen Dank für Ihren Anruf. Wie gewünscht erhalten Sie hier die "
        "mit Ihnen abgestimmte Zusammenfassung Ihres Anliegens:\n\n"
        f"{safe_summary}\n\n"
        "Wenn Sie etwas ergänzen oder korrigieren möchten, antworten Sie gerne "
        "auf diese E-Mail.\n\n"
        "Freundliche Grüße\n"
        "Anna\nKI-Telefonassistentin von Mein Küchenexperte\n"
    )
    return await asyncio.to_thread(_deliver, message, recipient)


async def send_appointment_confirmation(
    *, name: str, start: str, end: str, appointment_type: str,
    email: str, session_id: str, lang: str = "de",
) -> bool:
    """Send a professional appointment confirmation to the customer; no consent gate."""
    recipient = validate_customer_email(email)
    safe_name = _text(name, 160)
    safe_start = _text(start, 80)
    safe_end = _text(end, 80)
    safe_type = _text(appointment_type, 160)
    if not safe_name:
        raise SMTPDeliveryError("smtp_customer_name_required")
    if not safe_start:
        raise SMTPDeliveryError("smtp_appointment_start_required")

    logo_url = "https://mein-kuechenexperte.de/assets/img/logo.jpg"

    if lang == "en":
        subject = "Your Appointment Confirmation – Mein Küchenexperte"
        greeting = f"Dear {safe_name},"
        body_line1 = "Thank you for your call. Your appointment has been successfully booked."
        label_type = "Appointment"
        label_start = "Date &amp; Time"
        label_end = "End"
        closing = "We look forward to speaking with you.<br>Kind regards<br><strong>Mein K&uuml;chenexperte</strong>"
        closing_text = "We look forward to speaking with you.\nKind regards\nMein Küchenexperte"
        reply_hint = "Questions? Simply reply to this e-mail."
    else:
        subject = "Ihre Terminbestätigung – Mein Küchenexperte"
        greeting = f"Guten Tag {safe_name},"
        body_line1 = "vielen Dank für Ihren Anruf. Ihr Termin wurde erfolgreich eingetragen."
        label_type = "Terminart"
        label_start = "Datum &amp; Uhrzeit"
        label_end = "Ende"
        closing = "Wir freuen uns auf das Gespr&auml;ch mit Ihnen.<br>Mit freundlichen Gr&uuml;&szlig;en<br><strong>Mein K&uuml;chenexperte</strong>"
        closing_text = "Wir freuen uns auf das Gespräch mit Ihnen.\nMit freundlichen Grüßen\nMein Küchenexperte"
        reply_hint = "Fragen? Antworten Sie einfach auf diese E-Mail."

    html = f"""\
<html>
<body style="margin:0;padding:0;background:#1f2229;font-family:Arial,sans-serif;color:#dbe3ef;">
  <div style="max-width:640px;margin:0 auto;background:#23262e;">
    <div style="background:#4b5568;padding:22px 24px;text-align:center;">
      <img src="{logo_url}" alt="Mein K&uuml;chenexperte" width="417" height="49"
           style="max-width:320px;width:100%;height:auto;background:#fff;border-radius:6px;padding:8px;">
    </div>
    <div style="padding:28px 32px;line-height:1.65;font-size:18px;">
      <p style="margin:0 0 18px;">{greeting}</p>
      <p style="margin:0 0 24px;">{body_line1}</p>
      <table style="border-collapse:collapse;width:100%;margin:0 0 24px;font-size:17px;">
        <tr>
          <td style="padding:10px 14px;background:#2d3240;border-radius:6px 6px 0 0;"
              width="38%"><strong>{label_type}</strong></td>
          <td style="padding:10px 14px;background:#2d3240;border-radius:6px 6px 0 0;">{safe_type}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;background:#252830;"><strong>{label_start}</strong></td>
          <td style="padding:10px 14px;background:#252830;">{safe_start}</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;background:#2d3240;border-radius:0 0 6px 6px;"
              ><strong>{label_end}</strong></td>
          <td style="padding:10px 14px;background:#2d3240;border-radius:0 0 6px 6px;">{safe_end}</td>
        </tr>
      </table>
      <p style="margin:0 0 24px;font-size:15px;color:#b8c2d1;">{reply_hint}</p>
      <p style="margin:0;color:#b8c2d1;">{closing}</p>
    </div>
    <div style="background:#181c22;padding:14px 32px;text-align:center;font-size:13px;color:#6b7280;">
      mein-kuechenexperte.de
    </div>
  </div>
</body>
</html>"""

    text = (
        f"{greeting}\n\n{body_line1}\n\n"
        f"{label_type.replace('&amp;', '&')}: {safe_type}\n"
        f"{label_start.replace('&amp;', '&')}: {safe_start}\n"
        f"{label_end}: {safe_end}\n\n"
        f"{reply_hint}\n\n{closing_text}\n"
        f"\nmein-kuechenexperte.de\n"
        f"Referenz: {_text(session_id, 160)}\n"
    )

    message = EmailMessage()
    message["From"] = f"Mein Küchenexperte <{OWNER_MAILBOX}>"
    message["To"] = recipient
    message["Reply-To"] = OWNER_MAILBOX
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid(domain="mein-kuechenexperte.de")
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return await asyncio.to_thread(_deliver, message, recipient)


async def send_calendar_notification(operation: dict) -> bool:
    """Notify MKE operations; the master calendar never receives mail."""
    recipient = OWNER_MAILBOX
    labels = {"create": "Termin angelegt", "reschedule": "Termin verschoben", "cancel": "Termin abgesagt"}
    action = operation.get("action")
    if action not in labels or operation.get("calendar_changed") is not True:
        raise SMTPDeliveryError("invalid_calendar_notification")
    details = operation.get("details", {})
    original = operation.get("original") or {}
    message = EmailMessage()
    message["From"] = f"Mein Küchenexperte <{OWNER_MAILBOX}>"
    message["To"] = recipient
    message["Subject"] = "ANNA: " + labels[action]
    message["Date"] = formatdate(localtime=False)
    transaction = _text(operation.get("transaction_id"), 64)
    if re.fullmatch(r"[a-f0-9]{64}", transaction) is None:
        raise SMTPDeliveryError("invalid_calendar_notification")
    message["Message-ID"] = f"<anna-calendar-{transaction}@mein-kuechenexperte.de>"
    message.set_content(
        f"Quelle: ANNA\nVorgang: {labels[action]}\n"
        f"Name: {_text(details.get('name'), 160)}\n"
        f"Telefon: {_text(details.get('phone'), 80)}\n"
        f"E-Mail: {_text(details.get('email'), 254)}\n"
        f"Start: {_text(details.get('start'), 80)}\nEnde: {_text(details.get('end'), 80)}\n"
        f"Vorheriger Start: {_text(str(original.get('start', '')), 200)}\n"
        f"Vorheriges Ende: {_text(str(original.get('end', '')), 200)}\n"
        f"Grund: {_text(details.get('reason'), 800)}\n"
        f"Bearbeitet: {_text(operation.get('created_at'), 80)}\nReferenz: {transaction}\n"
    )
    return await asyncio.to_thread(_deliver, message, recipient)
