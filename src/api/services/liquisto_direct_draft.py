"""Unwired direct-mail draft provider; authority and debit precede key access."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx
from pydantic import SecretStr

from src.api.routes.liquisto_mail import build_mail_messages
from src.api.services.liquisto_mail_openai import (
    ENDPOINT,
    MAX_RESPONSE_BYTES,
    MailOpenAIError,
    parse_json,
    request_bytes,
    response_text,
    validate_draft,
)

MAX_BYTES = 8192
FRAMING_ALLOWANCE = 16384


@dataclass(frozen=True)
class DirectDraftProvider:
    """Synchronous private-host adapter; never registered or bound at startup."""

    key_supplier: Callable[[], SecretStr] = field(repr=False)
    enabled: bool = False

    def draft(
        self, raw: bytes, *, before_http: Callable[[], Callable[[], None]]
    ) -> str:
        if self.enabled is not True:
            raise MailOpenAIError("direct_draft_disabled")
        try:
            value = parse_json(raw.decode("utf-8", errors="strict"))
            if set(value) != {"subject", "new_text"}:
                raise ValueError
        except Exception:
            raise MailOpenAIError("direct_draft_projection_denied") from None
        return asyncio.run(
            generate_direct_draft(
                value["subject"],
                value["new_text"],
                enabled=True,
                before_http=before_http,
                key_supplier=self.key_supplier,
            )
        )


def direct_request(subject: str, new_text: str) -> bytes:
    """Two projected fields only; the trusted host must clear their exact hash."""
    if (
        type(subject) is not str
        or type(new_text) is not str
        or not 1 <= len(subject) <= 180
        or not 2 <= len(new_text) <= 4000
        or any(ord(c) < 32 or ord(c) == 127 for c in subject)
        or "\x00" in new_text
    ):
        raise MailOpenAIError("direct_draft_projection_denied")
    prompt = json.dumps(
        {"subject": subject, "new_text": new_text},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    encoded = request_bytes(build_mail_messages(prompt=prompt, context=[]))
    if len(encoded) > MAX_BYTES:
        raise MailOpenAIError("direct_draft_input_too_large")
    return encoded


async def generate_direct_draft(
    subject: str,
    new_text: str,
    *,
    enabled: bool = False,
    before_http: Callable[[], Callable[[], None]],
    key_supplier: Callable[[], SecretStr],
) -> str:
    """One generation, no counter/probe/retry/fallback. No route or startup binding.

    The separately reviewed host callback must verify fresh egress/content
    authority and atomically debit its durable seven-day/USD1 ledger. It runs
    before opening a client or reading a key. This module cannot activate it.
    """
    if enabled is not True:
        raise MailOpenAIError("direct_draft_disabled")
    encoded = direct_request(subject, new_text)
    try:
        final_check = before_http()
        if not callable(final_check):
            raise ValueError
        key = key_supplier()
        if not isinstance(key, SecretStr) or not key.get_secret_value().strip():
            raise ValueError
        final_check()
        async with (
            asyncio.timeout(20),
            httpx.AsyncClient(
                timeout=httpx.Timeout(20),
                follow_redirects=False,
                trust_env=False,
            ) as client,
        ):
            final_check()
            async with client.stream(
                "POST",
                ENDPOINT,
                content=encoded,
                headers={
                    "Authorization": "Bearer " + key.get_secret_value(),
                    "Content-Type": "application/json",
                },
            ) as response:
                if response.status_code != 200:
                    raise ValueError
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise ValueError
        usage = parse_json(bytes(raw))["usage"]
        count = usage["input_tokens"]
        if type(count) is not int or not 0 < count <= len(encoded) + FRAMING_ALLOWANCE:
            raise ValueError
        return validate_draft(
            parse_json(
                response_text(
                    bytes(raw),
                    expected_input_tokens=count,
                    max_output_tokens=512,
                )
            )
        )
    except Exception:
        raise MailOpenAIError("direct_draft_failed_no_retry") from None
