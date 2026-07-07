"""
What: Shared helpers for stored customer project uploads.
Does: Parses upload metadata, resolves private paths, extracts PDF text, redacts contact data, and deletes expired files.
Why: Upload download, analysis, and retention need tenant-safe file handling outside the public upload route.
Who: Upload routes and scheduler maintenance jobs.
Depends: pathlib, sqlalchemy, openai, src.api.config, src.db.models
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import base64
import re

import structlog
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.config import get_settings
from src.db.models.conversation import Conversation
from src.db.models.message import Message

log = structlog.get_logger()

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s()./-]{6,}\d)(?!\w)")


@dataclass(frozen=True)
class StoredProjectUpload:
    """Metadata for a project upload stored in a message tool call."""

    file_id: str
    conversation_id: str
    message_id: str
    original_filename: str
    content_type: str
    size_bytes: int
    relative_path: str
    created_at: datetime
    ai_analysis_completed: bool
    file_deleted: bool = False


def redact_contact_details(text: str) -> str:
    """Removes direct contact data before text is sent to AI providers."""
    redacted = EMAIL_RE.sub("[email-redacted]", text)
    return PHONE_RE.sub("[phone-redacted]", redacted)


def extract_uploads_from_message(message: Message) -> list[StoredProjectUpload]:
    """Returns project upload metadata embedded in one message."""
    uploads: list[StoredProjectUpload] = []
    tool_calls = message.tool_calls or []
    if not isinstance(tool_calls, list):
        return uploads

    for call in tool_calls:
        if not isinstance(call, dict) or call.get("type") != "project_upload":
            continue
        file_id = str(call.get("file_id") or "")
        relative_path = str(call.get("relative_path") or "")
        if not file_id or not relative_path:
            continue
        uploads.append(
            StoredProjectUpload(
                file_id=file_id,
                conversation_id=str(message.conversation_id),
                message_id=str(message.id),
                original_filename=str(call.get("original_filename") or file_id),
                content_type=str(
                    call.get("content_type") or "application/octet-stream"
                ),
                size_bytes=int(call.get("size_bytes") or 0),
                relative_path=relative_path,
                created_at=message.created_at,
                ai_analysis_completed=bool(call.get("ai_analysis_completed")),
                file_deleted=bool(call.get("file_deleted")),
            )
        )
    return uploads


def resolve_upload_path(relative_path: str) -> Path:
    """Resolves a stored relative upload path below the configured private root."""
    settings = get_settings()
    root = Path(settings.upload_storage_dir).resolve()
    requested = Path(relative_path)
    if requested.is_absolute() or ".." in requested.parts:
        raise ValueError("Invalid upload path")
    resolved = (root / requested).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError("Upload path escapes storage root")
    return resolved


def extract_pdf_text(data: bytes, *, max_chars: int = 12_000) -> str:
    """Extracts text from a PDF using pypdf when available."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for PDF text extraction") from exc

    reader = PdfReader(BytesIO(data))
    chunks: list[str] = []
    for page in reader.pages[:20]:
        page_text = page.extract_text() or ""
        if page_text.strip():
            chunks.append(page_text.strip())
        if sum(len(chunk) for chunk in chunks) >= max_chars:
            break
    return "\n\n".join(chunks)[:max_chars].strip()


def render_pdf_pages_as_data_urls(
    data: bytes,
    *,
    max_pages: int = 3,
    zoom: float = 1.6,
) -> list[str]:
    """Renders the first PDF pages to PNG data URLs for vision analysis."""
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required for PDF page rendering") from exc

    data_urls: list[str] = []
    document = fitz.open(stream=data, filetype="pdf")
    try:
        matrix = fitz.Matrix(zoom, zoom)
        for index in range(min(max_pages, document.page_count)):
            page = document.load_page(index)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            png_bytes = pixmap.tobytes("png")
            encoded = base64.b64encode(png_bytes).decode("ascii")
            data_urls.append(f"data:image/png;base64,{encoded}")
    finally:
        document.close()
    return data_urls


async def analyze_pdf_upload(
    *, data: bytes, filename: str, agent_name: str
) -> str | None:
    """Summarizes PDF project content after text extraction and page rendering."""
    settings = get_settings()
    if not settings.enable_upload_ai_analysis or not settings.openai_api_key:
        return None

    extracted_text = ""
    rendered_pages: list[str] = []
    try:
        extracted_text = extract_pdf_text(data)
    except Exception as exc:
        log.warning(
            "upload.pdf_text_extraction_failed", filename=filename, error=str(exc)
        )
    try:
        rendered_pages = render_pdf_pages_as_data_urls(data)
    except Exception as exc:
        log.warning("upload.pdf_render_failed", filename=filename, error=str(exc))

    if not extracted_text and not rendered_pages:
        return "Das PDF wurde gespeichert, enthält aber keinen auslesbaren Text."

    safe_text = redact_contact_details(extracted_text)
    user_content: list[dict[str, object]] = [
        {
            "type": "text",
            "text": (
                f"Datei: {filename}. Fasse die für {agent_name} relevanten "
                "Planungsdetails kurz auf Deutsch zusammen. Beschreibe erkennbare "
                "Grundriss-, Raum-, Maß-, Anschluss- und Bestandsinformationen, "
                "aber gib keine verbindliche Planungsempfehlung."
            ),
        }
    ]
    if safe_text:
        user_content.append(
            {
                "type": "text",
                "text": f"Aus dem PDF lokal extrahierter Text:\n\n{safe_text}",
            }
        )
    for data_url in rendered_pages:
        user_content.append({"type": "image_url", "image_url": {"url": data_url}})

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.openai_chat_model,
        max_tokens=450,
        messages=[
            {
                "role": "system",
                "content": (
                    "Du analysierst PDF-Unterlagen für eine Küchenberatung. "
                    "Fasse nur projektbezogene, nicht-sensitive Inhalte als Entwurf "
                    "zusammen: Raummaße, Grundrisshinweise, Bestand, Wünsche, "
                    "Materialien, Geräte, offene Fragen. Wenn etwas unsicher oder "
                    "schlecht lesbar ist, markiere es als unsicher. Erstelle keine "
                    "verbindliche Fachberatung und transkribiere keine Kontaktdaten."
                ),
            },
            {"role": "user", "content": user_content},
        ],
    )
    return (response.choices[0].message.content or "").strip() or None


async def list_stored_project_uploads(
    *,
    session: AsyncSession,
    studio_id,
    conversation_id=None,
    limit: int = 500,
) -> list[StoredProjectUpload]:
    """Lists stored project uploads for a tenant, optionally scoped to one conversation."""
    statement = (
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.studio_id == studio_id)
        .where(Message.tool_calls.is_not(None))
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    if conversation_id is not None:
        statement = statement.where(Conversation.id == conversation_id)

    result = await session.execute(statement)
    uploads: list[StoredProjectUpload] = []
    for message in result.scalars().all():
        uploads.extend(extract_uploads_from_message(message))
    return uploads


async def delete_expired_upload_files(
    *,
    session: AsyncSession,
    cutoff: datetime,
) -> tuple[int, int]:
    """Deletes known and orphan upload files older than the cutoff."""
    result = await session.execute(
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Message.tool_calls.is_not(None))
        .where(Message.created_at < cutoff)
    )
    deleted_known = 0
    for message in result.scalars().all():
        changed = False
        tool_calls = message.tool_calls or []
        if not isinstance(tool_calls, list):
            continue
        for call in tool_calls:
            if not isinstance(call, dict) or call.get("type") != "project_upload":
                continue
            if call.get("file_deleted"):
                continue
            relative_path = str(call.get("relative_path") or "")
            if not relative_path:
                continue
            try:
                path = resolve_upload_path(relative_path)
            except ValueError:
                continue
            if path.exists():
                path.unlink()
                deleted_known += 1
            call["file_deleted"] = True
            call["file_deleted_at"] = datetime.now(timezone.utc).isoformat()
            changed = True
        if changed:
            message.tool_calls = list(tool_calls)

    deleted_orphans = _delete_orphan_files(cutoff)
    await session.flush()
    return deleted_known, deleted_orphans


def _delete_orphan_files(cutoff: datetime) -> int:
    """Deletes old files in the upload root that are no longer referenced."""
    settings = get_settings()
    root = Path(settings.upload_storage_dir)
    if not root.exists():
        return 0

    deleted = 0
    cutoff_ts = cutoff.timestamp()
    for path in root.rglob("*"):
        if not path.is_file() or path.stat().st_mtime >= cutoff_ts:
            continue
        try:
            path.unlink()
            deleted += 1
        except OSError as exc:
            log.warning(
                "upload.retention_delete_failed", path=str(path), error=str(exc)
            )

    for directory in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            continue
    return deleted
