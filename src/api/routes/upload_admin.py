"""
Project Upload Admin Routes
===========================
What:    Protected dashboard routes for private project upload files.
Does:    Lists upload metadata and serves private files to authenticated tenants.
Why:     Upload files must remain private while still being available to staff.
Who:     Dashboard users with tenant-authenticated access.
Depends: fastapi, pydantic, src.api.deps, src.api.services.project_uploads
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.api.deps import CurrentStudio, DBSession
from src.api.services.project_uploads import (
    list_stored_project_uploads,
    resolve_upload_path,
)

router = APIRouter(prefix="/uploads", tags=["Uploads"])


class ProjectFileResponse(BaseModel):
    """Admin-safe metadata for one private project upload."""

    file_id: str
    conversation_id: str
    message_id: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    ai_analysis_completed: bool
    file_deleted: bool


def _project_file_response(upload) -> ProjectFileResponse:
    return ProjectFileResponse(
        file_id=upload.file_id,
        conversation_id=upload.conversation_id,
        message_id=upload.message_id,
        filename=upload.original_filename,
        content_type=upload.content_type,
        size_bytes=upload.size_bytes,
        created_at=upload.created_at,
        ai_analysis_completed=upload.ai_analysis_completed,
        file_deleted=upload.file_deleted,
    )


@router.get("/project-files", response_model=list[ProjectFileResponse])
async def list_project_files(
    studio: CurrentStudio,
    session: DBSession,
    conversation_id: UUID | None = None,
) -> list[ProjectFileResponse]:
    """Lists private project uploads for the authenticated tenant."""
    uploads = await list_stored_project_uploads(
        session=session,
        studio_id=studio.id,
        conversation_id=conversation_id,
    )
    return [_project_file_response(upload) for upload in uploads]


@router.get("/project-files/{file_id}")
async def download_project_file(
    file_id: str,
    studio: CurrentStudio,
    session: DBSession,
) -> FileResponse:
    """Downloads a private project upload for the authenticated tenant."""
    uploads = await list_stored_project_uploads(session=session, studio_id=studio.id)
    upload = next((item for item in uploads if item.file_id == file_id), None)
    if upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file_not_found")
    if upload.file_deleted:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="file_deleted")

    try:
        path = resolve_upload_path(upload.relative_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="invalid_stored_file_path",
        ) from exc
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="file_not_found")

    return FileResponse(
        path=path,
        media_type=upload.content_type,
        filename=upload.original_filename,
        headers={"Cache-Control": "private, no-store"},
    )
