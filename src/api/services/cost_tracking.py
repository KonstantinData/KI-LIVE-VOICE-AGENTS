"""Provider cost tracking helpers.

What: Converts OpenAI usage payloads into tenant-scoped cost events.
Does: Normalizes token details, applies pricing snapshots, and creates DB rows.
Why: Per-chat cost reporting needs consistent raw usage and estimated cost storage.
Who: Voice usage reporting and upload analysis routes.
Depends on: decimal, sqlalchemy session, ConversationCostEvent model.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.conversation_cost_event import ConversationCostEvent

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


async def record_openai_cost_event(
    *,
    session: AsyncSession,
    studio_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    event_type: str,
    channel: str,
    component: str,
    model: str,
    usage: dict[str, Any] | None,
    lead_id: uuid.UUID | None = None,
    message_id: uuid.UUID | None = None,
    provider_event_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ConversationCostEvent:
    """Stores one normalized OpenAI usage/cost event."""
    normalized = normalize_openai_usage(usage)
    event = ConversationCostEvent(
        studio_id=studio_id,
        conversation_id=conversation_id,
        lead_id=lead_id,
        message_id=message_id,
        event_type=event_type,
        channel=channel,
        component=component,
        provider="openai",
        provider_event_id=provider_event_id,
        model=model,
        estimated_cost_usd=estimate_openai_cost_usd(model, normalized),
        pricing_snapshot=PRICING_SNAPSHOT if _rates_for_model(model) else None,
        metadata_=metadata,
        **normalized,
    )
    session.add(event)
    return event
