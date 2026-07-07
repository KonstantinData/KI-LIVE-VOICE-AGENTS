"""
Voice Session Routes
====================
What:    FastAPI routes for browser live voice sessions.
Does:    Brokers WebRTC SDP, persists consent-safe transcripts, executes allowlisted tools.
Why:     Voice mode needs tenant checks, consent checks, server-side credentials, and audits.
Who:     Website widget voice mode.
Depends: fastapi, sqlalchemy, src.api.services, src.agents.lisa
"""

import uuid
from datetime import datetime, timedelta, timezone
import re
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.lisa.agent import LisaAgent
from src.api.config import get_settings
from src.api.services.crm_handoff import (
    CrmHandoffFailedError,
    CrmHandoffNotConfiguredError,
    estimate_openai_cost_usd,
    normalize_openai_usage,
    post_openai_usage_to_crm,
    post_voice_contact_to_crm,
)
from src.api.services.project_uploads import list_stored_project_uploads
from src.api.services.openai_realtime import OpenAIRealtimeAdapter
from src.api.services.voice_sessions import (
    load_voice_conversation,
    load_voice_studio,
    origin_allowed,
    realtime_session_config,
    safety_identifier,
    voice_enabled,
)
from src.core.memory import MemoryManager
from src.db.database import get_session
from src.db.models.event import Event
from src.db.models.message import Message
from src.tenants.registry import get_tenant_profile_for_studio

router = APIRouter(prefix="/voice", tags=["Live Voice"])
log = structlog.get_logger()
MAX_CONTACT_TEXT_CHARS = 1600
EMAIL_RE = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")
PHONE_RE = re.compile(r"^[+()0-9\s./-]{6,50}$")


class VoiceSessionRequest(BaseModel):
    studio: str = Field(min_length=1, max_length=100)
    visitor_id: str = Field(min_length=1, max_length=255)
    client_sdp: str = Field(min_length=1)
    consent_granted: bool
    consent_version: str = Field(min_length=1, max_length=50)
    address_mode: str = Field(default="sie", pattern="^(du|sie)$")


class EphemeralVoiceSessionRequest(BaseModel):
    studio: str = Field(min_length=1, max_length=100)
    visitor_id: str = Field(min_length=1, max_length=255)
    consent_granted: bool
    consent_version: str = Field(min_length=1, max_length=80)
    session_id: str | None = Field(default=None, max_length=120)
    address_mode: str = Field(default="sie", pattern="^(du|sie)$")


class EphemeralVoiceSessionResponse(BaseModel):
    client_secret: str
    expires_at: str
    model: str
    voice: str
    conversation_id: str
    voice_session_id: str
    raw_audio_stored: bool = False


class VoiceToolCallRequest(BaseModel):
    studio: str = Field(min_length=1, max_length=100)
    visitor_id: str = Field(min_length=1, max_length=255)
    conversation_id: uuid.UUID
    tool_call_id: str = Field(min_length=1, max_length=255)
    tool_name: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)
    consent_granted: bool


class VoiceTranscriptRequest(BaseModel):
    studio: str = Field(min_length=1, max_length=100)
    visitor_id: str = Field(min_length=1, max_length=255)
    conversation_id: uuid.UUID
    role: str = Field(pattern="^(user|assistant)$")
    text: str = Field(min_length=1, max_length=4000)
    provider_event_id: str | None = Field(default=None, max_length=255)
    consent_granted: bool


class VoiceFinalTranscriptRequest(BaseModel):
    studio: str = Field(min_length=1, max_length=100)
    visitor_id: str = Field(min_length=1, max_length=255)
    conversation_id: uuid.UUID
    voice_session_id: str = Field(min_length=1, max_length=120)
    role: str = Field(pattern="^(user|assistant)$")
    transcript: str = Field(min_length=1, max_length=4000)
    provider_event_id: str | None = Field(default=None, max_length=255)
    item_id: str | None = Field(default=None, max_length=255)
    consent_granted: bool
    consent_version: str = Field(min_length=1, max_length=80)


class VoiceUsageEventRequest(BaseModel):
    """Realtime usage event reported by the browser data channel."""

    studio: str = Field(min_length=1, max_length=100)
    visitor_id: str = Field(min_length=1, max_length=255)
    conversation_id: uuid.UUID
    voice_session_id: str = Field(min_length=1, max_length=120)
    event_type: str = Field(
        pattern="^(realtime_response|realtime_input_transcription)$"
    )
    provider_event_id: str | None = Field(default=None, max_length=255)
    provider_response_id: str | None = Field(default=None, max_length=255)
    model: str = Field(default="gpt-realtime-2.1", min_length=1, max_length=120)
    usage: dict[str, Any] = Field(default_factory=dict)
    consent_granted: bool
    consent_version: str = Field(min_length=1, max_length=80)


class VoiceUsageEventResponse(BaseModel):
    """CRM usage handoff result."""

    stored: bool
    cost_event_id: str
    estimated_cost_usd: str | None = None


class VoiceEndRequest(BaseModel):
    studio: str = Field(min_length=1, max_length=100)
    visitor_id: str = Field(min_length=1, max_length=255)
    conversation_id: uuid.UUID
    close_reason: str = Field(default="user_ended", max_length=100)
    consent_granted: bool


class VoiceContactHandoffRequest(BaseModel):
    """Manual contact form submission sent directly to the private API."""

    studio: str = Field(min_length=1, max_length=100)
    visitor_id: str = Field(min_length=1, max_length=255)
    conversation_id: uuid.UUID
    voice_session_id: str = Field(min_length=1, max_length=120)
    first_name: str = Field(min_length=2, max_length=80)
    last_name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=3, max_length=254)
    phone: str | None = Field(default=None, max_length=50)
    best_reachability: str | None = Field(default=None, max_length=160)
    project_summary: str = Field(default="", max_length=1600)
    additional_notes: str | None = Field(default=None, max_length=1600)
    contact_consent_confirmed: bool
    consent_granted: bool
    consent_version: str = Field(min_length=1, max_length=80)


class VoiceContactHandoffResponse(BaseModel):
    """Manual contact handoff result."""

    success: bool
    lead_id: str | None = None
    emails_sent: bool = False
    crm_captured: bool = False
    crm_capture_id: str | None = None
    error: str | None = None


def _clean_contact_text(value: Any, limit: int = MAX_CONTACT_TEXT_CHARS) -> str:
    """Normalizes manual contact form text without accepting HTML markup."""
    text = str(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _valid_email(value: str) -> bool:
    """Returns whether a manually entered email address is usable."""
    return len(value) <= 254 and bool(EMAIL_RE.match(value))


def _valid_phone(value: str) -> bool:
    """Returns whether an optional phone number looks plausible."""
    if not value:
        return True
    digits = re.sub(r"\D", "", value)
    return bool(PHONE_RE.match(value)) and 6 <= len(digits) <= 20


def _parse_client_secret(data: dict[str, Any]) -> tuple[str, datetime]:
    """Extracts ephemeral client secret variants returned by OpenAI."""
    client_secret = data.get("client_secret")
    secret = data.get("value")
    expires_at = data.get("expires_at")

    if isinstance(client_secret, dict):
        secret = secret or client_secret.get("value")
        expires_at = expires_at or client_secret.get("expires_at")
    elif isinstance(client_secret, str):
        secret = secret or client_secret

    if not secret:
        raise HTTPException(status_code=502, detail="openai_secret_missing")

    if isinstance(expires_at, int):
        expires = datetime.fromtimestamp(expires_at, tz=timezone.utc)
    else:
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    return str(secret), expires


@router.post("/session", response_model=EphemeralVoiceSessionResponse)
async def create_ephemeral_voice_session(
    payload: EphemeralVoiceSessionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> EphemeralVoiceSessionResponse:
    """Creates an ephemeral OpenAI Realtime client secret for browser WebRTC."""
    settings = get_settings()
    if not origin_allowed(request):
        raise HTTPException(status_code=403, detail="Origin not allowed")
    if not payload.consent_granted:
        raise HTTPException(status_code=401, detail="Voice consent required")
    if not settings.enable_voice_sessions:
        raise HTTPException(status_code=403, detail="Voice is disabled")
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Voice provider is not configured")

    studio = await load_voice_studio(session, payload.studio)
    if not voice_enabled(studio):
        raise HTTPException(status_code=403, detail="Voice is disabled for this studio")
    conversation = await load_voice_conversation(session, studio, payload.visitor_id)
    conversation.channel = "voice"
    conversation.metadata_ = {
        **(conversation.metadata_ or {}),
        "voice_consent": {
            "version": payload.consent_version,
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "raw_audio_stored": False,
        },
        "address_mode": payload.address_mode,
    }
    voice_session_id = payload.session_id or f"voice_{uuid.uuid4()}"
    memory = MemoryManager(session)
    context = await memory.get_context(conversation.id, studio.id)
    config = realtime_session_config(
        studio,
        conversation,
        [],
        context.lead_summary,
        payload.address_mode,
    )
    profile = get_tenant_profile_for_studio(studio.slug)
    voice_agent = profile.live_voice_agent() if profile is not None else None
    config["tracing"] = {
        "workflow_name": f"live_voice_{studio.slug}",
        "group_id": str(conversation.id),
        "metadata": {
            "tenant_id": profile.tenant_id if profile is not None else studio.slug,
            "agent_profile_id": voice_agent.id
            if voice_agent is not None
            else "legacy-live-voice",
            "studio": studio.slug,
            "voice_session_id": voice_session_id,
            "consent_version": payload.consent_version,
            "origin": request.headers.get("origin", ""),
        },
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/realtime/client_secrets",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "OpenAI-Safety-Identifier": safety_identifier(
                    studio, payload.visitor_id
                ),
            },
            json={"session": config},
        )
    if response.status_code >= 400:
        log.warning(
            "voice.openai_client_secret_failed",
            status=response.status_code,
            request_id=response.headers.get("x-request-id", ""),
            body=response.text[:800],
            model=str(config["model"]),
            studio=studio.slug,
        )
        raise HTTPException(status_code=502, detail="openai_realtime_session_failed")

    client_secret, expires = _parse_client_secret(response.json())
    session.add(
        Event(
            studio_id=studio.id,
            type="voice_session_created",
            actor=f"voice:{payload.visitor_id}",
            payload={
                "conversation_id": str(conversation.id),
                "voice_session_id": voice_session_id,
                "consent_version": payload.consent_version,
                "raw_audio_stored": False,
                "model": str(config["model"]),
                "address_mode": payload.address_mode,
            },
        )
    )
    await session.commit()
    return EphemeralVoiceSessionResponse(
        client_secret=client_secret,
        expires_at=expires.isoformat(),
        model=str(config["model"]),
        voice=str(config["audio"]["output"]["voice"]),
        conversation_id=str(conversation.id),
        voice_session_id=voice_session_id,
    )


@router.post("/sessions/webrtc")
async def create_webrtc_voice_session(
    payload: VoiceSessionRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Creates a consent-gated OpenAI Realtime WebRTC session."""
    settings = get_settings()
    if not origin_allowed(request):
        raise HTTPException(status_code=403, detail="Origin not allowed")
    if not payload.consent_granted:
        raise HTTPException(status_code=401, detail="Voice consent required")
    if len(payload.client_sdp) > settings.max_voice_sdp_chars:
        raise HTTPException(status_code=413, detail="SDP payload is too large")
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Voice provider is not configured")

    studio = await load_voice_studio(session, payload.studio)
    if not voice_enabled(studio):
        raise HTTPException(status_code=403, detail="Voice is disabled for this studio")

    conversation = await load_voice_conversation(session, studio, payload.visitor_id)
    conversation.channel = "voice"
    conversation.metadata_ = {
        **(conversation.metadata_ or {}),
        "voice_consent": {
            "version": payload.consent_version,
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "raw_audio_stored": False,
        },
        "address_mode": payload.address_mode,
    }
    memory = MemoryManager(session)
    context = await memory.get_context(conversation.id, studio.id)
    call = await OpenAIRealtimeAdapter(settings).create_webrtc_call(
        client_sdp=payload.client_sdp,
        session_config=realtime_session_config(
            studio, conversation, [], context.lead_summary, payload.address_mode
        ),
        safety_identifier=safety_identifier(studio, payload.visitor_id),
    )
    voice_session_id = str(uuid.uuid4())
    session.add(
        Event(
            studio_id=studio.id,
            type="voice_session_requested",
            actor=f"voice:{payload.visitor_id}",
            payload={
                "conversation_id": str(conversation.id),
                "voice_session_id": voice_session_id,
                "provider_call_id": call.provider_call_id,
                "consent_version": payload.consent_version,
                "address_mode": payload.address_mode,
            },
        )
    )
    await session.commit()
    log.info(
        "voice.session_created",
        studio=studio.slug,
        conversation_id=str(conversation.id),
    )
    return {
        "conversation_id": str(conversation.id),
        "voice_session_id": voice_session_id,
        "sdp_answer": call.sdp_answer,
        "expires_at": call.expires_at.isoformat(),
        "config": {
            "transport": "webrtc",
            "raw_audio_stored": False,
            "max_session_seconds": settings.max_voice_session_seconds,
        },
    }


@router.post("/tool-calls")
async def handle_voice_tool_call(
    payload: VoiceToolCallRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Rejects legacy voice tool calls; contact data uses the secure form."""
    if not origin_allowed(request):
        raise HTTPException(status_code=403, detail="Origin not allowed")
    if not payload.consent_granted:
        raise HTTPException(status_code=401, detail="Voice consent required")
    raise HTTPException(
        status_code=410,
        detail="voice_tools_disabled_use_secure_contact_form",
    )


@router.post("/transcripts")
async def persist_voice_transcript(
    payload: VoiceTranscriptRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Persists a final voice transcript message after consent."""
    if not origin_allowed(request):
        raise HTTPException(status_code=403, detail="Origin not allowed")
    if not payload.consent_granted:
        raise HTTPException(status_code=401, detail="Voice consent required")
    studio = await load_voice_studio(session, payload.studio)
    conversation = await load_voice_conversation(
        session, studio, payload.visitor_id, payload.conversation_id
    )
    session.add(
        Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            role=payload.role,
            content=payload.text,
            tool_calls=[
                {"provider_event_id": payload.provider_event_id, "channel": "voice"}
            ],
        )
    )
    session.add(
        Event(
            studio_id=studio.id,
            type="voice_transcript_finalized",
            actor=f"voice:{payload.visitor_id}",
            payload={
                "conversation_id": str(conversation.id),
                "role": payload.role,
                "provider_event_id": payload.provider_event_id,
            },
        )
    )
    await session.commit()
    return {"status": "stored"}


@router.post("/transcript")
async def persist_voice_final_transcript(
    payload: VoiceFinalTranscriptRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | bool]:
    """Persists a final Realtime transcript event from the widget contract."""
    if not origin_allowed(request):
        raise HTTPException(status_code=403, detail="Origin not allowed")
    if not payload.consent_granted:
        raise HTTPException(status_code=401, detail="Voice consent required")
    studio = await load_voice_studio(session, payload.studio)
    conversation = await load_voice_conversation(
        session, studio, payload.visitor_id, payload.conversation_id
    )
    text = payload.transcript.strip()
    existing = (
        await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .where(Message.role == payload.role)
            .where(Message.content == text)
        )
    ).scalar_one_or_none()
    if existing:
        return {
            "stored": True,
            "conversation_id": str(conversation.id),
            "message_id": str(existing.id),
        }
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role=payload.role,
        content=text,
        tool_calls=[
            {
                "provider_event_id": payload.provider_event_id,
                "item_id": payload.item_id,
                "voice_session_id": payload.voice_session_id,
                "consent_version": payload.consent_version,
                "channel": "voice",
                "raw_audio_stored": False,
            }
        ],
    )
    session.add(message)
    session.add(
        Event(
            studio_id=studio.id,
            type="voice_transcript_finalized",
            actor=f"voice:{payload.visitor_id}",
            payload={
                "conversation_id": str(conversation.id),
                "message_id": str(message.id),
                "role": payload.role,
                "provider_event_id": payload.provider_event_id,
                "voice_session_id": payload.voice_session_id,
                "raw_audio_stored": False,
            },
        )
    )
    await session.commit()
    return {
        "stored": True,
        "conversation_id": str(conversation.id),
        "message_id": str(message.id),
    }


@router.post("/usage-events", response_model=VoiceUsageEventResponse)
async def persist_voice_usage_event(
    payload: VoiceUsageEventRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> VoiceUsageEventResponse:
    """Forwards Realtime token usage to the tenant CRM ledger."""
    if not origin_allowed(request):
        raise HTTPException(status_code=403, detail="Origin not allowed")
    if not payload.consent_granted:
        raise HTTPException(status_code=401, detail="Voice consent required")
    studio = await load_voice_studio(session, payload.studio)
    conversation = await load_voice_conversation(
        session, studio, payload.visitor_id, payload.conversation_id
    )
    provider_event_id = (
        payload.provider_response_id
        or payload.provider_event_id
        or f"{payload.voice_session_id}:{payload.event_type}"
    )
    normalized_usage = normalize_openai_usage(payload.usage)
    estimated_cost = estimate_openai_cost_usd(payload.model, normalized_usage)
    try:
        usage_id = await post_openai_usage_to_crm(
            source_event_id=provider_event_id,
            conversation_id=str(conversation.id),
            visitor_id=payload.visitor_id,
            channel_type="voice",
            component="realtime_session",
            model=payload.model,
            usage=payload.usage,
            metadata={
                "voice_session_id": payload.voice_session_id,
                "consent_version": payload.consent_version,
                "provider_event_id": payload.provider_event_id,
                "provider_response_id": payload.provider_response_id,
            },
        )
    except CrmHandoffNotConfiguredError as exc:
        raise HTTPException(
            status_code=503, detail="crm_usage_handoff_not_configured"
        ) from exc
    except CrmHandoffFailedError as exc:
        raise HTTPException(status_code=502, detail="crm_usage_handoff_failed") from exc
    await session.commit()
    return VoiceUsageEventResponse(
        stored=True,
        cost_event_id=usage_id,
        estimated_cost_usd=str(estimated_cost) if estimated_cost is not None else None,
    )


@router.post("/contact-handoff", response_model=VoiceContactHandoffResponse)
async def submit_voice_contact_handoff(
    payload: VoiceContactHandoffRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> VoiceContactHandoffResponse:
    """Forwards secure manual contact form data to the tenant CRM."""
    if not origin_allowed(request):
        raise HTTPException(status_code=403, detail="Origin not allowed")
    if not payload.consent_granted:
        raise HTTPException(status_code=401, detail="Voice consent required")
    studio = await load_voice_studio(session, payload.studio)
    conversation = await load_voice_conversation(
        session, studio, payload.visitor_id, payload.conversation_id
    )

    first_name = _clean_contact_text(payload.first_name, 80)
    last_name = _clean_contact_text(payload.last_name, 80)
    email = _clean_contact_text(payload.email, 254).lower()
    phone = _clean_contact_text(payload.phone, 50)
    best_reachability = _clean_contact_text(payload.best_reachability, 160)
    project_summary = _clean_contact_text(payload.project_summary, 1600)
    additional_notes = _clean_contact_text(payload.additional_notes, 1600)

    if not payload.contact_consent_confirmed:
        return VoiceContactHandoffResponse(
            success=False, error="contact_consent_required"
        )
    if len(first_name) < 2 or len(last_name) < 2:
        return VoiceContactHandoffResponse(success=False, error="invalid_name")
    if not _valid_email(email):
        return VoiceContactHandoffResponse(success=False, error="invalid_email")
    if not _valid_phone(phone):
        return VoiceContactHandoffResponse(success=False, error="invalid_phone")
    if not project_summary:
        project_summary = "Der Kunde wünscht eine Kontaktaufnahme zur Küchenberatung."
    uploads = await list_stored_project_uploads(
        session=session,
        studio_id=studio.id,
        conversation_id=conversation.id,
        limit=25,
    )
    project_uploads = [
        {
            "file_id": upload.file_id,
            "conversation_id": upload.conversation_id,
            "message_id": upload.message_id,
            "original_filename": upload.original_filename,
            "content_type": upload.content_type,
            "size_bytes": upload.size_bytes,
            "ai_analysis_completed": upload.ai_analysis_completed,
            "analysis_summary": upload.analysis_summary,
            "created_at": upload.created_at.isoformat(),
        }
        for upload in uploads
        if not upload.file_deleted
    ]

    crm_capture_id: str | None = None
    crm_error: str | None = None
    try:
        crm_capture_id = await post_voice_contact_to_crm(
            run_id=f"voice:{conversation.id}:{payload.voice_session_id}",
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            source_origin=str(request.headers.get("origin") or ""),
            privacy_accepted=payload.contact_consent_confirmed,
            project_summary=project_summary,
            additional_notes=additional_notes,
            best_reachability=best_reachability,
            conversation_id=str(conversation.id),
            project_uploads=project_uploads,
        )
    except CrmHandoffNotConfiguredError as exc:
        crm_error = "crm_handoff_not_configured"
        log.warning(
            "voice.crm_contact_handoff_not_configured",
            studio=studio.slug,
            conversation_id=str(conversation.id),
            error=str(exc),
        )
        raise HTTPException(status_code=503, detail=crm_error) from exc
    except CrmHandoffFailedError as exc:
        crm_error = "crm_handoff_failed"
        log.warning(
            "voice.crm_contact_handoff_failed",
            studio=studio.slug,
            conversation_id=str(conversation.id),
            error=str(exc),
        )
        raise HTTPException(status_code=502, detail=crm_error) from exc

    session.add(
        Event(
            studio_id=studio.id,
            type="voice_lead_handoff",
            actor=f"voice:{payload.visitor_id}",
            payload={
                "conversation_id": str(conversation.id),
                "voice_session_id": payload.voice_session_id,
                "emails_sent": False,
                "crm_captured": True,
                "crm_capture_id": crm_capture_id,
                "project_upload_count": len(project_uploads),
            },
        )
    )
    await session.commit()
    return VoiceContactHandoffResponse(
        success=True,
        lead_id=None,
        emails_sent=False,
        crm_captured=True,
        crm_capture_id=crm_capture_id,
        error=crm_error,
    )


@router.post("/session/end")
@router.post("/sessions/end")
async def end_voice_session(
    payload: VoiceEndRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Finalizes a voice conversation and writes the staff summary."""
    if not origin_allowed(request):
        raise HTTPException(status_code=403, detail="Origin not allowed")
    studio = await load_voice_studio(session, payload.studio)
    conversation = await load_voice_conversation(
        session, studio, payload.visitor_id, payload.conversation_id
    )
    await LisaAgent(session=session).finalize_conversation(conversation, studio)
    session.add(
        Event(
            studio_id=studio.id,
            type="voice_session_ended",
            actor=f"voice:{payload.visitor_id}",
            payload={
                "conversation_id": str(conversation.id),
                "reason": payload.close_reason,
            },
        )
    )
    await session.commit()
    return {"status": "ended"}
