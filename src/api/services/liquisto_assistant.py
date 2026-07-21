"""Local-only provider adapter for the Liquisto internal assistant."""

from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlsplit

import httpx

from src.api.config import Settings


PRODUCTION_LOCAL_LLM_BASE_URL = "http://liquisto-assistant-llm:11434/v1"
LOCAL_DEVELOPMENT_HOSTS = {"localhost", "127.0.0.1", "::1"}
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
MAX_ANSWER_CHARS = 6000


class LiquistoAssistantConfigurationError(RuntimeError):
    """Raised when the internal assistant is not safely configured."""


class LiquistoAssistantProviderError(RuntimeError):
    """Raised when the local provider cannot produce a valid response."""


@dataclass(frozen=True)
class LiquistoAssistantRuntimeConfig:
    """Validated, local-only provider configuration."""

    service_token: str
    base_url: str
    model: str
    timeout_seconds: float
    max_output_tokens: int

    @classmethod
    def from_settings(cls, settings: Settings) -> "LiquistoAssistantRuntimeConfig":
        """Builds a config and rejects missing or non-local provider settings."""
        service_token = settings.liquisto_assistant_service_token
        if not service_token or any(character.isspace() for character in service_token):
            raise LiquistoAssistantConfigurationError("service_token_missing")

        base_url = validate_local_llm_base_url(
            settings.liquisto_assistant_llm_base_url,
            app_env=settings.app_env,
        )
        model = settings.liquisto_assistant_llm_model.strip()
        if not MODEL_RE.fullmatch(model):
            raise LiquistoAssistantConfigurationError("local_llm_model_invalid")
        if not 1.0 <= settings.liquisto_assistant_llm_timeout_seconds <= 60.0:
            raise LiquistoAssistantConfigurationError("local_llm_timeout_invalid")
        if not 1 <= settings.liquisto_assistant_llm_max_output_tokens <= 4096:
            raise LiquistoAssistantConfigurationError("local_llm_output_limit_invalid")
        return cls(
            service_token=service_token,
            base_url=base_url,
            model=model,
            timeout_seconds=settings.liquisto_assistant_llm_timeout_seconds,
            max_output_tokens=settings.liquisto_assistant_llm_max_output_tokens,
        )


def validate_local_llm_base_url(raw_url: str, *, app_env: str) -> str:
    """Allows only the fixed production host or loopback development hosts."""
    normalized = raw_url.strip().rstrip("/")
    if not normalized:
        raise LiquistoAssistantConfigurationError("local_llm_base_url_missing")
    try:
        parsed = urlsplit(normalized)
        _ = parsed.port
    except ValueError as exc:
        raise LiquistoAssistantConfigurationError("local_llm_base_url_invalid") from exc
    if (
        parsed.scheme != "http"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") != "/v1"
    ):
        raise LiquistoAssistantConfigurationError("local_llm_base_url_invalid")

    if app_env.lower() in {"development", "test"}:
        if parsed.hostname not in LOCAL_DEVELOPMENT_HOSTS:
            raise LiquistoAssistantConfigurationError("local_llm_host_not_loopback")
        return normalized

    if normalized != PRODUCTION_LOCAL_LLM_BASE_URL:
        raise LiquistoAssistantConfigurationError("local_llm_host_not_internal")
    return normalized


class LocalOpenAICompatibleClient:
    """Minimal client that can call only a validated local chat-completions API."""

    def __init__(self, config: LiquistoAssistantRuntimeConfig) -> None:
        self._config = config

    async def respond(self, messages: list[dict[str, str]]) -> str:
        """Returns one local model answer without tools or provider fallback."""
        payload = {
            "model": self._config.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": self._config.max_output_tokens,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self._config.timeout_seconds) as client:
                response = await client.post(
                    f"{self._config.base_url}/chat/completions",
                    headers={"Accept": "application/json"},
                    json=payload,
                )
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LiquistoAssistantProviderError("local_llm_response_invalid") from exc
        if not isinstance(answer, str) or not answer.strip():
            raise LiquistoAssistantProviderError("local_llm_answer_empty")
        answer = answer.strip()
        if len(answer) > MAX_ANSWER_CHARS:
            raise LiquistoAssistantProviderError("local_llm_answer_too_long")
        return answer

    async def ready(self) -> bool:
        """Checks that the configured model is visible on the local provider."""
        try:
            async with httpx.AsyncClient(timeout=min(self._config.timeout_seconds, 3.0)) as client:
                response = await client.get(
                    f"{self._config.base_url}/models",
                    headers={"Accept": "application/json"},
                )
            response.raise_for_status()
            data = response.json()
            models = data.get("data", [])
            return any(item.get("id") == self._config.model for item in models)
        except (httpx.HTTPError, AttributeError, TypeError, ValueError):
            return False
