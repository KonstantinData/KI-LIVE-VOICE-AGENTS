"""
Voice Session Services
======================
What:    Shared session helpers for browser live voice routes.
Does:    Validates origins and feature flags, loads tenants, creates conversations, builds provider config.
Why:     Voice routes need reusable tenant-safe orchestration without oversized route files.
Who:     FastAPI voice routes.
Depends: fastapi, sqlalchemy, src.agents.lisa, src.api.config, src.tenants
"""

import hashlib
import uuid
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.lisa.voice_prompt import build_lisa_voice_prompt
from src.api.config import get_settings
from src.db.models.conversation import Conversation
from src.db.models.studio import Studio
from src.tenants.registry import get_tenant_profile_for_studio


def origin_allowed(request: Request) -> bool:
    """Checks request origin against configured frontend origins."""
    settings = get_settings()
    origin = request.headers.get("origin")
    if origin is None:
        return settings.app_env != "production"
    return origin in settings.cors_origins


def voice_enabled(studio: Studio) -> bool:
    """Checks the global and studio-level voice kill switches."""
    profile = get_tenant_profile_for_studio(studio.slug)
    if profile is not None:
        try:
            voice_agent = profile.live_voice_agent()
        except ValueError:
            return False
        return (
            get_settings().enable_voice_sessions
            and profile.public_widget.voice_enabled
            and voice_agent.enabled
        )
    config = studio.config or {}
    return bool(config.get("voice_enabled")) and get_settings().enable_voice_sessions


def safety_identifier(studio: Studio, visitor_id: str) -> str:
    """Returns a stable privacy-preserving provider safety identifier."""
    return hashlib.sha256(f"{studio.id}:{visitor_id}".encode("utf-8")).hexdigest()


async def load_voice_studio(session: AsyncSession, slug: str) -> Studio:
    """Loads an active studio for public voice routes."""
    result = await session.execute(select(Studio).where(Studio.slug == slug))
    studio = result.scalar_one_or_none()
    if studio is None or not studio.is_active:
        raise HTTPException(status_code=404, detail="Studio not found")
    return studio


async def load_voice_conversation(
    session: AsyncSession,
    studio: Studio,
    visitor_id: str,
    conversation_id: uuid.UUID | None = None,
) -> Conversation:
    """Loads or creates an active tenant-bound voice conversation."""
    query = select(Conversation).where(Conversation.studio_id == studio.id)
    if conversation_id:
        query = query.where(Conversation.id == conversation_id).where(
            Conversation.visitor_id == visitor_id
        )
    else:
        query = query.where(Conversation.visitor_id == visitor_id).where(
            Conversation.status == "active"
        )
    result = await session.execute(query)
    conversation = result.scalar_one_or_none()
    if conversation:
        return conversation
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id=visitor_id,
        channel="voice",
        status="active",
        metadata_={},
    )
    session.add(conversation)
    await session.flush()
    return conversation


def realtime_session_config(
    studio: Studio,
    conversation: Conversation,
    tools: list[dict],
    lead_summary: str | None,
    address_mode: str = "sie",
) -> dict[str, Any]:
    """Builds the OpenAI Realtime session configuration for a tenant live voice agent."""
    settings = get_settings()
    profile = get_tenant_profile_for_studio(studio.slug)
    voice_agent = profile.live_voice_agent() if profile is not None else None
    model = voice_agent.model if voice_agent is not None else settings.openai_realtime_model
    voice = voice_agent.voice if voice_agent is not None else settings.openai_realtime_voice
    agent_name = (
        voice_agent.display_name
        if voice_agent is not None
        else str((studio.config or {}).get("agent_name") or "Live Voice Agent")
    )
    config: dict[str, Any] = {
        "type": "realtime",
        "model": model,
        "instructions": build_lisa_voice_prompt(
            studio,
            lead_summary,
            address_mode,
            agent_display_name=agent_name,
        ),
        "audio": {
            "output": {"voice": voice},
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
    }
    if tools:
        config["tools"] = tools
        config["tool_choice"] = "auto"
    return config
