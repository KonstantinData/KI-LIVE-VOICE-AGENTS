"""Contract and isolation tests for the Liquisto internal assistant."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.liquisto_assistant_main import app as liquisto_assistant_app
from src.api.config import get_settings
from src.api.services import liquisto_assistant
from src.api.services.liquisto_assistant import (
    LiquistoAssistantConfigurationError,
    validate_local_llm_base_url,
)
from src.api.services.openai_realtime import RealtimeCallResult
from src.tenants.registry import TenantRegistryError, get_tenant_profile


SERVICE_TOKEN = "test-liquisto-service-token"
LOCAL_BASE_URL = "http://127.0.0.1:11434/v1"
LOCAL_MODEL = "liquisto-local-test"


class FakeResponse:
    """Small httpx response double."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._data


class FakeAsyncClient:
    """Captures local provider calls without network access."""

    calls: list[dict] = []
    answer = json.dumps({
        "answer": "Die wichtigste Abweichung ist Quelle A.",
        "prepared_actions": [],
    })

    def __init__(self, *, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_args) -> None:
        return None

    async def post(self, url: str, *, headers: dict, json: dict) -> FakeResponse:
        self.calls.append({"method": "POST", "url": url, "headers": headers, "json": json})
        return FakeResponse({
            "choices": [{"message": {"content": self.answer}}]
        })

    async def get(self, url: str, *, headers: dict) -> FakeResponse:
        self.calls.append({"method": "GET", "url": url, "headers": headers})
        return FakeResponse({"data": [{"id": LOCAL_MODEL}]})


@pytest.fixture(autouse=True)
def configure_local_assistant(monkeypatch):
    """Configures the test process for loopback-only local inference."""
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "test")
    monkeypatch.setattr(settings, "liquisto_assistant_service_token", SERVICE_TOKEN)
    monkeypatch.setattr(settings, "liquisto_assistant_llm_base_url", LOCAL_BASE_URL)
    monkeypatch.setattr(settings, "liquisto_assistant_llm_model", LOCAL_MODEL)
    monkeypatch.setattr(settings, "liquisto_assistant_llm_timeout_seconds", 5.0)
    monkeypatch.setattr(settings, "liquisto_assistant_llm_max_output_tokens", 400)
    monkeypatch.setattr(settings, "liquisto_assistant_voice_enabled", False)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-server-only")
    FakeAsyncClient.calls = []
    FakeAsyncClient.answer = json.dumps({
        "answer": "Die wichtigste Abweichung ist Quelle A.",
        "prepared_actions": [],
    })
    monkeypatch.setattr(liquisto_assistant.httpx, "AsyncClient", FakeAsyncClient)


def request_payload() -> dict:
    """Returns the exact valid request contract."""
    return {
        "contract_version": "2.0",
        "tenant_id": "liquisto",
        "area_id": "liquisto",
        "agent_id": "liquisto-assistant",
        "request_id": "req-123",
        "principal_id": "user-123",
        "conversation_id": None,
        "prompt": "Welche Abweichung soll ich zuerst prüfen?",
        "surface": "cockpit",
        "mode": "inform-and-prepare",
        "context": [
            {
                "source_id": "crm-open-tasks",
                "label": "Betriebslage",
                "system": "liquisto-crm",
                "permission": "crm:read",
                "observed_at": "2026-07-24T08:00:00+02:00",
                "classification": "internal",
                "content": "Lieferstatus weicht vom bestätigten Termin ab.",
            }
        ],
    }


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {SERVICE_TOKEN}"}


def voice_request_payload() -> dict:
    """Returns the exact valid internal Olivia Voice v2 contract."""
    source = request_payload()["context"][0]
    return {
        "contract_version": "2.0",
        "tenant_id": "liquisto",
        "area_id": "liquisto",
        "agent_id": "liquisto-assistant",
        "request_id": "req-voice-123",
        "principal_id": "user-123",
        "surface": "cockpit",
        "address_mode": "du",
        "context": [source],
        "client_sdp": "v=0\r\n",
    }


@pytest_asyncio.fixture
async def assistant_client():
    """Uses only the dedicated Liquisto internal-service application."""
    async with AsyncClient(
        transport=ASGITransport(app=liquisto_assistant_app),
        base_url="http://test",
    ) as local_client:
        yield local_client


@pytest.mark.asyncio
async def test_internal_voice_call_is_kill_switched_by_default(assistant_client):
    response = await assistant_client.post(
        "/assistant/voice/calls",
        headers=auth_headers(),
        json=voice_request_payload(),
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "assistant_voice_disabled"}


@pytest.mark.asyncio
async def test_internal_voice_readiness_requires_service_auth(assistant_client):
    response = await assistant_client.get("/assistant/voice/readyz")

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_service_token"}


@pytest.mark.asyncio
async def test_internal_voice_readiness_fails_when_kill_switch_is_off(
    assistant_client,
):
    response = await assistant_client.get(
        "/assistant/voice/readyz", headers=auth_headers()
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "assistant_voice_disabled"}


@pytest.mark.asyncio
async def test_internal_voice_readiness_contract_is_exact(
    assistant_client, monkeypatch
):
    monkeypatch.setattr(get_settings(), "liquisto_assistant_voice_enabled", True)

    response = await assistant_client.get(
        "/assistant/voice/readyz", headers=auth_headers()
    )

    assert response.status_code == 200
    assert response.json() == {
        "contract_version": "2.0",
        "status": "ready",
        "tenant_id": "liquisto",
        "agent_id": "liquisto-assistant",
        "channel": "voice",
        "voice_enabled": True,
    }


@pytest.mark.asyncio
async def test_internal_voice_readiness_requires_provider_key(
    assistant_client, monkeypatch
):
    settings = get_settings()
    monkeypatch.setattr(settings, "liquisto_assistant_voice_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "")

    response = await assistant_client.get(
        "/assistant/voice/readyz", headers=auth_headers()
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "assistant_voice_provider_not_configured"}


@pytest.mark.asyncio
async def test_internal_voice_readiness_requires_valid_registry(
    assistant_client, monkeypatch
):
    monkeypatch.setattr(get_settings(), "liquisto_assistant_voice_enabled", True)

    def invalid_profile(_tenant_id):
        raise TenantRegistryError("invalid")

    monkeypatch.setattr(
        "src.api.routes.assistant.get_tenant_profile", invalid_profile
    )

    response = await assistant_client.get(
        "/assistant/voice/readyz", headers=auth_headers()
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "assistant_voice_contract_not_configured"}


@pytest.mark.asyncio
async def test_internal_voice_call_requires_service_auth(assistant_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "liquisto_assistant_voice_enabled", True)

    response = await assistant_client.post(
        "/assistant/voice/calls", json=voice_request_payload()
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_service_token"}


@pytest.mark.asyncio
async def test_internal_voice_call_uses_fixed_tool_free_olivia_session(
    assistant_client, monkeypatch
):
    settings = get_settings()
    monkeypatch.setattr(settings, "liquisto_assistant_voice_enabled", True)
    calls: list[dict] = []

    async def fake_create_webrtc_call(
        self, *, client_sdp, session_config, safety_identifier
    ):
        calls.append({
            "client_sdp": client_sdp,
            "session_config": session_config,
            "safety_identifier": safety_identifier,
        })
        return RealtimeCallResult(
            sdp_answer="v=0-answer",
            provider_call_id="rtc_liquisto_123",
            expires_at=datetime(2026, 7, 24, 9, 0, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(
        "src.api.routes.assistant.OpenAIRealtimeAdapter.create_webrtc_call",
        fake_create_webrtc_call,
    )

    response = await assistant_client.post(
        "/assistant/voice/calls",
        headers=auth_headers(),
        json=voice_request_payload(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "contract_version": "2.0",
        "request_id": "req-voice-123",
        "call_id": "rtc_liquisto_123",
        "sdp_answer": "v=0-answer",
        "expires_at": "2026-07-24T09:00:00Z",
        "model": "gpt-realtime-2.1",
        "voice": "shimmer",
    }
    assert len(calls) == 1
    call = calls[0]
    assert call["client_sdp"] == "v=0\r\n"
    assert len(call["safety_identifier"]) == 64
    session = call["session_config"]
    assert session["tools"] == []
    assert session["tool_choice"] == "none"
    instructions = session["instructions"].lower()
    assert "du bist olivia" in instructions
    assert "transforming excess inventory" in instructions
    assert "lieferstatus weicht" in instructions
    for forbidden in ("kea", "lisa", "kuechen", "küchen", "kontakt", "dsgvo", "datenschutz"):
        assert forbidden not in instructions
    assert "sk-test-server-only" not in str(response.json())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tenant_id", "mein-kuechenexperte"),
        ("area_id", "other-area"),
        ("agent_id", "liquisto-lotse"),
        ("agent_id", "liquisto-intake"),
    ],
)
async def test_internal_voice_call_rejects_foreign_or_old_contract_ids(
    assistant_client, monkeypatch, field, value
):
    monkeypatch.setattr(get_settings(), "liquisto_assistant_voice_enabled", True)
    payload = voice_request_payload()
    payload[field] = value

    response = await assistant_client.post(
        "/assistant/voice/calls", headers=auth_headers(), json=payload
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_internal_voice_call_rejects_duplicate_sources(
    assistant_client, monkeypatch
):
    monkeypatch.setattr(get_settings(), "liquisto_assistant_voice_enabled", True)
    payload = voice_request_payload()
    payload["context"] = [payload["context"][0], payload["context"][0]]

    response = await assistant_client.post(
        "/assistant/voice/calls", headers=auth_headers(), json=payload
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("system", "foreign-crm"),
        ("permission", "crm:write"),
    ],
)
async def test_internal_voice_call_rejects_foreign_or_write_context(
    assistant_client, monkeypatch, field, value
):
    monkeypatch.setattr(get_settings(), "liquisto_assistant_voice_enabled", True)
    payload = voice_request_payload()
    payload["context"][0][field] = value

    response = await assistant_client.post(
        "/assistant/voice/calls", headers=auth_headers(), json=payload
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_patch",
    [
        {"source_id": "unknown-source"},
        {
            "source_id": "liquisto-trade",
            "system": "liquisto-trade",
            "permission": "trade:read",
            "classification": "internal",
        },
        {"system": "liquisto-trade"},
        {"permission": "tasks:read"},
        {"classification": "public"},
    ],
)
async def test_internal_voice_call_rejects_unknown_gated_or_mismatched_source(
    assistant_client, monkeypatch, source_patch
):
    monkeypatch.setattr(get_settings(), "liquisto_assistant_voice_enabled", True)
    payload = voice_request_payload()
    payload["context"][0].update(source_patch)

    response = await assistant_client.post(
        "/assistant/voice/calls", headers=auth_headers(), json=payload
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "assistant_source_not_allowed"}


@pytest.mark.asyncio
async def test_text_assistant_rejects_gated_source(assistant_client):
    payload = request_payload()
    payload["context"][0].update({
        "source_id": "liquisto-documents",
        "system": "liquisto-documents",
        "permission": "documents:read",
        "classification": "internal",
    })

    response = await assistant_client.post(
        "/assistant/respond", headers=auth_headers(), json=payload
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "assistant_source_not_allowed"}
    assert not FakeAsyncClient.calls


@pytest.mark.asyncio
async def test_assistant_responds_via_mocked_local_provider(assistant_client):
    """Happy path is local, tool-free, bounded, and contract exact."""
    response = await assistant_client.post(
        "/assistant/respond",
        headers=auth_headers(),
        json=request_payload(),
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "contract_version",
        "request_id",
        "response_id",
        "conversation_id",
        "mode",
        "answer_mode",
        "answer",
        "sources",
        "prepared_actions",
    }
    assert data["contract_version"] == "2.0"
    assert data["request_id"] == "req-123"
    assert data["mode"] == "inform-and-prepare"
    assert data["answer_mode"] == "analysis-only"
    assert data["answer"] == "Die wichtigste Abweichung ist Quelle A."
    assert data["sources"] == [
        {"source_id": "crm-open-tasks", "label": "Betriebslage"}
    ]
    assert data["prepared_actions"] == []

    call = FakeAsyncClient.calls[0]
    assert call["url"] == f"{LOCAL_BASE_URL}/chat/completions"
    assert call["json"]["model"] == LOCAL_MODEL
    assert "tools" not in call["json"]
    assert "functions" not in call["json"]
    serialized_messages = str(call["json"]["messages"]).lower()
    assert "du bist olivia" in serialized_messages
    assert "transforming excess inventory" in serialized_messages
    assert "olivia knowledge boundary" in serialized_messages
    assert "freigegebenes liquisto-wissen" in serialized_messages
    assert "not-executable" in serialized_messages
    for forbidden in ("kea", "lisa", "küchen", "kuechen", "mein-küchenexperte"):
        assert forbidden not in serialized_messages


@pytest.mark.asyncio
async def test_assistant_returns_non_executable_source_bound_draft(assistant_client):
    FakeAsyncClient.answer = json.dumps({
        "answer": "Ich habe einen Aufgabenentwurf vorbereitet.",
        "prepared_actions": [{
            "draft_id": "draft-123",
            "authority_mode": "draft-only",
            "kind": "task",
            "title": "Lieferabweichung prüfen",
            "target_system": "tasks",
            "source_ids": ["crm-open-tasks"],
            "prepared_at": "2026-07-24T08:05:00+02:00",
            "preview": "Lieferstatus und bestätigten Termin abgleichen.",
            "expected_effect": "Die Abweichung ist entscheidungsreif dokumentiert.",
            "risks": ["Quelldaten könnten veraltet sein."],
            "missing_information": [],
            "execution_status": "not-executable",
        }],
    })

    response = await assistant_client.post(
        "/assistant/respond", headers=auth_headers(), json=request_payload()
    )

    assert response.status_code == 200
    draft = response.json()["prepared_actions"][0]
    assert draft["authority_mode"] == "draft-only"
    assert draft["execution_status"] == "not-executable"
    assert draft["source_ids"] == ["crm-open-tasks"]


@pytest.mark.asyncio
async def test_assistant_rejects_draft_with_unavailable_source(assistant_client):
    FakeAsyncClient.answer = json.dumps({
        "answer": "Entwurf.",
        "prepared_actions": [{
            "draft_id": "draft-foreign",
            "authority_mode": "draft-only",
            "kind": "note",
            "title": "Unbelegter Entwurf",
            "target_system": "documents",
            "source_ids": ["foreign-source"],
            "prepared_at": "2026-07-24T08:05:00+02:00",
            "preview": "Nicht erlaubt.",
            "expected_effect": "Keine.",
            "risks": [],
            "missing_information": [],
            "execution_status": "not-executable",
        }],
    })

    response = await assistant_client.post(
        "/assistant/respond", headers=auth_headers(), json=request_payload()
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "local_assistant_unavailable"}


@pytest.mark.asyncio
async def test_assistant_echoes_existing_conversation_id(assistant_client):
    payload = request_payload()
    payload["conversation_id"] = "conv-existing"

    response = await assistant_client.post(
        "/assistant/respond",
        headers=auth_headers(),
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == "conv-existing"


@pytest.mark.asyncio
async def test_assistant_rejects_oversized_local_model_answer(assistant_client):
    FakeAsyncClient.answer = "x" * 6001

    response = await assistant_client.post(
        "/assistant/respond",
        headers=auth_headers(),
        json=request_payload(),
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "local_assistant_unavailable"}


@pytest.mark.asyncio
async def test_assistant_rejects_missing_bearer_token(assistant_client):
    response = await assistant_client.post("/assistant/respond", json=request_payload())

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_service_token"}
    assert not FakeAsyncClient.calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("setting_name", "value"),
    [
        ("liquisto_assistant_service_token", ""),
        ("liquisto_assistant_service_token", f"{SERVICE_TOKEN} "),
        ("liquisto_assistant_llm_base_url", ""),
        ("liquisto_assistant_llm_model", ""),
    ],
)
async def test_assistant_fails_closed_on_missing_configuration(
    assistant_client,
    monkeypatch,
    setting_name,
    value,
):
    settings = get_settings()
    monkeypatch.setattr(settings, setting_name, value)

    response = await assistant_client.post(
        "/assistant/respond",
        headers=auth_headers(),
        json=request_payload(),
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "assistant_not_configured"}
    assert not FakeAsyncClient.calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("tenant_id", "mein-kuechenexperte"),
        ("area_id", "other-area"),
        ("agent_id", "liquisto-lotse"),
        ("mode", "write"),
    ],
)
async def test_assistant_contract_mismatches_fail_closed(
    assistant_client,
    field,
    invalid_value,
):
    payload = deepcopy(request_payload())
    payload[field] = invalid_value

    response = await assistant_client.post(
        "/assistant/respond",
        headers=auth_headers(),
        json=payload,
    )

    assert response.status_code == 422
    assert not FakeAsyncClient.calls


@pytest.mark.asyncio
async def test_assistant_rejects_blank_or_oversized_prompt(assistant_client):
    for invalid_prompt in ("  ", "x" * 1201):
        payload = request_payload()
        payload["prompt"] = invalid_prompt
        response = await assistant_client.post(
            "/assistant/respond",
            headers=auth_headers(),
            json=payload,
        )
        assert response.status_code == 422
    assert not FakeAsyncClient.calls


@pytest.mark.asyncio
async def test_health_and_authenticated_readiness_contracts_are_exact(assistant_client):
    health = await assistant_client.get("/healthz")
    unauthenticated_ready = await assistant_client.get("/readyz")
    ready = await assistant_client.get("/readyz", headers=auth_headers())

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert unauthenticated_ready.status_code == 401
    assert ready.status_code == 200
    assert ready.json() == {
        "contract_version": "2.0",
        "status": "ready",
        "tenant_id": "liquisto",
        "agent_id": "liquisto-assistant",
    }


@pytest.mark.asyncio
async def test_liquisto_only_app_exposes_no_widget_voice_or_websocket_routes(
    assistant_client,
):
    assert (await assistant_client.get("/healthz")).json() == {"status": "ok"}
    assert (await assistant_client.post("/voice/session", json={})).status_code == 404
    assert (
        await assistant_client.get("/widget-config/?studio=liquisto")
    ).status_code == 404


@pytest.mark.asyncio
async def test_shared_runtime_does_not_expose_liquisto_internal_routes(client):
    assert (
        await client.post(
            "/assistant/respond",
            headers=auth_headers(),
            json=request_payload(),
        )
    ).status_code == 404
    assert (await client.get("/healthz")).status_code == 404
    assert (await client.get("/readyz", headers=auth_headers())).status_code == 404


def test_local_provider_url_is_strictly_validated():
    assert (
        validate_local_llm_base_url(LOCAL_BASE_URL, app_env="development")
        == LOCAL_BASE_URL
    )
    assert (
        validate_local_llm_base_url(
            "http://liquisto-assistant-llm:11434/v1",
            app_env="production",
        )
        == "http://liquisto-assistant-llm:11434/v1"
    )
    with pytest.raises(LiquistoAssistantConfigurationError):
        validate_local_llm_base_url("https://api.openai.com/v1", app_env="production")
    with pytest.raises(LiquistoAssistantConfigurationError):
        validate_local_llm_base_url("http://other-service:11434/v1", app_env="production")
    with pytest.raises(LiquistoAssistantConfigurationError):
        validate_local_llm_base_url("http://other-service:11434/v1", app_env="development")


def test_liquisto_assistant_registry_contract_has_no_tools():
    profile = get_tenant_profile("liquisto")
    agent = profile.assistant_agent("liquisto-assistant")
    voice = profile.live_voice_agent("liquisto-assistant")

    assert agent.agent_type == "text-assistant"
    assert agent.provider == "openai-compatible-local"
    assert agent.tools == ()
    assert agent.allowed_modes == ("inform-and-prepare",)
    assert voice.enabled is True
    assert voice.audience == "internal-authenticated"
    assert voice.tools == ()
    assert voice.contact_handoff is None
    assert profile.public_widget.voice_enabled is False
    active_sources = {
        source.id: source for source in profile.data_sources if source.status == "active"
    }
    assert set(active_sources) == {
        "liquisto-business-purpose",
        "crm-companies",
        "crm-deals",
        "crm-open-tasks",
    }
    assert active_sources["liquisto-business-purpose"].system == (
        "liquisto-tenant-registry"
    )
    assert active_sources["liquisto-business-purpose"].required_permission == (
        "tenant:read"
    )
    for source_id in ("crm-companies", "crm-deals", "crm-open-tasks"):
        assert active_sources[source_id].system == "liquisto-crm"
        assert active_sources[source_id].required_permission == "crm:read"
        assert active_sources[source_id].allowed_classifications == ("internal",)
    assert all(
        source.status == "planned"
        for source in profile.data_sources
        if source.id
        in {
            "liquisto-cloud-architecture",
            "liquisto-platform-content",
            "liquisto-internal-processes",
            "liquisto-website",
            "liquisto-trade",
            "liquisto-control",
            "liquisto-documents",
            "liquisto-integrations",
        }
    )


def test_deployment_contract_matches_scas_internal_endpoint():
    compose = Path("deploy/liquisto-assistant/compose.yaml").read_text(encoding="utf-8")
    dockerfile = Path("deploy/liquisto-assistant/Dockerfile").read_text(encoding="utf-8")
    deployment_docs = Path("deploy/liquisto-assistant/README.md").read_text(
        encoding="utf-8"
    )

    assert "liquisto-local-assistant:" in compose
    assert "name: liquisto-assistant" in compose
    assert "127.0.0.1:8080/healthz" in compose
    assert 'LIQUISTO_ASSISTANT_LLM_TIMEOUT_SECONDS: "60"' in compose
    assert "LIQUISTO_ASSISTANT_VOICE_ENABLED" in compose
    assert "OPENAI_API_KEY" in compose
    assert "EXPOSE 8080" in dockerfile
    assert '"--port", "8080"' in dockerfile
    assert (
        "http://liquisto-local-assistant:8080/assistant/respond" in deployment_docs
    )
    assert (
        "http://liquisto-local-assistant:8080/assistant/voice/calls"
        in deployment_docs
    )
