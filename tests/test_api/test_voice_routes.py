"""Tests for tenant-scoped live voice routes."""

from datetime import datetime, timezone
import uuid
from typing import Any

import pytest
from sqlalchemy import select

from src.api.config import get_settings
from src.api.services.openai_realtime import RealtimeCallResult
from src.db.models.conversation import Conversation
from src.db.models.message import Message
from src.db.models.studio import Studio


class _FakeOpenAIResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeAsyncClient:
    status_code = 200
    payload: dict[str, Any] = {
        "client_secret": {"value": "eph_test_secret", "expires_at": 1_900_000_000}
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def post(self, *args: Any, **kwargs: Any) -> _FakeOpenAIResponse:
        return _FakeOpenAIResponse(self.status_code, self.payload)


async def _seed_voice_studio(db_session, *, voice_enabled: bool = True) -> Studio:
    """Creates a studio with configurable voice feature flag."""
    slug = f"voice-studio-{uuid.uuid4().hex}"
    studio = Studio(
        id=uuid.uuid4(),
        name="Mein Küchenexperte",
        slug=slug,
        api_key=f"voice-api-key-{uuid.uuid4()}",
        config={"agent_name": "KEA", "voice_enabled": voice_enabled},
        is_active=True,
    )
    db_session.add(studio)
    await db_session.flush()
    return studio


async def _seed_registered_studio(db_session, *, slug: str, name: str) -> Studio:
    """Creates a database studio that matches a tenant registry profile."""
    studio = Studio(
        id=uuid.uuid4(),
        name=name,
        slug=slug,
        api_key=f"voice-api-key-{uuid.uuid4()}",
        config={"agent_name": "Legacy Agent", "voice_enabled": True},
        is_active=True,
    )
    db_session.add(studio)
    await db_session.flush()
    return studio


@pytest.fixture(autouse=True)
def _voice_settings(monkeypatch):
    """Enables voice settings without relying on developer-local .env files."""
    settings = get_settings()
    monkeypatch.setattr(settings, "enable_voice_sessions", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(
        settings, "cors_origins", ["https://www.mein-kuechenexperte.de"]
    )


@pytest.mark.asyncio
async def test_voice_session_requires_consent(db_client, db_session):
    """Voice sessions reject requests without explicit consent."""
    studio = await _seed_voice_studio(db_session)

    response = await db_client.post(
        "/voice/sessions/webrtc",
        json={
            "studio": studio.slug,
            "visitor_id": "visitor-1",
            "client_sdp": "v=0",
            "consent_granted": False,
            "consent_version": "voice-v1",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_voice_session_rejects_disabled_studio(db_client, db_session):
    """Studio-level feature flag disables voice even when global voice is on."""
    studio = await _seed_voice_studio(db_session, voice_enabled=False)

    response = await db_client.post(
        "/voice/sessions/webrtc",
        json={
            "studio": studio.slug,
            "visitor_id": "visitor-1",
            "client_sdp": "v=0",
            "consent_granted": True,
            "consent_version": "voice-v1",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_voice_session_rejects_disabled_tenant_agent(db_client, db_session):
    """A registered tenant cannot start a disabled or foreign voice agent."""
    await _seed_registered_studio(db_session, slug="liquisto", name="Liquisto")

    disabled_response = await db_client.post(
        "/voice/sessions/webrtc",
        json={
            "studio": "liquisto",
            "agent_id": "liquisto-intake",
            "visitor_id": "visitor-1",
            "client_sdp": "v=0",
            "consent_granted": True,
            "consent_version": "voice-v1",
        },
    )
    foreign_response = await db_client.post(
        "/voice/sessions/webrtc",
        json={
            "studio": "liquisto",
            "agent_id": "kea-project-intake",
            "visitor_id": "visitor-1",
            "client_sdp": "v=0",
            "consent_granted": True,
            "consent_version": "voice-v1",
        },
    )

    assert disabled_response.status_code == 403
    assert foreign_response.status_code == 403


@pytest.mark.asyncio
async def test_voice_session_rejects_bad_origin(db_client, db_session):
    """Voice session broker applies the configured origin allowlist."""
    studio = await _seed_voice_studio(db_session)

    response = await db_client.post(
        "/voice/sessions/webrtc",
        headers={"Origin": "https://evil.example"},
        json={
            "studio": studio.slug,
            "visitor_id": "visitor-1",
            "client_sdp": "v=0",
            "consent_granted": True,
            "consent_version": "voice-v1",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_voice_session_creates_conversation_and_returns_sdp(
    db_client,
    db_session,
    monkeypatch,
):
    """Broker creates a tenant-bound voice conversation without exposing API keys."""
    studio = await _seed_voice_studio(db_session)

    async def fake_create_call(self, *, client_sdp, session_config, safety_identifier):
        assert client_sdp == "v=0"
        assert session_config["model"] == "gpt-realtime-2.1"
        assert session_config["audio"]["input"]["turn_detection"]["interrupt_response"]
        assert "konsequent per Du" in session_config["instructions"]
        assert "Kontaktformular im Chatfenster" in session_config["instructions"]
        assert "nicht an OpenAI" in session_config["instructions"]
        assert "tools" not in session_config
        assert "tool_choice" not in session_config
        assert safety_identifier
        return RealtimeCallResult(
            sdp_answer="v=0-answer",
            provider_call_id="rtc_test",
            expires_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(
        "src.api.services.openai_realtime.OpenAIRealtimeAdapter.create_webrtc_call",
        fake_create_call,
    )

    response = await db_client.post(
        "/voice/sessions/webrtc",
        json={
            "studio": studio.slug,
            "visitor_id": "visitor-voice",
            "client_sdp": "v=0",
            "consent_granted": True,
            "consent_version": "voice-v1",
            "address_mode": "du",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["sdp_answer"] == "v=0-answer"
    assert "sk-test" not in str(data)
    conversation = await db_session.get(
        Conversation, uuid.UUID(data["conversation_id"])
    )
    assert conversation is not None
    assert conversation.channel == "voice"
    assert conversation.metadata_["voice_consent"]["raw_audio_stored"] is False
    assert conversation.metadata_["address_mode"] == "du"


@pytest.mark.asyncio
async def test_voice_session_endpoint_returns_ephemeral_secret(
    db_client,
    db_session,
    monkeypatch,
):
    """Live widget route returns only an ephemeral Realtime secret."""
    studio = await _seed_voice_studio(db_session)
    monkeypatch.setattr("src.api.routes.voice.httpx.AsyncClient", _FakeAsyncClient)

    response = await db_client.post(
        "/voice/session",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        json={
            "studio": studio.slug,
            "visitor_id": "visitor-voice",
            "consent_granted": True,
            "consent_version": "voice-v1",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["client_secret"] == "eph_test_secret"
    assert data["conversation_id"]
    assert data["voice_session_id"]
    assert data["raw_audio_stored"] is False
    assert "sk-test" not in str(data)


@pytest.mark.asyncio
async def test_voice_tool_call_endpoint_is_disabled(db_client, db_session):
    """Legacy Realtime tool calls are disabled in favor of the secure form."""
    studio = await _seed_voice_studio(db_session)
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor-voice",
        channel="voice",
        status="active",
    )
    db_session.add(conversation)
    await db_session.flush()

    response = await db_client.post(
        "/voice/tool-calls",
        json={
            "studio": studio.slug,
            "visitor_id": "visitor-voice",
            "conversation_id": str(conversation.id),
            "tool_call_id": "call_1",
            "tool_name": "delete_everything",
            "arguments": {},
            "consent_granted": True,
        },
    )

    assert response.status_code == 410
    assert response.json()["detail"] == "voice_tools_disabled_use_secure_contact_form"


@pytest.mark.asyncio
async def test_voice_transcript_persists_final_messages(db_client, db_session):
    """Final voice transcript chunks are stored as tenant-bound messages."""
    studio = await _seed_voice_studio(db_session)
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor-voice",
        channel="voice",
        status="active",
    )
    db_session.add(conversation)
    await db_session.flush()

    response = await db_client.post(
        "/voice/transcripts",
        json={
            "studio": studio.slug,
            "visitor_id": "visitor-voice",
            "conversation_id": str(conversation.id),
            "role": "user",
            "text": "Ich suche eine moderne Küche.",
            "provider_event_id": "event_1",
            "consent_granted": True,
        },
    )

    assert response.status_code == 200
    messages = (
        (
            await db_session.execute(
                select(Message).where(Message.conversation_id == conversation.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(messages) == 1
    assert messages[0].content == "Ich suche eine moderne Küche."


@pytest.mark.asyncio
async def test_voice_transcript_endpoint_persists_widget_contract(
    db_client,
    db_session,
):
    """The live widget contract stores final transcripts and avoids raw audio."""
    studio = await _seed_voice_studio(db_session)
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor-voice",
        channel="voice",
        status="active",
    )
    db_session.add(conversation)
    await db_session.flush()

    response = await db_client.post(
        "/voice/transcript",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        json={
            "studio": studio.slug,
            "visitor_id": "visitor-voice",
            "conversation_id": str(conversation.id),
            "voice_session_id": "voice-test",
            "role": "assistant",
            "transcript": "Gerne, ich nehme die Eckdaten auf.",
            "provider_event_id": "event_1",
            "item_id": "item_1",
            "consent_granted": True,
            "consent_version": "voice-v1",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["stored"] is True
    messages = (
        (
            await db_session.execute(
                select(Message).where(Message.conversation_id == conversation.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(messages) == 1
    assert messages[0].role == "assistant"
    assert messages[0].tool_calls[0]["raw_audio_stored"] is False


@pytest.mark.asyncio
async def test_voice_usage_event_persists_realtime_cost(
    db_client,
    db_session,
    monkeypatch,
):
    """The widget forwards Realtime usage to the CRM cost ledger."""
    studio = await _seed_voice_studio(db_session)
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor-usage",
        channel="voice",
        status="active",
    )
    db_session.add(conversation)
    await db_session.flush()
    usage_handoffs: list[dict[str, Any]] = []

    async def fake_usage_handoff(**kwargs):
        usage_handoffs.append(kwargs)
        return "crm-usage-1"

    monkeypatch.setattr(
        "src.api.routes.voice.post_openai_usage_to_crm", fake_usage_handoff
    )

    response = await db_client.post(
        "/voice/usage-events",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        json={
            "studio": studio.slug,
            "visitor_id": "visitor-usage",
            "conversation_id": str(conversation.id),
            "voice_session_id": "voice-test",
            "event_type": "realtime_response",
            "provider_event_id": "event_1",
            "provider_response_id": "resp_1",
            "model": "gpt-realtime-2.1",
            "usage": {
                "total_tokens": 253,
                "input_tokens": 132,
                "output_tokens": 121,
                "input_token_details": {
                    "text_tokens": 119,
                    "audio_tokens": 13,
                    "image_tokens": 0,
                    "cached_tokens": 64,
                    "cached_tokens_details": {
                        "text_tokens": 64,
                        "audio_tokens": 0,
                        "image_tokens": 0,
                    },
                },
                "output_token_details": {
                    "text_tokens": 30,
                    "audio_tokens": 91,
                },
            },
            "consent_granted": True,
            "consent_version": "voice-v1",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["stored"] is True
    assert data["cost_event_id"] == "crm-usage-1"
    assert data["estimated_cost_usd"] is not None
    assert len(usage_handoffs) == 1
    event = usage_handoffs[0]
    assert event["conversation_id"] == str(conversation.id)
    assert event["visitor_id"] == "visitor-usage"
    assert event["channel_type"] == "voice"
    assert event["component"] == "realtime_session"
    assert event["metadata"]["voice_session_id"] == "voice-test"


@pytest.mark.asyncio
async def test_voice_contact_handoff_forwards_manual_form_to_crm(
    db_client,
    db_session,
    monkeypatch,
):
    """Manual contact handoff sends PII only to the tenant CRM."""
    studio = await _seed_voice_studio(db_session)
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor-contact",
        channel="voice",
        status="active",
    )
    db_session.add(conversation)
    await db_session.flush()
    crm_handoffs: list[dict[str, Any]] = []

    async def fake_crm_handoff(**kwargs):
        crm_handoffs.append(kwargs)
        return "crm-ledger-1"

    monkeypatch.setattr(
        "src.api.routes.voice.post_voice_contact_to_crm", fake_crm_handoff
    )

    response = await db_client.post(
        "/voice/contact-handoff",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        json={
            "studio": studio.slug,
            "visitor_id": "visitor-contact",
            "conversation_id": str(conversation.id),
            "voice_session_id": "voice-test",
            "first_name": "Max",
            "last_name": "Mustermann",
            "email": "max@example.com",
            "phone": "+49 176 23785746",
            "best_reachability": "Samstagvormittag",
            "project_summary": "Moderne offene Küche mit Insel und Budgetrahmen 10 bis 15 Tausend Euro.",
            "additional_notes": "Kochfeld und Spüle in der Insel prüfen.",
            "contact_consent_confirmed": True,
            "consent_granted": True,
            "consent_version": "voice-v1",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["lead_id"] is None
    assert data["emails_sent"] is False
    assert data["crm_captured"] is True
    assert data["crm_capture_id"] == "crm-ledger-1"
    assert len(crm_handoffs) == 1
    crm_payload = crm_handoffs[0]
    assert crm_payload["run_id"] == f"voice:{conversation.id}:voice-test"
    assert crm_payload["email"] == "max@example.com"
    assert crm_payload["phone"] == "+49 176 23785746"
    assert crm_payload["privacy_accepted"] is True
    assert crm_payload["conversation_id"] == str(conversation.id)
    assert crm_payload["project_uploads"] == []
    assert "transcript" not in str(crm_payload).lower()
