"""Contract and isolation tests for the Liquisto internal assistant."""

from __future__ import annotations

from copy import deepcopy
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
from src.tenants.registry import get_tenant_profile


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
    answer = "Die wichtigste Abweichung ist Quelle A."

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
    FakeAsyncClient.calls = []
    FakeAsyncClient.answer = "Die wichtigste Abweichung ist Quelle A."
    monkeypatch.setattr(liquisto_assistant.httpx, "AsyncClient", FakeAsyncClient)


def request_payload() -> dict:
    """Returns the exact valid request contract."""
    return {
        "contract_version": "1.0",
        "tenant_id": "liquisto",
        "area_id": "liquisto",
        "agent_id": "liquisto-lotse",
        "request_id": "req-123",
        "principal_id": "user-123",
        "conversation_id": None,
        "prompt": "Welche Abweichung soll ich zuerst prüfen?",
        "surface": "cockpit",
        "mode": "analysis-only",
        "context": [
            {
                "source_id": "source-a",
                "label": "Betriebslage",
                "content": "Lieferstatus weicht vom bestätigten Termin ab.",
            }
        ],
    }


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {SERVICE_TOKEN}"}


@pytest_asyncio.fixture
async def assistant_client():
    """Uses only the dedicated Liquisto internal-service application."""
    async with AsyncClient(
        transport=ASGITransport(app=liquisto_assistant_app),
        base_url="http://test",
    ) as local_client:
        yield local_client


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
        "answer",
        "sources",
    }
    assert data["contract_version"] == "1.0"
    assert data["request_id"] == "req-123"
    assert data["mode"] == "analysis-only"
    assert data["answer"] == "Die wichtigste Abweichung ist Quelle A."
    assert data["sources"] == [{"source_id": "source-a", "label": "Betriebslage"}]

    call = FakeAsyncClient.calls[0]
    assert call["url"] == f"{LOCAL_BASE_URL}/chat/completions"
    assert call["json"]["model"] == LOCAL_MODEL
    assert "tools" not in call["json"]
    assert "functions" not in call["json"]
    serialized_messages = str(call["json"]["messages"]).lower()
    for forbidden in ("kea", "lisa", "küchen", "kuechen", "mein-küchenexperte"):
        assert forbidden not in serialized_messages


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
        ("agent_id", "liquisto-intake"),
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
        "contract_version": "1.0",
        "status": "ready",
        "tenant_id": "liquisto",
        "agent_id": "liquisto-lotse",
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
    agent = profile.assistant_agent("liquisto-lotse")

    assert agent.agent_type == "text-assistant"
    assert agent.provider == "openai-compatible-local"
    assert agent.tools == ()
    assert agent.allowed_modes == ("analysis-only",)


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
    assert "EXPOSE 8080" in dockerfile
    assert '"--port", "8080"' in dockerfile
    assert (
        "http://liquisto-local-assistant:8080/assistant/respond" in deployment_docs
    )
