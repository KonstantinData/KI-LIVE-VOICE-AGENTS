"""Authenticated internal API for Olivia, the Liquisto assistant."""

from __future__ import annotations

import secrets
from datetime import datetime
import hashlib
from typing import Annotated, Literal
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
import structlog

from src.agents.liquisto_assistant.navigation import (
    NAVIGATION_DESTINATIONS,
    NAVIGATION_CONTRACT_VERSION,
    NAVIGATION_TOOL_NAME,
    liquisto_navigation_tool_definition,
)
from src.agents.liquisto_assistant.prompt import (
    build_liquisto_assistant_messages,
    build_liquisto_assistant_voice_prompt,
)
from src.api.config import Settings, get_settings
from src.api.services.liquisto_assistant import (
    LiquistoAssistantConfigurationError,
    LiquistoAssistantProviderError,
    LiquistoAssistantRuntimeConfig,
    LocalOpenAICompatibleClient,
)
from src.api.services.openai_realtime import OpenAIRealtimeAdapter
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
    """One permission-filtered, request-local source item."""

    source_id: Identifier
    label: str = Field(min_length=1, max_length=200)
    system: Identifier
    permission: Identifier
    observed_at: datetime
    classification: Literal["public", "internal"]
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("system")
    @classmethod
    def validate_tenant_system(cls, value: str) -> str:
        if not value.startswith("liquisto-"):
            raise ValueError("context system must be tenant-bound to liquisto")
        return value

    @field_validator("permission")
    @classmethod
    def validate_read_permission(cls, value: str) -> str:
        if not value.endswith(":read"):
            raise ValueError("context permission must be read-only")
        return value

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value


class AssistantRespondRequest(StrictContractModel):
    """Exact SCAS-to-runtime v2 request contract."""

    contract_version: Literal["2.0"]
    tenant_id: Literal["liquisto"]
    area_id: Literal["liquisto"]
    agent_id: Literal["liquisto-assistant"]
    request_id: Identifier
    principal_id: Identifier
    conversation_id: Identifier | None = None
    prompt: str = Field(min_length=2, max_length=1200)
    surface: Literal["cockpit", "crm", "trade", "control"]
    mode: Literal["inform-and-prepare"]
    context: list[AssistantContextItem] = Field(max_length=12)

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("prompt must contain at least two non-whitespace characters")
        return normalized

    @model_validator(mode="after")
    def validate_bounded_context(self) -> "AssistantRespondRequest":
        source_ids = [item.source_id for item in self.context]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("context source_id values must be unique")
        if sum(len(item.content) for item in self.context) > 20_000:
            raise ValueError("context content exceeds aggregate limit")
        return self


class AssistantSource(StrictContractModel):
    """One permission-filtered source available to the answer."""

    source_id: Identifier
    label: str = Field(min_length=1, max_length=200)


class PreparedAction(StrictContractModel):
    """One ephemeral, non-executable action draft."""

    draft_id: Identifier
    authority_mode: Literal["draft-only"]
    kind: Literal[
        "email", "calendar-event", "task", "change-proposal", "briefing", "note"
    ]
    title: str = Field(min_length=1, max_length=200)
    target_system: Literal[
        "email", "calendar", "tasks", "crm", "trade", "documents", "workbench"
    ]
    source_ids: list[Identifier] = Field(min_length=1, max_length=20)
    prepared_at: datetime
    preview: str = Field(min_length=1, max_length=6000)
    expected_effect: str = Field(min_length=1, max_length=1000)
    risks: list[str] = Field(max_length=10)
    missing_information: list[str] = Field(max_length=10)
    execution_status: Literal["not-executable"]

    @field_validator("source_ids")
    @classmethod
    def validate_unique_source_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("prepared action source_ids must be unique")
        return value

    @field_validator("prepared_at")
    @classmethod
    def validate_prepared_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("prepared_at must be timezone-aware")
        return value


class ProviderDraft(StrictContractModel):
    """Strict JSON object returned by the local model."""

    answer: str = Field(min_length=1, max_length=6000)
    prepared_actions: list[PreparedAction] = Field(max_length=8)


class AssistantRespondResponse(StrictContractModel):
    """Exact runtime-to-SCAS v2 response contract."""

    contract_version: Literal["2.0"] = "2.0"
    request_id: Identifier
    response_id: Identifier
    conversation_id: Identifier
    mode: Literal["inform-and-prepare"] = "inform-and-prepare"
    answer_mode: Literal["analysis-only"] = "analysis-only"
    answer: str = Field(min_length=1, max_length=6000)
    sources: list[AssistantSource]
    prepared_actions: list[PreparedAction] = Field(max_length=8)


class AssistantReadyResponse(StrictContractModel):
    """Exact authenticated readiness contract."""

    contract_version: Literal["2.0"] = "2.0"
    status: Literal["ready"] = "ready"
    tenant_id: Literal["liquisto"] = "liquisto"
    agent_id: Literal["liquisto-assistant"] = "liquisto-assistant"


class AssistantVoiceCallRequest(StrictContractModel):
    """Exact SCAS-to-runtime v2 contract for an internal Olivia WebRTC call."""

    contract_version: Literal["2.0"]
    tenant_id: Literal["liquisto"]
    area_id: Literal["liquisto"]
    agent_id: Literal["liquisto-assistant"]
    request_id: Identifier
    principal_id: Identifier
    surface: Literal["cockpit", "crm", "trade", "control"]
    address_mode: Literal["du", "sie"]
    context: list[AssistantContextItem] = Field(min_length=1, max_length=12)
    client_sdp: str = Field(min_length=1, max_length=200_000)

    @model_validator(mode="after")
    def validate_bounded_context(self) -> "AssistantVoiceCallRequest":
        source_ids = [item.source_id for item in self.context]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("context source_id values must be unique")
        if sum(len(item.content) for item in self.context) > 20_000:
            raise ValueError("context content exceeds aggregate limit")
        return self


class AssistantVoiceCallResponse(StrictContractModel):
    """Safe WebRTC connection material returned to the authenticated BFF."""

    contract_version: Literal["2.0"] = "2.0"
    request_id: Identifier
    call_id: Identifier
    sdp_answer: str = Field(min_length=1, max_length=200_000)
    expires_at: datetime
    model: str = Field(min_length=1, max_length=120)
    voice: str = Field(min_length=1, max_length=120)


class AssistantVoiceReadyResponse(StrictContractModel):
    """Exact authenticated readiness contract for Olivia Voice."""

    contract_version: Literal["2.0"] = "2.0"
    status: Literal["ready"] = "ready"
    tenant_id: Literal["liquisto"] = "liquisto"
    agent_id: Literal["liquisto-assistant"] = "liquisto-assistant"
    channel: Literal["voice"] = "voice"
    voice_enabled: Literal[True] = True
    navigation_contract_version: Literal["1.1"] = "1.1"
    navigation_destinations: tuple[
        Literal["workbench.cockpit"],
        Literal["crm.overview"],
        Literal["crm.tasks"],
    ] = NAVIGATION_DESTINATIONS


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


def _configured_assistant():
    """Loads and validates the immutable Olivia registry contract."""
    try:
        profile = get_tenant_profile("liquisto")
        agent = profile.assistant_agent("liquisto-assistant")
    except (TenantRegistryError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="assistant_contract_not_configured",
        ) from exc
    if (
        profile.studio_slug != "liquisto"
        or agent.prompt_profile != "liquisto-assistant"
        or agent.provider != "openai-compatible-local"
        or agent.model_env != "LIQUISTO_ASSISTANT_LLM_MODEL"
        or agent.tools
        or agent.allowed_modes != ("inform-and-prepare",)
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="assistant_contract_not_configured",
        )
    return profile, agent


def _configured_voice_agent():
    """Loads Olivia's internal-only, navigation-only Live Voice profile."""
    try:
        profile = get_tenant_profile("liquisto")
        agent = profile.live_voice_agent("liquisto-assistant")
    except (TenantRegistryError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="assistant_voice_contract_not_configured",
        ) from exc
    if (
        profile.studio_slug != "liquisto"
        or profile.public_widget.voice_enabled
        or agent.prompt_profile != "liquisto-assistant"
        or not agent.enabled
        or agent.audience != "internal-authenticated"
        or agent.tools != (NAVIGATION_TOOL_NAME,)
        or agent.contact_handoff is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="assistant_voice_contract_not_configured",
        )
    return profile, agent


def _validate_context_sources(profile, context: list[AssistantContextItem]) -> None:
    """Allows only exact active registry source contracts for this tenant."""
    sources = {source.id: source for source in profile.data_sources}
    for item in context:
        source = sources.get(item.source_id)
        if (
            source is None
            or source.tenant_id != profile.tenant_id
            or source.status != "active"
            or source.access_modes != ("read",)
            or item.system != source.system
            or item.permission != source.required_permission
            or item.classification not in source.allowed_classifications
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="assistant_source_not_allowed",
            )


def _validate_agent_contract(payload: AssistantRespondRequest) -> None:
    profile, agent = _configured_assistant()
    if (
        profile.tenant_id != payload.tenant_id
        or profile.studio_slug != payload.area_id
        or payload.surface not in agent.allowed_surfaces
        or payload.mode not in agent.allowed_modes
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="assistant_contract_not_allowed",
        )
    _validate_context_sources(profile, payload.context)


@router.post("/respond", response_model=AssistantRespondResponse)
async def respond(
    payload: AssistantRespondRequest,
    config: LiquistoAssistantRuntimeConfig = Depends(require_service_auth),
) -> AssistantRespondResponse:
    """Returns an analysis and zero or more strictly non-executable drafts."""
    _validate_agent_contract(payload)
    messages = build_liquisto_assistant_messages(
        prompt=payload.prompt,
        surface=payload.surface,
        context=[item.model_dump(mode="json") for item in payload.context],
    )
    try:
        raw_answer = await LocalOpenAICompatibleClient(config).respond(messages)
        provider_draft = ProviderDraft.model_validate_json(raw_answer)
        allowed_source_ids = {item.source_id for item in payload.context}
        if any(
            not set(action.source_ids).issubset(allowed_source_ids)
            for action in provider_draft.prepared_actions
        ):
            raise ValueError("prepared action references an unavailable source")
    except (LiquistoAssistantProviderError, ValidationError, ValueError) as exc:
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
        principal_id=payload.principal_id,
        surface=payload.surface,
        source_count=len(payload.context),
        prepared_action_count=len(provider_draft.prepared_actions),
    )
    return AssistantRespondResponse(
        request_id=payload.request_id,
        response_id=response_id,
        conversation_id=conversation_id,
        answer=provider_draft.answer,
        sources=[
            AssistantSource(source_id=item.source_id, label=item.label)
            for item in payload.context
        ],
        prepared_actions=provider_draft.prepared_actions,
    )


@router.post("/voice/calls", response_model=AssistantVoiceCallResponse)
async def create_internal_voice_call(
    payload: AssistantVoiceCallRequest,
    settings: Settings = Depends(get_settings),
    _config: LiquistoAssistantRuntimeConfig = Depends(require_service_auth),
) -> AssistantVoiceCallResponse:
    """Brokers one employee-authenticated, navigation-only Olivia WebRTC call."""
    if not settings.liquisto_assistant_voice_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="assistant_voice_disabled",
        )
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="assistant_voice_provider_not_configured",
        )
    if len(payload.client_sdp) > settings.max_voice_sdp_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="assistant_voice_sdp_too_large",
        )
    profile, agent = _configured_voice_agent()
    _validate_context_sources(profile, payload.context)
    instructions = build_liquisto_assistant_voice_prompt(
        studio_slug=profile.studio_slug,
        address_mode=payload.address_mode,
        surface=payload.surface,
        context=[item.model_dump(mode="json") for item in payload.context],
        request_id=payload.request_id,
        navigation_enabled=True,
    )
    session_config = {
        "type": "realtime",
        "model": agent.model,
        "instructions": instructions,
        "audio": {
            "output": {"voice": agent.voice},
            "input": {
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 450,
                    "create_response": True,
                    "interrupt_response": True,
                }
            },
        },
        "reasoning": {"effort": "low"},
        "tools": [liquisto_navigation_tool_definition()],
        "tool_choice": "auto",
    }
    safety_identifier = hashlib.sha256(
        f"liquisto:{payload.principal_id}:{payload.request_id}".encode("utf-8")
    ).hexdigest()
    try:
        call = await OpenAIRealtimeAdapter(settings).create_webrtc_call(
            client_sdp=payload.client_sdp,
            session_config=session_config,
            safety_identifier=safety_identifier,
        )
    except httpx.HTTPError as exc:
        log.warning(
            "liquisto_assistant.voice_provider_failed",
            request_id=payload.request_id,
            principal_id=payload.principal_id,
            surface=payload.surface,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="assistant_voice_unavailable",
        ) from exc
    if not call.provider_call_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="assistant_voice_call_id_missing",
        )
    log.info(
        "liquisto_assistant.voice_call_created",
        request_id=payload.request_id,
        principal_id=payload.principal_id,
        surface=payload.surface,
        source_count=len(payload.context),
        call_id=call.provider_call_id,
        tenant_id=profile.tenant_id,
        agent_id=agent.id,
        navigation_contract_version=NAVIGATION_CONTRACT_VERSION,
        navigation_tool=NAVIGATION_TOOL_NAME,
        raw_audio_stored=False,
    )
    return AssistantVoiceCallResponse(
        request_id=payload.request_id,
        call_id=call.provider_call_id,
        sdp_answer=call.sdp_answer,
        expires_at=call.expires_at,
        model=agent.model,
        voice=agent.voice,
    )


@router.get("/voice/readyz", response_model=AssistantVoiceReadyResponse)
async def assistant_voice_readiness(
    settings: Settings = Depends(get_settings),
    _config: LiquistoAssistantRuntimeConfig = Depends(require_service_auth),
) -> AssistantVoiceReadyResponse:
    """Reports ready only for the fully enabled internal Olivia Voice contract."""
    if not settings.liquisto_assistant_voice_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="assistant_voice_disabled",
        )
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="assistant_voice_provider_not_configured",
        )
    _configured_voice_agent()
    return AssistantVoiceReadyResponse()


@health_router.get("/healthz")
async def assistant_health() -> dict[str, str]:
    """Returns the exact unauthenticated liveness contract."""
    return {"status": "ok"}


@health_router.get("/readyz", response_model=AssistantReadyResponse)
async def assistant_readiness(
    config: LiquistoAssistantRuntimeConfig = Depends(require_service_auth),
) -> AssistantReadyResponse:
    """Requires the Olivia registry contract and configured local model."""
    _configured_assistant()
    if not await LocalOpenAICompatibleClient(config).ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="local_assistant_not_ready",
        )
    return AssistantReadyResponse()
