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

from pathlib import Path
import hmac
import time
from uuid import UUID
from uuid import uuid4

import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    Query,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.config import get_settings
from src.api.services.crm_handoff import (
    CrmHandoffFailedError,
    CrmHandoffNotConfiguredError,
    post_openai_usage_to_crm,
)
from src.api.services.project_upload_runtime import (
    ALLOWED_TYPES,
    analyze_project_upload as _analyze_project_upload,
    enforce_upload_limits,
    get_or_create_conversation,
    load_studio,
    origin_allowed,
    safe_name,
    sniff_content_type,
    storage_path,
)
from src.api.services.project_uploads import list_stored_project_uploads, resolve_upload_path
from src.db.database import get_session
from src.db.models.event import Event
from src.db.models.message import Message
from src.tenants.registry import agent_display_name, get_tenant_profile_for_studio

router = APIRouter(prefix="/uploads", tags=["Uploads"])
log = structlog.get_logger()


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


def _upload_access_secret() -> str:
    settings = get_settings()
    return settings.crm_upload_access_secret or settings.crm_contact_handoff_secret


def _upload_access_signature(
    *, tenant_id: str, conversation_id: str, file_id: str, expires: int, secret: str
) -> str:
    payload = f"{tenant_id}\n{conversation_id}\n{file_id}\n{expires}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, "sha256").hexdigest()


def _verify_upload_access_signature(
    *, tenant_id: str, conversation_id: str, file_id: str, expires: int, signature: str
) -> None:
    secret = _upload_access_secret()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="upload_not_found"
        )
    now = int(time.time())
    if expires < now or expires > now + 3600:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="upload_link_expired"
        )
    expected = _upload_access_signature(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        file_id=file_id,
        expires=expires,
        secret=secret,
    )
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="upload_access_denied"
        )


@router.post("/project-file", response_model=ProjectUploadResponse)
async def upload_project_file(
    request: Request,
    studio: str = Form(..., min_length=1, max_length=100),
    visitor_id: str = Form(..., min_length=1, max_length=255),
    conversation_id: UUID | None = Form(default=None),
    consent_granted: bool = Form(...),
    consent_version: str = Form(..., min_length=1, max_length=80),
    ai_analysis_consent: bool = Form(False),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> ProjectUploadResponse:
    """Stores a consented project file upload and records it in the conversation."""
    settings = get_settings()
    if not origin_allowed(request.headers.get("origin")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="origin_not_allowed"
        )
    if not consent_granted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="consent_required"
        )
    if not ai_analysis_consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="upload_analysis_consent_required",
        )

    studio_row = await load_studio(session, studio)
    tenant_profile = get_tenant_profile_for_studio(studio_row.slug)
    if tenant_profile is not None:
        upload_policy = tenant_profile.upload_policy
        if upload_policy is None or not upload_policy.enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="uploads_disabled"
            )
        if content_type := file.content_type:
            if (
                content_type in ALLOWED_TYPES
                and content_type not in upload_policy.allowed_content_types
            ):
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="unsupported_file_type",
                )
    conversation = await get_or_create_conversation(
        session, studio_row, visitor_id, conversation_id
    )
    await enforce_upload_limits(
        session=session,
        conversation=conversation,
        visitor_id=visitor_id,
    )
    data = await file.read(settings.max_upload_file_bytes + 1)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="empty_file"
        )
    if len(data) > settings.max_upload_file_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="file_too_large",
        )

    content_type = sniff_content_type(data, file.content_type)
    if tenant_profile is not None and tenant_profile.upload_policy is not None:
        if content_type not in tenant_profile.upload_policy.allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="unsupported_file_type",
            )
    extension = ALLOWED_TYPES[content_type]
    original_name = safe_name(file.filename)
    absolute_path, relative_path = storage_path(
        studio_slug=studio_row.slug,
        conversation_id=str(conversation.id),
        extension=extension,
    )
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(data)

    analysis_summary: str | None = None
    analysis_usage: dict | None = None
    analysis_model: str | None = None
    analysis_error: str | None = None
    upload_agent_name = agent_display_name(studio_row.slug, fallback="Live Voice Agent")
    try:
        analysis_result = await _analyze_project_upload(
            content_type=content_type,
            data=data,
            filename=original_name,
            agent_name=upload_agent_name,
        )
        if analysis_result is not None:
            analysis_summary = analysis_result.summary
            analysis_usage = analysis_result.usage
            analysis_model = analysis_result.model
    except Exception as exc:
        analysis_error = "analysis_failed"
        log.warning(
            "upload.analysis_failed",
            error=str(exc),
            conversation_id=str(conversation.id),
        )

    content = (
        f"Der Kunde hat eine Projektdatei hochgeladen: {original_name} "
        f"({content_type}, {len(data)} Bytes)."
    )
    if analysis_summary:
        content += (
            f"\nKI-Dateizusammenfassung für {upload_agent_name}: {analysis_summary}"
        )
    elif content_type == "application/pdf":
        content += (
            "\nHinweis: Das PDF wurde gespeichert und kann vom Team geprüft werden."
        )

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
                "analysis_summary": analysis_summary or "",
                "analysis_error": analysis_error,
                "consent_version": consent_version,
            }
        ],
    )
    session.add(message)
    await session.flush()
    if analysis_usage is not None and analysis_model is not None:
        try:
            await post_openai_usage_to_crm(
                source_event_id=str(message.id),
                conversation_id=str(conversation.id),
                visitor_id=visitor_id,
                channel_type="upload",
                component="project_upload_analysis",
                model=analysis_model,
                usage=analysis_usage,
                metadata={
                    "file_id": Path(relative_path).stem,
                    "original_filename": original_name,
                    "content_type": content_type,
                    "size_bytes": len(data),
                    "analysis_error": analysis_error,
                },
            )
        except (CrmHandoffNotConfiguredError, CrmHandoffFailedError) as exc:
            log.warning(
                "upload.crm_usage_handoff_failed",
                conversation_id=str(conversation.id),
                message_id=str(message.id),
                error=str(exc),
            )
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
            f"Die Datei wurde hochgeladen und für {upload_agent_name} zusammengefasst."
            if analysis_summary
            else "Die Datei wurde hochgeladen und für die Beratung gespeichert."
        ),
    )


@router.get("/project-file/{file_id}/content")
async def download_project_file(
    file_id: str,
    tenant_id: str = Query(..., min_length=1, max_length=100),
    conversation_id: UUID = Query(...),
    expires: int = Query(...),
    signature: str = Query(..., min_length=64, max_length=64),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    """Streams a CRM-authorized project upload after tenant-scoped HMAC validation."""
    if not file_id or not all(c.isalnum() or c == "-" for c in file_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="upload_not_found"
        )
    _verify_upload_access_signature(
        tenant_id=tenant_id,
        conversation_id=str(conversation_id),
        file_id=file_id,
        expires=expires,
        signature=signature,
    )

    studio_row = await load_studio(session, tenant_id)
    uploads = await list_stored_project_uploads(
        session=session,
        studio_id=studio_row.id,
        conversation_id=conversation_id,
        limit=100,
    )
    upload = next(
        (
            stored_upload
            for stored_upload in uploads
            if stored_upload.file_id == file_id and not stored_upload.file_deleted
        ),
        None,
    )
    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="upload_not_found"
        )
    try:
        path = resolve_upload_path(upload.relative_path)
    except ValueError as exc:
        log.warning("upload.access_invalid_path", file_id=file_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="upload_not_found"
        ) from exc
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="upload_not_found"
        )

    session.add(
        Event(
            studio_id=studio_row.id,
            type="project_file_accessed",
            actor="crm:file-view",
            payload={
                "conversation_id": str(conversation_id),
                "message_id": upload.message_id,
                "file_id": upload.file_id,
                "original_filename": upload.original_filename,
                "content_type": upload.content_type,
                "size_bytes": upload.size_bytes,
            },
        )
    )
    await session.commit()

    return FileResponse(
        path,
        media_type=upload.content_type,
        filename=upload.original_filename,
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
