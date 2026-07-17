"""CRM handoff client.

What: Sends sanitized KEA handoff and usage events to the Mein Küchenexperte CRM.
Does: Normalizes voice contact and provider usage payloads, then posts them to CRM webhooks.
Why: The CRM source of truth lives in the mein-kuechenexperte repository, not here.
Who: Voice and upload routes call this service after consent-gated customer actions.
Depends on: httpx, decimal, src.api.config
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import os
from typing import Any

import httpx

from src.api.config import get_settings

CRM_TENANT_ID = "mein-kuechenexperte"
PRICING_SNAPSHOT = "openai_2026-07-07"
MILLION = Decimal("1000000")


@dataclass(frozen=True)
class ModelTokenRates:
    """Per-million token rates for one provider model."""

    text_input: Decimal
    text_cached_input: Decimal
    text_output: Decimal
    audio_input: Decimal = Decimal("0")
    audio_cached_input: Decimal = Decimal("0")
    audio_output: Decimal = Decimal("0")
    image_input: Decimal = Decimal("0")
    image_cached_input: Decimal = Decimal("0")


OPENAI_RATES: dict[str, ModelTokenRates] = {
    "gpt-4o-mini": ModelTokenRates(
        text_input=Decimal("0.15"),
        text_cached_input=Decimal("0.075"),
        text_output=Decimal("0.60"),
        image_input=Decimal("0.15"),
        image_cached_input=Decimal("0.075"),
    ),
    "gpt-realtime-2.1": ModelTokenRates(
        text_input=Decimal("4.00"),
        text_cached_input=Decimal("0.40"),
        text_output=Decimal("24.00"),
        audio_input=Decimal("32.00"),
        audio_cached_input=Decimal("0.40"),
        audio_output=Decimal("64.00"),
        image_input=Decimal("5.00"),
        image_cached_input=Decimal("0.50"),
    ),
}


class CrmHandoffNotConfiguredError(RuntimeError):
    """Raised when a CRM handoff webhook or secret is missing."""


class CrmHandoffFailedError(RuntimeError):
    """Raised when the CRM rejects a handoff."""


def _rates_for_model(model: str) -> ModelTokenRates | None:
    """Returns rates for exact models and stable snapshot aliases."""
    if model in OPENAI_RATES:
        return OPENAI_RATES[model]
    if model.startswith("gpt-4o-mini"):
        return OPENAI_RATES["gpt-4o-mini"]
    if model.startswith("gpt-realtime-2.1"):
        return OPENAI_RATES["gpt-realtime-2.1"]
    return None


def _as_int(value: Any) -> int:
    """Returns a non-negative integer token count from provider JSON."""
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def normalize_openai_usage(usage: dict[str, Any] | None) -> dict[str, int]:
    """Normalizes OpenAI usage fields from chat or realtime responses."""
    usage = usage or {}
    input_details = usage.get("input_token_details") or {}
    cached_details = input_details.get("cached_tokens_details") or {}
    output_details = usage.get("output_token_details") or {}

    prompt_tokens = _as_int(usage.get("prompt_tokens"))
    completion_tokens = _as_int(usage.get("completion_tokens"))
    input_tokens = _as_int(usage.get("input_tokens")) or prompt_tokens
    output_tokens = _as_int(usage.get("output_tokens")) or completion_tokens
    total_tokens = _as_int(usage.get("total_tokens")) or input_tokens + output_tokens

    cached_text = _as_int(cached_details.get("text_tokens"))
    cached_audio = _as_int(cached_details.get("audio_tokens"))
    cached_image = _as_int(cached_details.get("image_tokens"))
    input_text = _as_int(input_details.get("text_tokens"))
    input_audio = _as_int(input_details.get("audio_tokens"))
    input_image = _as_int(input_details.get("image_tokens"))
    if not any((input_text, input_audio, input_image)) and input_tokens:
        input_text = input_tokens

    output_text = _as_int(output_details.get("text_tokens"))
    output_audio = _as_int(output_details.get("audio_tokens"))
    if not any((output_text, output_audio)) and output_tokens:
        output_text = output_tokens

    return {
        "total_tokens": total_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_text_tokens": input_text,
        "input_audio_tokens": input_audio,
        "input_image_tokens": input_image,
        "cached_text_tokens": cached_text,
        "cached_audio_tokens": cached_audio,
        "cached_image_tokens": cached_image,
        "output_text_tokens": output_text,
        "output_audio_tokens": output_audio,
    }


def estimate_openai_cost_usd(model: str, tokens: dict[str, int]) -> Decimal | None:
    """Estimates event cost from a pricing snapshot and normalized token counts."""
    rates = _rates_for_model(model)
    if rates is None:
        return None

    billable_text_input = max(
        0, tokens["input_text_tokens"] - tokens["cached_text_tokens"]
    )
    billable_audio_input = max(
        0, tokens["input_audio_tokens"] - tokens["cached_audio_tokens"]
    )
    billable_image_input = max(
        0, tokens["input_image_tokens"] - tokens["cached_image_tokens"]
    )
    total = (
        Decimal(billable_text_input) * rates.text_input
        + Decimal(tokens["cached_text_tokens"]) * rates.text_cached_input
        + Decimal(tokens["output_text_tokens"]) * rates.text_output
        + Decimal(billable_audio_input) * rates.audio_input
        + Decimal(tokens["cached_audio_tokens"]) * rates.audio_cached_input
        + Decimal(tokens["output_audio_tokens"]) * rates.audio_output
        + Decimal(billable_image_input) * rates.image_input
        + Decimal(tokens["cached_image_tokens"]) * rates.image_cached_input
    ) / MILLION
    return total.quantize(Decimal("0.000001"))


def _website_url() -> str:
    """Returns the configured public CRM website URL."""
    configured = get_settings().website_url.rstrip("/")
    if configured in {
        "https://www.mein-kuechenexperte.de",
        "http://www.mein-kuechenexperte.de",
    }:
        return configured.replace("://www.", "://", 1)
    return configured


def _contact_handoff_endpoint() -> str:
    """Returns the CRM contact handoff endpoint."""
    settings = get_settings()
    return (
        settings.crm_contact_handoff_endpoint.strip()
        or f"{_website_url()}/agent-lead-webhook"
    )


def _usage_handoff_endpoint() -> str:
    """Returns the CRM AI usage handoff endpoint."""
    settings = get_settings()
    return (
        settings.crm_usage_handoff_endpoint.strip()
        or f"{_website_url()}/agent-usage-webhook"
    )


def _configured_secret(*values: str) -> str:
    """Returns the first configured shared secret from canonical and legacy names."""
    for value in values:
        secret = value.strip()
        if secret:
            return secret
    return ""


def _contact_handoff_secret() -> str:
    """Returns the contact webhook secret, including the CRM-side env alias."""
    settings = get_settings()
    return _configured_secret(
        settings.crm_contact_handoff_secret,
        os.getenv("AGENT_WEBHOOK_SECRET", ""),
    )


def _usage_handoff_secret() -> str:
    """Returns the usage webhook secret, including the CRM-side env alias."""
    settings = get_settings()
    return _configured_secret(
        settings.crm_usage_handoff_secret,
        os.getenv("AGENT_USAGE_WEBHOOK_SECRET", ""),
    )


async def post_voice_contact_to_crm(
    *,
    run_id: str,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    source_origin: str,
    privacy_accepted: bool,
    project_summary: str,
    additional_notes: str,
    best_reachability: str,
    conversation_id: str,
    project_uploads: list[dict[str, Any]] | None = None,
) -> str:
    """Sends a sanitized voice contact handoff to the CRM webhook."""
    secret = _contact_handoff_secret()
    if not secret:
        raise CrmHandoffNotConfiguredError("crm_contact_handoff_secret_missing")

    payload = {
        "tenant_id": CRM_TENANT_ID,
        "run_id": run_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "wants_quick_check": True,
        "wants_pdf": False,
        "privacy_accepted": privacy_accepted,
        "source_origin": source_origin,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "project_summary": project_summary,
        "additional_notes": additional_notes,
        "best_reachability": best_reachability,
        "conversation_id": conversation_id,
        "project_uploads": project_uploads or [],
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            _contact_handoff_endpoint(),
            headers={
                "X-Agent-Webhook-Secret": secret,
                "Accept": "application/json",
            },
            json=payload,
        )
    if response.status_code < 200 or response.status_code >= 300:
        raise CrmHandoffFailedError(f"crm_contact_handoff_http_{response.status_code}")
    data = response.json()
    if data.get("success") is not True:
        raise CrmHandoffFailedError("crm_contact_handoff_rejected")
    return str(data.get("ledger_id") or data.get("message") or "accepted")


async def post_openai_usage_to_crm(
    *,
    source_event_id: str,
    conversation_id: str | None,
    visitor_id: str | None,
    channel_type: str,
    component: str,
    model: str,
    usage: dict[str, Any] | None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Sends normalized AI usage telemetry to the CRM usage ledger."""
    secret = _usage_handoff_secret()
    if not secret:
        raise CrmHandoffNotConfiguredError("crm_usage_handoff_secret_missing")

    normalized = normalize_openai_usage(usage)
    estimated_cost = estimate_openai_cost_usd(model, normalized)
    payload = {
        "tenant_id": CRM_TENANT_ID,
        "source_system": "ki-live-voice-agents",
        "source_event_id": source_event_id,
        "conversation_id": conversation_id or "",
        "visitor_id": visitor_id or "",
        "channel_type": channel_type,
        "component": component,
        "provider": "openai",
        "model": model,
        **normalized,
        "estimated_cost_usd": str(estimated_cost)
        if estimated_cost is not None
        else None,
        "pricing_snapshot": PRICING_SNAPSHOT if _rates_for_model(model) else "",
        "metadata": metadata or {},
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            _usage_handoff_endpoint(),
            headers={
                "X-Agent-Usage-Webhook-Secret": secret,
                "Accept": "application/json",
            },
            json=payload,
        )
    if response.status_code < 200 or response.status_code >= 300:
        raise CrmHandoffFailedError(f"crm_usage_handoff_http_{response.status_code}")
    data = response.json()
    if data.get("success") is not True:
        raise CrmHandoffFailedError("crm_usage_handoff_rejected")
    return str(data.get("usage_id") or "accepted")
