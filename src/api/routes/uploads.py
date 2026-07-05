"""
Project Upload Routes
=====================
What:    Public widget upload endpoint for customer project files.
Does:    Validates PDF/PNG/JPEG uploads, stores them privately, and records
         upload context in the active conversation.
Why:     KEA needs photos or plans to discuss existing room situations without
         exposing customer files as public assets.
Who:     The embeddable widget calls POST /uploads/project-file after consent.
Depends: fastapi, sqlalchemy, openai, src.api.config, src.db.models
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.config import get_settings
from src.db.database import get_session
from src.db.models.conversation import Conversation
from src.db.models.event import Event
from src.db.models.message import Message
from src.db.models.studio import Studio

router = APIRouter(prefix="/uploads", tags=["Uploads"])
log = structlog.get_logger()

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}
IMAGE_TYPES = {"image/jpeg", "image/png"}


class ProjectUploadResponse(BaseModel):
    """Upload response returned to the widget."""

    success: bool
    conversation_id: str
    file_id: str
    filename: str
    content_type: str
    size_bytes: int
    analysis_summary: str | None = None
    message: str


def _allowed_origins() -> set[str]:
    settings = get_settings()
    origins = {origin.rstrip("/") for origin in settings.cors_origins if origin}
    origins.update({
        settings.website_url.rstrip("/"),
        settings.dashboard_url.rstrip("/"),
        settings.widget_url.rstrip("/"),
    })
    return {origin for origin in origins if origin}


def _origin_allowed(origin: str | None) -> bool:
    settings = get_settings()
    if origin is None:
        return settings.app_env != "production"
    return origin.rstrip("/") in _allowed_origins()


def _safe_name(filename: str | None) -> str:
    name = Path(filename or "upload").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return name[:120] or "upload"


def _sniff_content_type(data: bytes, declared_type: str | None) -> str:
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


def _storage_path(
    *,
    studio_slug: str,
    conversation_id: str,
    extension: str,
) -> tuple[Path, str]:
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
    return Path(settings.upload_storage_dir) / relative_path, str(relative_path).replace("\\", "/")


async def _load_studio(session: AsyncSession, slug: str) -> Studio:
    result = await session.execute(select(Studio).where(Studio.slug == slug))
    studio = result.scalar_one_or_none()
    if studio is None or not studio.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="studio_not_found")
    return studio


async def _get_or_create_conversation(
    session: AsyncSession,
    studio: Studio,
    visitor_id: str,
) -> Conversation:
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


async def _enforce_upload_limits(
    *,
    session: AsyncSession,
    conversation: Conversation,
    visitor_id: str,
) -> None:
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


async def _analyze_image_upload(
    *,
    content_type: str,
    data: bytes,
    filename: str,
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
                            f"Datei: {filename}. Fasse die für KEA relevanten "
                            "Küchenplanungsdetails kurz auf Deutsch zusammen."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    )
    return (response.choices[0].message.content or "").strip() or None


@router.post("/project-file", response_model=ProjectUploadResponse)
async def upload_project_file(
    request: Request,
    studio: str = Form(..., min_length=1, max_length=100),
    visitor_id: str = Form(..., min_length=1, max_length=255),
    consent_granted: bool = Form(...),
    consent_version: str = Form(..., min_length=1, max_length=80),
    ai_analysis_consent: bool = Form(False),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> ProjectUploadResponse:
    """Stores a consented project file upload and records it in the conversation."""
    settings = get_settings()
    if not _origin_allowed(request.headers.get("origin")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="origin_not_allowed")
    if not consent_granted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="consent_required")
    if not ai_analysis_consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="upload_analysis_consent_required",
        )

    studio_row = await _load_studio(session, studio)
    conversation = await _get_or_create_conversation(session, studio_row, visitor_id)
    await _enforce_upload_limits(
        session=session,
        conversation=conversation,
        visitor_id=visitor_id,
    )

    data = await file.read(settings.max_upload_file_bytes + 1)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty_file")
    if len(data) > settings.max_upload_file_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="file_too_large")

    content_type = _sniff_content_type(data, file.content_type)
    extension = ALLOWED_TYPES[content_type]
    original_name = _safe_name(file.filename)
    absolute_path, relative_path = _storage_path(
        studio_slug=studio_row.slug,
        conversation_id=str(conversation.id),
        extension=extension,
    )
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(data)

    analysis_summary: str | None = None
    analysis_error: str | None = None
    try:
        analysis_summary = await _analyze_image_upload(
            content_type=content_type,
            data=data,
            filename=original_name,
        )
    except Exception as exc:
        analysis_error = "analysis_failed"
        log.warning("upload.analysis_failed", error=str(exc), conversation_id=str(conversation.id))

    content = (
        f"Der Kunde hat eine Projektdatei hochgeladen: {original_name} "
        f"({content_type}, {len(data)} Bytes)."
    )
    if analysis_summary:
        content += f"\nKI-Dateizusammenfassung für die Beratung: {analysis_summary}"
    elif content_type == "application/pdf":
        content += "\nHinweis: Das PDF wurde gespeichert und kann vom Team geprüft werden."

    message = Message(
        id=uuid4(),
        conversation_id=conversation.id,
        role="user",
        content=content,
        tool_calls=[
            {
                "type": "project_upload",
                "file_id": Path(relative_path).stem,
                "original_filename": original_name,
                "content_type": content_type,
                "size_bytes": len(data),
                "relative_path": relative_path,
                "ai_analysis_requested": ai_analysis_consent,
                "ai_analysis_completed": bool(analysis_summary),
                "analysis_error": analysis_error,
                "consent_version": consent_version,
            }
        ],
    )
    session.add(message)
    session.add(
        Event(
            studio_id=studio_row.id,
            type="project_file_uploaded",
            actor=f"visitor:{visitor_id}",
            payload={
                "conversation_id": str(conversation.id),
                "message_id": str(message.id),
                "original_filename": original_name,
                "content_type": content_type,
                "size_bytes": len(data),
                "relative_path": relative_path,
                "ai_analysis_completed": bool(analysis_summary),
            },
        )
    )
    await session.commit()

    return ProjectUploadResponse(
        success=True,
        conversation_id=str(conversation.id),
        file_id=Path(relative_path).stem,
        filename=original_name,
        content_type=content_type,
        size_bytes=len(data),
        analysis_summary=analysis_summary,
        message=(
            "Die Datei wurde hochgeladen und für KEA zusammengefasst."
            if analysis_summary
            else "Die Datei wurde hochgeladen und für die Beratung gespeichert."
        ),
    )
