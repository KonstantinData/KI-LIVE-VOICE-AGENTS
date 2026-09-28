"""Consent-gated, tenant-bound contact handoff for Anna's telephone channel."""

from __future__ import annotations

import re
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from src.tenants.models import PhoneAgentProfile


class PhoneContactHandoffError(RuntimeError):
    """A customer-safe telephone handoff failure."""


def _text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit]


def _email(value: Any) -> str:
    candidate = _text(value, 254).lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", candidate):
        raise PhoneContactHandoffError("invalid_email")
    return candidate


def _phone(value: Any) -> str:
    candidate = _text(value, 50)
    digits = re.sub(r"\D", "", candidate)
    if candidate and not 6 <= len(digits) <= 20:
        raise PhoneContactHandoffError("invalid_phone")
    return candidate


def _utf8_text(value: Any, max_bytes: int) -> str:
    """Normalize text and truncate without cutting a UTF-8 code point."""
    normalized = " ".join(str(value or "").replace("\x00", " ").split())
    encoded = normalized.encode("utf-8")
    if len(encoded) <= max_bytes:
        return normalized
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


async def submit_phone_contact_handoff(
    *,
    tenant_id: str,
    agent: PhoneAgentProfile,
    arguments: dict[str, Any],
    transcript: str,
    contact_secret: str,
    session_id: str,
) -> dict[str, Any]:
    """Send one purpose-limited voice capture through the configured CRM boundary."""
    policy = agent.contact_handoff
    if (
        tenant_id != "mein-kuechenexperte"
        or agent.id != "anna-phone-assistant"
        or "submit_phone_contact_handoff" not in agent.tools
        or policy is None
        or policy.crm_target != tenant_id
    ):
        raise PhoneContactHandoffError("phone_handoff_not_authorized")
    if arguments.get("contact_consent_confirmed") is not True:
        raise PhoneContactHandoffError("contact_consent_required")
    if os.getenv("ANNA_DIRECT_SMTP") == "true":
        from .mail import (
            SMTPDeliveryError, send_customer_summary, send_phone_notification,
            validate_customer_email,
        )

        first_name = _text(arguments.get("first_name"), 80)
        last_name = _text(arguments.get("last_name"), 80)
        if not first_name or not last_name:
            raise PhoneContactHandoffError("invalid_name")
        email = _email(arguments["email"]) if arguments.get("email") else ""
        phone = _phone(arguments.get("phone"))
        if not email and not phone:
            raise PhoneContactHandoffError("return_channel_required")
        summary = _utf8_text(arguments.get("conversation_summary"), 2400)
        if not summary:
            raise PhoneContactHandoffError("summary_required")
        customer_requested = arguments.get("customer_summary_consent_confirmed") is True
        if customer_requested and (
            not email or arguments.get("email_confirmed") is not True
        ):
            raise PhoneContactHandoffError("confirmed_customer_email_required")
        if customer_requested:
            try:
                email = validate_customer_email(arguments["email"])
            except SMTPDeliveryError:
                raise PhoneContactHandoffError("invalid_customer_email") from None
        internal_accepted = False
        customer_accepted = False
        try:
            internal_accepted = await send_phone_notification(
                summary=summary,
                contact={
                    "full_name": f"{first_name} {last_name}",
                    "email": email, "phone": phone,
                    "best_reachability": _text(arguments.get("best_reachability"), 160),
                    "preferred_channel": _text(arguments.get("preferred_channel"), 20),
                    "additional_notes": _utf8_text(arguments.get("additional_notes"), 1600),
                },
                session_id=session_id,
            )
        except SMTPDeliveryError:
            pass  # Preserve each independent outcome without exposing provider details.
        if customer_requested:
            try:
                customer_accepted = await send_customer_summary(
                    summary=summary, full_name=f"{first_name} {last_name}", email=email,
                    consent_confirmed=True, email_confirmed=True, session_id=session_id,
                )
            except SMTPDeliveryError:
                pass
        return {
            "success": internal_accepted and (not customer_requested or customer_accepted),
            "internal_email_sent": internal_accepted,
            "customer_email_sent": customer_accepted,
            "crm_captured": False,
            "customer_summary_requested": customer_requested,
        }
    if arguments.get("transcript_consent_confirmed") is not True:
        raise PhoneContactHandoffError("transcript_consent_required")

    first_name = _text(arguments.get("first_name"), 80)
    last_name = _text(arguments.get("last_name"), 80)
    if len(first_name) < 2 or len(last_name) < 2:
        raise PhoneContactHandoffError("invalid_name")
    email = _email(arguments.get("email"))
    phone = _phone(arguments.get("phone"))
    summary = _utf8_text(arguments.get("conversation_summary"), 2400)
    if not summary:
        raise PhoneContactHandoffError("summary_required")
    normalized_transcript = _utf8_text(transcript, 12000)
    if not normalized_transcript:
        raise PhoneContactHandoffError("transcript_unavailable")
    if not contact_secret.strip():
        raise PhoneContactHandoffError("crm_handoff_not_configured")

    try:
        occurred_at = datetime.now(timezone.utc).isoformat()
        event_id = f"{agent.id}:{session_id}"
        payload = {
            "tenant_id": tenant_id,
            "agent_id": agent.id,
            "source_system": "ki-live-voice-agents",
            "event_id": event_id,
            "session_id": session_id,
            "conversation_id": session_id,
            "occurred_at_utc": occurred_at,
            "preferred_channel": _text(arguments.get("preferred_channel"), 20) or "email",
            "contact": {
                "first_name": first_name,
                "last_name": last_name,
                "full_name": f"{first_name} {last_name}",
                "email": email,
                "phone": phone,
            },
            "consent": {
                "contact_capture_accepted": True,
                "transcript_processing_accepted": True,
                "customer_summary_email_accepted": True,
                "version": "anna-phone-consent-v1",
                "captured_at_utc": occurred_at,
            },
            "transcript": normalized_transcript,
            "transcript_language": "de-DE",
            # Realtime transcript events provide no calibrated confidence value.
            "transcript_confidence": None,
            "customer_summary": _utf8_text(summary, 2400),
            "additional_notes": _utf8_text(arguments.get("additional_notes"), 1600),
            "best_reachability": _text(arguments.get("best_reachability"), 160),
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                policy.contact_endpoint,
                headers={
                    "X-Anna-Webhook-Secret": contact_secret,
                    "Accept": "application/json",
                },
                json=payload,
            )
        if not 200 <= response.status_code < 300:
            raise PhoneContactHandoffError("crm_handoff_failed")
        response_data = response.json()
        if response_data.get("success") is not True:
            raise PhoneContactHandoffError("crm_handoff_failed")
    except PhoneContactHandoffError:
        raise
    except (httpx.HTTPError, ValueError):
        raise PhoneContactHandoffError("crm_handoff_failed") from None
    return {"success": True, "crm_captured": True, "customer_summary_requested": True}
