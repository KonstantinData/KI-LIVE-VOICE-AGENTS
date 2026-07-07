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
from html import escape
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
from src.api.services.email_service import EmailService, EmailServiceDisabledError
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
from src.db.models.lead import Lead
from src.db.models.message import Message
from src.tenants.registry import agent_display_name, get_tenant_profile_for_studio

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


def _lead_notification_email(studio) -> str:
    """Returns the configured staff notification mailbox for lead handoff."""
    config = studio.config or {}
    return str(
        config.get("lead_notification_email")
        or config.get("contact_email")
        or "beratung@mein-kuechenexperte.de"
    )


def _summary_items(text: str) -> list[str]:
    """Splits a customer-approved project summary into compact email bullets."""
    parts = [
        _clean_contact_text(part, 240)
        for part in re.split(r"[\n;]+", text)
        if _clean_contact_text(part, 240)
    ]
    if not parts and text:
        parts = [_clean_contact_text(text, 480)]
    unique: list[str] = []
    seen: set[str] = set()
    for part in parts:
        key = part.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(part)
        if len(unique) >= 7:
            break
    return unique or ["Der Kunde wünscht eine Kontaktaufnahme zur Küchenberatung."]


def _html_list(items: list[str]) -> str:
    """Formats escaped bullet points for email HTML."""
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def _customer_email_html(
    *,
    first_name: str,
    last_name: str,
    summary_items: list[str],
    best_reachability: str,
) -> str:
    """Builds the customer confirmation email."""
    reachability_html = (
        f"<p><strong>Beste Erreichbarkeit:</strong> {escape(best_reachability)}</p>"
        if best_reachability
        else ""
    )
    return f"""
<p>Hallo {escape(first_name)} {escape(last_name)},</p>
<p>vielen Dank für Ihr Interesse an Mein Küchenexperte. Ihre Anfrage ist bei uns eingegangen.</p>
<p><strong>Zusammenfassung unseres Gesprächs:</strong></p>
{_html_list(summary_items)}
{reachability_html}
<p>Wir melden uns zeitnah bei Ihnen, um die nächsten Schritte für Ihr Küchenprojekt zu besprechen.</p>
<p>Mit freundlichen Grüßen<br>Mein Küchenexperte</p>
"""


def _admin_email_html(
    *,
    studio,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    best_reachability: str,
    summary_items: list[str],
    additional_notes: str,
    conversation_id: uuid.UUID,
    voice_session_id: str,
    agent_name: str,
) -> str:
    """Builds the internal lead handoff email."""
    phone_html = f"<li>Telefon: {escape(phone)}</li>" if phone else ""
    reachability_html = (
        f"<li>Beste Erreichbarkeit: {escape(best_reachability)}</li>"
        if best_reachability
        else ""
    )
    notes_html = (
        f"<p><strong>Zusätzliche Hinweise:</strong><br>{escape(additional_notes)}</p>"
        if additional_notes
        else ""
    )
    return f"""
<p><strong>Neue {escape(agent_name)}-Kundenanfrage für {escape(studio.name or studio.slug)}</strong></p>
<p><strong>Kontaktdaten</strong></p>
<ul>
  <li>Name: {escape(first_name)} {escape(last_name)}</li>
  <li>E-Mail: <a href="mailto:{escape(email)}">{escape(email)}</a></li>
  {phone_html}
  {reachability_html}
</ul>
<p><strong>Gesprächszusammenfassung</strong></p>
{_html_list(summary_items)}
{notes_html}
<p style="font-size:12px;color:#666">
Conversation: {escape(str(conversation_id))}<br>
Voice Session: {escape(voice_session_id)}<br>
Quelle: {escape(agent_name)} Voice Widget
</p>
"""


async def _upsert_contact_lead(
    *,
    session: AsyncSession,
    studio,
    visitor_id: str,
    conversation,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    best_reachability: str,
    project_summary: str,
    additional_notes: str,
    consent_version: str,
) -> Lead:
    """Creates or updates the lead from the manual secure contact form."""
    lead = (
        await session.execute(
            select(Lead)
            .where(Lead.studio_id == studio.id)
            .where(Lead.visitor_id == visitor_id)
        )
    ).scalar_one_or_none()
    if lead is None:
        lead = Lead(
            id=uuid.uuid4(),
            studio_id=studio.id,
            visitor_id=visitor_id,
            status="qualified",
            score=70.0,
            source_channel="voice_widget",
            profile={},
        )
        session.add(lead)

    full_name = f"{first_name} {last_name}".strip()
    profile = dict(lead.profile or {})
    profile.update({
        "first_name": first_name,
        "last_name": last_name,
        "name": full_name,
        "email": email,
        "phone": phone,
        "best_reachability": best_reachability,
        "project_summary": project_summary,
        "additional_notes": additional_notes,
        "contact_consent_confirmed": True,
        "contact_consent_version": consent_version,
        "handoff_channel": "secure_widget_form",
        "handoff_at": datetime.now(timezone.utc).isoformat(),
    })
    lead.name = full_name
    lead.email = email
    lead.phone = phone or None
    lead.summary = project_summary
    lead.profile = profile
    lead.score = max(float(lead.score or 0), 85.0)
    lead.status = "qualified"
    if conversation.lead_id is None:
        conversation.lead_id = lead.id
    return lead


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
    config = realtime_session_config(studio, conversation, [], None, payload.address_mode)
    profile = get_tenant_profile_for_studio(studio.slug)
    voice_agent = profile.live_voice_agent() if profile is not None else None
    config["tracing"] = {
        "workflow_name": f"live_voice_{studio.slug}",
        "group_id": str(conversation.id),
        "metadata": {
            "tenant_id": profile.tenant_id if profile is not None else studio.slug,
            "agent_profile_id": voice_agent.id if voice_agent is not None else "legacy-live-voice",
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
                "OpenAI-Safety-Identifier": safety_identifier(studio, payload.visitor_id),
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
    session.add(Event(
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
    ))
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
    session.add(Event(
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
    ))
    await session.commit()
    log.info("voice.session_created", studio=studio.slug, conversation_id=str(conversation.id))
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
    session.add(Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role=payload.role,
        content=payload.text,
        tool_calls=[{"provider_event_id": payload.provider_event_id, "channel": "voice"}],
    ))
    session.add(Event(
        studio_id=studio.id,
        type="voice_transcript_finalized",
        actor=f"voice:{payload.visitor_id}",
        payload={
            "conversation_id": str(conversation.id),
            "role": payload.role,
            "provider_event_id": payload.provider_event_id,
        },
    ))
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
    session.add(Event(
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
    ))
    await session.commit()
    return {
        "stored": True,
        "conversation_id": str(conversation.id),
        "message_id": str(message.id),
    }


@router.post("/contact-handoff", response_model=VoiceContactHandoffResponse)
async def submit_voice_contact_handoff(
    payload: VoiceContactHandoffRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> VoiceContactHandoffResponse:
    """Stores secure manual contact form data without routing it through voice."""
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
        return VoiceContactHandoffResponse(success=False, error="contact_consent_required")
    if len(first_name) < 2 or len(last_name) < 2:
        return VoiceContactHandoffResponse(success=False, error="invalid_name")
    if not _valid_email(email):
        return VoiceContactHandoffResponse(success=False, error="invalid_email")
    if not _valid_phone(phone):
        return VoiceContactHandoffResponse(success=False, error="invalid_phone")
    if not project_summary:
        project_summary = "Der Kunde wünscht eine Kontaktaufnahme zur Küchenberatung."

    lead = await _upsert_contact_lead(
        session=session,
        studio=studio,
        visitor_id=payload.visitor_id,
        conversation=conversation,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        best_reachability=best_reachability,
        project_summary=project_summary,
        additional_notes=additional_notes,
        consent_version=payload.consent_version,
    )
    await session.flush()

    summary_items = _summary_items(project_summary)
    handoff_agent_name = agent_display_name(studio.slug, fallback="Live Voice Agent")
    emails_sent = False
    email_error: str | None = None
    try:
        email_service = EmailService()
        await email_service.send(
            to=email,
            subject="Ihre Anfrage bei Mein Küchenexperte",
            html=_customer_email_html(
                first_name=first_name,
                last_name=last_name,
                summary_items=summary_items,
                best_reachability=best_reachability,
            ),
        )
        await email_service.send(
            to=_lead_notification_email(studio),
            subject=f"Neue {handoff_agent_name}-Anfrage: {first_name} {last_name}",
            html=_admin_email_html(
                studio=studio,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                best_reachability=best_reachability,
                summary_items=summary_items,
                additional_notes=additional_notes,
                conversation_id=conversation.id,
                voice_session_id=payload.voice_session_id,
                agent_name=handoff_agent_name,
            ),
        )
        emails_sent = True
    except EmailServiceDisabledError:
        email_error = "email_disabled"
    except Exception:
        email_error = "email_delivery_failed"

    session.add(Event(
        studio_id=studio.id,
        type="voice_lead_handoff",
        actor=f"voice:{payload.visitor_id}",
        payload={
            "conversation_id": str(conversation.id),
            "lead_id": str(lead.id),
            "voice_session_id": payload.voice_session_id,
            "emails_sent": emails_sent,
            "email_error": email_error,
        },
    ))
    await session.commit()
    return VoiceContactHandoffResponse(
        success=True,
        lead_id=str(lead.id),
        emails_sent=emails_sent,
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
    session.add(Event(
        studio_id=studio.id,
        type="voice_session_ended",
        actor=f"voice:{payload.visitor_id}",
        payload={"conversation_id": str(conversation.id), "reason": payload.close_reason},
    ))
    await session.commit()
    return {"status": "ended"}
