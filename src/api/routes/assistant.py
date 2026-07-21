"""Authenticated internal API for the Liquisto Lotse text assistant."""

from __future__ import annotations

import secrets
from typing import Annotated, Literal
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import structlog

from src.agents.liquisto_lotse.prompt import build_liquisto_lotse_messages
from src.api.config import Settings, get_settings
from src.api.services.liquisto_assistant import (
    LiquistoAssistantConfigurationError,
    LiquistoAssistantProviderError,
    LiquistoAssistantRuntimeConfig,
    LocalOpenAICompatibleClient,
)
from src.tenants.registry import TenantRegistryError, get_tenant_profile


router = APIRouter(prefix="/assistant", tags=["Liquisto Internal Assistant"])
health_router = APIRouter(tags=["Liquisto Internal Assistant"])
log = structlog.get_logger()
Identifier = Annotated[
    str,
    Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"),
]


class StrictContractModel(BaseModel):
    """Rejects unknown integration-contract fields."""

    model_config = ConfigDict(extra="forbid")


class AssistantContextItem(StrictContractModel):
    """One bounded, request-local source item."""

    source_id: Identifier
    label: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=4000)


class AssistantRespondRequest(StrictContractModel):
    """Exact SCAS-to-runtime request contract."""

    contract_version: Literal["1.0"]
    tenant_id: Literal["liquisto"]
    area_id: Literal["liquisto"]
    agent_id: Literal["liquisto-lotse"]
    request_id: Identifier
    principal_id: Identifier
    conversation_id: Identifier | None = None
    prompt: str = Field(min_length=2, max_length=1200)
    surface: Literal["cockpit", "crm", "trade", "control"]
    mode: Literal["analysis-only"]
    context: list[AssistantContextItem] = Field(max_length=12)

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        """Normalizes the bounded prompt and rejects whitespace-only input."""
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("prompt must contain at least two non-whitespace characters")
        return normalized

    @model_validator(mode="after")
    def validate_bounded_context(self) -> "AssistantRespondRequest":
        """Rejects duplicate sources and excessive aggregate context."""
        source_ids = [item.source_id for item in self.context]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("context source_id values must be unique")
        if sum(len(item.content) for item in self.context) > 20_000:
            raise ValueError("context content exceeds aggregate limit")
        return self


class AssistantSource(StrictContractModel):
    """One source attached to the generated analysis."""

    source_id: Identifier
    label: str = Field(min_length=1, max_length=200)


class AssistantRespondResponse(StrictContractModel):
    """Exact runtime-to-SCAS response contract."""

    contract_version: Literal["1.0"] = "1.0"
    request_id: Identifier
    response_id: Identifier
    conversation_id: Identifier
    mode: Literal["analysis-only"] = "analysis-only"
    answer: str = Field(min_length=1, max_length=6000)
    sources: list[AssistantSource]


class AssistantReadyResponse(StrictContractModel):
    """Exact authenticated readiness contract."""

    contract_version: Literal["1.0"] = "1.0"
    status: Literal["ready"] = "ready"
    tenant_id: Literal["liquisto"] = "liquisto"
    agent_id: Literal["liquisto-lotse"] = "liquisto-lotse"


def _runtime_config(settings: Settings) -> LiquistoAssistantRuntimeConfig:
    try:
        return LiquistoAssistantRuntimeConfig.from_settings(settings)
    except LiquistoAssistantConfigurationError as exc:
        log.error("liquisto_assistant.configuration_invalid", reason=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="assistant_not_configured",
        ) from exc


def require_service_auth(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> LiquistoAssistantRuntimeConfig:
    """Authenticates the SCAS service with a constant-time Bearer comparison."""
    config = _runtime_config(settings)
    scheme, separator, credential = (authorization or "").partition(" ")
    if (
        separator != " "
        or scheme.lower() != "bearer"
        or not credential
        or not secrets.compare_digest(credential, config.service_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_service_token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return config


def _validate_agent_contract(payload: AssistantRespondRequest) -> None:
    """Confirms registry authority for the exact internal assistant contract."""
    try:
        profile = get_tenant_profile(payload.tenant_id)
        agent = profile.assistant_agent(payload.agent_id)
    except (TenantRegistryError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="assistant_contract_not_allowed",
        ) from exc
    if (
        profile.tenant_id != payload.tenant_id
        or profile.studio_slug != payload.area_id
        or agent.prompt_profile != "liquisto-lotse"
        or agent.provider != "openai-compatible-local"
        or agent.model_env != "LIQUISTO_ASSISTANT_LLM_MODEL"
        or agent.tools
        or payload.surface not in agent.allowed_surfaces
        or payload.mode not in agent.allowed_modes
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="assistant_contract_not_allowed",
        )


@router.post("/respond", response_model=AssistantRespondResponse)
async def respond(
    payload: AssistantRespondRequest,
    config: LiquistoAssistantRuntimeConfig = Depends(require_service_auth),
) -> AssistantRespondResponse:
    """Returns a tool-free analysis from the configured local provider."""
    _validate_agent_contract(payload)
    messages = build_liquisto_lotse_messages(
        prompt=payload.prompt,
        surface=payload.surface,
        context=[item.model_dump() for item in payload.context],
    )
    try:
        answer = await LocalOpenAICompatibleClient(config).respond(messages)
    except LiquistoAssistantProviderError as exc:
        log.warning(
            "liquisto_assistant.provider_failed",
            request_id=payload.request_id,
            surface=payload.surface,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="local_assistant_unavailable",
        ) from exc

    response_id = f"resp_{uuid.uuid4().hex}"
    conversation_id = payload.conversation_id or f"conv_{uuid.uuid4().hex}"
    log.info(
        "liquisto_assistant.responded",
        request_id=payload.request_id,
        response_id=response_id,
        surface=payload.surface,
        source_count=len(payload.context),
    )
    return AssistantRespondResponse(
        request_id=payload.request_id,
        response_id=response_id,
        conversation_id=conversation_id,
        answer=answer,
        sources=[
            AssistantSource(source_id=item.source_id, label=item.label)
            for item in payload.context
        ],
    )


@health_router.get("/healthz")
async def assistant_health() -> dict[str, str]:
    """Returns the exact unauthenticated liveness contract."""
    return {"status": "ok"}


@health_router.get("/readyz", response_model=AssistantReadyResponse)
async def assistant_readiness(
    config: LiquistoAssistantRuntimeConfig = Depends(require_service_auth),
) -> AssistantReadyResponse:
    """Requires service auth, safe configuration, and the configured local model."""
    if not await LocalOpenAICompatibleClient(config).ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="local_assistant_not_ready",
        )
    return AssistantReadyResponse()
