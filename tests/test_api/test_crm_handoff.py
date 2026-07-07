"""Tests for outgoing CRM handoff payloads."""

from typing import Any

import pytest

from src.api.config import get_settings
from src.api.services import crm_handoff


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeAsyncClient:
    calls: list[dict[str, Any]] = []
    response = _FakeResponse({"success": True, "usage_id": "usage-1"})

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def post(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.response


def test_normalize_openai_usage_keeps_audio_and_cached_tokens():
    """Realtime usage is normalized before it leaves the runtime backend."""
    normalized = crm_handoff.normalize_openai_usage(
        {
            "total_tokens": 253,
            "input_tokens": 132,
            "output_tokens": 121,
            "input_token_details": {
                "text_tokens": 119,
                "audio_tokens": 13,
                "cached_tokens_details": {"text_tokens": 64},
            },
            "output_token_details": {"text_tokens": 30, "audio_tokens": 91},
        }
    )

    assert normalized["input_text_tokens"] == 119
    assert normalized["input_audio_tokens"] == 13
    assert normalized["cached_text_tokens"] == 64
    assert normalized["output_audio_tokens"] == 91


@pytest.mark.asyncio
async def test_usage_handoff_posts_to_mein_kuechenexperte_crm(monkeypatch):
    """Usage events are sent to the tenant CRM instead of local cost tables."""
    settings = get_settings()
    monkeypatch.setattr(settings, "crm_usage_handoff_secret", "secret")
    monkeypatch.setattr(settings, "website_url", "https://www.mein-kuechenexperte.de")
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.response = _FakeResponse({"success": True, "usage_id": "usage-42"})
    monkeypatch.setattr(crm_handoff.httpx, "AsyncClient", _FakeAsyncClient)

    usage_id = await crm_handoff.post_openai_usage_to_crm(
        source_event_id="resp_1",
        conversation_id="conversation-1",
        visitor_id="visitor-1",
        channel_type="voice",
        component="realtime_session",
        model="gpt-realtime-2.1",
        usage={"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
        metadata={"voice_session_id": "voice-1"},
    )

    assert usage_id == "usage-42"
    call = _FakeAsyncClient.calls[0]
    assert call["url"] == "https://mein-kuechenexperte.de/agent-usage-webhook"
    assert call["headers"]["X-Agent-Usage-Webhook-Secret"] == "secret"
    assert call["json"]["tenant_id"] == "mein-kuechenexperte"
    assert call["json"]["source_system"] == "ki-live-voice-agents"
    assert call["json"]["estimated_cost_usd"] is not None


@pytest.mark.asyncio
async def test_contact_handoff_posts_to_mein_kuechenexperte_crm(monkeypatch):
    """Contact data is forwarded to the CRM webhook with the shared secret."""
    settings = get_settings()
    monkeypatch.setattr(settings, "crm_contact_handoff_secret", "secret")
    monkeypatch.setattr(settings, "website_url", "https://www.mein-kuechenexperte.de")
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.response = _FakeResponse(
        {"success": True, "ledger_id": "ledger-1"}
    )
    monkeypatch.setattr(crm_handoff.httpx, "AsyncClient", _FakeAsyncClient)

    ledger_id = await crm_handoff.post_voice_contact_to_crm(
        run_id="voice:conversation:session",
        first_name="Max",
        last_name="Mustermann",
        email="max@example.test",
        phone="+49 171 1234567",
        source_origin="https://www.mein-kuechenexperte.de",
        privacy_accepted=True,
        project_summary="Küche mit Insel",
        additional_notes="Samstag erreichbar",
        best_reachability="Samstag",
        conversation_id="conversation-1",
        project_uploads=[
            {
                "file_id": "file-1",
                "original_filename": "grundriss.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1234,
            }
        ],
    )

    assert ledger_id == "ledger-1"
    call = _FakeAsyncClient.calls[0]
    assert call["url"] == "https://mein-kuechenexperte.de/agent-lead-webhook"
    assert call["headers"]["X-Agent-Webhook-Secret"] == "secret"
    assert call["json"]["tenant_id"] == "mein-kuechenexperte"
    assert call["json"]["email"] == "max@example.test"
    assert call["json"]["privacy_accepted"] is True
    assert call["json"]["conversation_id"] == "conversation-1"
    assert call["json"]["project_uploads"][0]["original_filename"] == "grundriss.pdf"
