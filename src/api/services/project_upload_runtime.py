"""Runtime helpers for public project upload validation, storage, and analysis."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from uuid import UUID, uuid4

import structlog
from fastapi import HTTPException, status
from openai import AsyncOpenAI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.config import get_settings
from src.api.services.project_uploads import analyze_pdf_upload
from src.db.models.conversation import Conversation
from src.db.models.message import Message
from src.db.models.studio import Studio

log = structlog.get_logger()

ALLOWED_TYPES = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}
IMAGE_TYPES = {"image/jpeg", "image/png"}


def origin_allowed(origin: str | None) -> bool:
    """Returns whether an upload request origin is allowed."""
    settings = get_settings()
    if origin is None:
        return settings.app_env != "production"
    return origin.rstrip("/") in _allowed_origins()


def safe_name(filename: str | None) -> str:
    """Normalizes a customer-provided filename for metadata storage."""
    name = Path(filename or "upload").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return name[:120] or "upload"


def sniff_content_type(data: bytes, declared_type: str | None) -> str:
    """Detects the real supported content type from file bytes."""
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if declared_type in ALLOWED_TYPES:
        return declared_type
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="unsupported_file_type",
    )


def storage_path(*, studio_slug: str, conversation_id: str, extension: str) -> tuple[Path, str]:
    """Builds the private absolute and relative storage paths for an upload."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    file_id = str(uuid4())
    relative_path = Path(
        studio_slug,
        f"{now.year:04d}",
        f"{now.month:02d}",
        conversation_id,
        f"{file_id}{extension}",
    )
    return (
        Path(settings.upload_storage_dir) / relative_path,
        str(relative_path).replace("\\", "/"),
    )


async def load_studio(session: AsyncSession, slug: str) -> Studio:
    """Loads an active studio by slug or raises a public 404."""
    result = await session.execute(select(Studio).where(Studio.slug == slug))
    studio = result.scalar_one_or_none()
    if studio is None or not studio.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="studio_not_found")
    return studio


async def get_or_create_conversation(
    session: AsyncSession,
    studio: Studio,
    visitor_id: str,
    conversation_id: UUID | None = None,
) -> Conversation:
    """Loads an explicit conversation or reuses/creates an active one."""
    if conversation_id is not None:
        result = await session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.studio_id == studio.id)
            .where(Conversation.visitor_id == visitor_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="conversation_not_found",
            )
        return conversation

    result = await session.execute(
        select(Conversation)
        .where(Conversation.studio_id == studio.id)
        .where(Conversation.visitor_id == visitor_id)
        .where(Conversation.status == "active")
    )
    conversation = result.scalar_one_or_none()
    if conversation is not None:
        return conversation

    conversation = Conversation(
        studio_id=studio.id,
        visitor_id=visitor_id,
        channel="widget",
        status="active",
        metadata_={},
    )
    session.add(conversation)
    await session.flush()
    await session.refresh(conversation)
    return conversation


async def enforce_upload_limits(
    *,
    session: AsyncSession,
    conversation: Conversation,
    visitor_id: str,
) -> None:
    """Applies per-visitor and per-conversation upload limits."""
    settings = get_settings()
    hour_start = datetime.now(timezone.utc) - timedelta(hours=1)
    visitor_count = (
        await session.execute(
            select(func.count(Message.id))
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.visitor_id == visitor_id)
            .where(Message.created_at >= hour_start)
            .where(Message.content.like("Der Kunde hat eine Projektdatei hochgeladen:%"))
        )
    ).scalar_one()
    if int(visitor_count or 0) >= settings.max_uploads_per_visitor_hour:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="upload_rate_limit_exceeded",
        )

    conversation_count = (
        await session.execute(
            select(func.count(Message.id))
            .where(Message.conversation_id == conversation.id)
            .where(Message.content.like("Der Kunde hat eine Projektdatei hochgeladen:%"))
        )
    ).scalar_one()
    if int(conversation_count or 0) >= settings.max_uploads_per_conversation:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="conversation_upload_limit_exceeded",
        )


async def analyze_project_upload(
    *,
    content_type: str,
    data: bytes,
    filename: str,
    agent_name: str,
) -> str | None:
    """Returns a privacy-minimized OpenAI summary for supported uploads."""
    if content_type in IMAGE_TYPES:
        return await _analyze_image_upload(
            content_type=content_type,
            data=data,
            filename=filename,
            agent_name=agent_name,
        )
    if content_type == "application/pdf":
        return await analyze_pdf_upload(data=data, filename=filename, agent_name=agent_name)
    return None


def _allowed_origins() -> set[str]:
    settings = get_settings()
    origins = {origin.rstrip("/") for origin in settings.cors_origins if origin}
    origins.update({
        settings.website_url.rstrip("/"),
        settings.dashboard_url.rstrip("/"),
        settings.widget_url.rstrip("/"),
    })
    return {origin for origin in origins if origin}


async def _analyze_image_upload(
    *,
    content_type: str,
    data: bytes,
    filename: str,
    agent_name: str,
) -> str | None:
    settings = get_settings()
    if (
        not settings.enable_upload_ai_analysis
        or not settings.openai_api_key
        or content_type not in IMAGE_TYPES
    ):
        return None

    data_url = f"data:{content_type};base64,{base64.b64encode(data).decode('ascii')}"
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.openai_chat_model,
        max_tokens=450,
        messages=[
            {
                "role": "system",
                "content": (
                    "Du analysierst Kundenfotos für eine Küchenberatung. "
                    "Beschreibe nur sichtbare, nicht-sensitive Projektdetails: "
                    "Raumwirkung, Küchenform, Anschlüsse soweit erkennbar, "
                    "Stauraum, Arbeitsfläche, Licht, mögliche Planungsfragen. "
                    "Keine Personen identifizieren, keine privaten Details ableiten."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Datei: {filename}. Fasse die für {agent_name} relevanten "
                            "Küchenplanungsdetails kurz auf Deutsch zusammen."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    )
    return (response.choices[0].message.content or "").strip() or None
