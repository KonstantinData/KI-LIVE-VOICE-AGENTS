"""Tests for upload validation, limits, and retention cleanup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest

from src.api.config import get_settings
from src.api.services.project_uploads import (
    delete_expired_upload_files,
    redact_contact_details,
)
from src.db.models.conversation import Conversation
from src.db.models.message import Message
from tests.test_api.upload_helpers import seed_studio


def test_redact_contact_details_removes_email_and_phone():
    text = "Kontakt: test@example.com oder +49 171 1234567. Raum: 12 qm."
    redacted = redact_contact_details(text)

    assert "test@example.com" not in redacted
    assert "+49 171 1234567" not in redacted
    assert "Raum: 12 qm" in redacted


@pytest.mark.asyncio
async def test_upload_retention_deletes_expired_private_files(
    db_session,
    tmp_path,
    monkeypatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))
    studio = await seed_studio(db_session, slug="mein-kuechenexperte-retention")
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor-retention",
        status="closed",
    )
    relative_path = f"{studio.slug}/2026/01/{conversation.id}/old-file.png"
    file_path = tmp_path / relative_path
    file_path.parent.mkdir(parents=True)
    file_path.write_bytes(b"\x89PNG\r\n\x1a\nexpired")
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="user",
        content="Der Kunde hat eine Projektdatei hochgeladen: old-file.png",
        created_at=datetime.now(timezone.utc) - timedelta(days=200),
        tool_calls=[
            {
                "type": "project_upload",
                "file_id": "old-file",
                "original_filename": "old-file.png",
                "content_type": "image/png",
                "size_bytes": 15,
                "relative_path": relative_path,
            }
        ],
    )
    db_session.add_all([conversation, message])
    await db_session.flush()

    deleted_known, deleted_orphans = await delete_expired_upload_files(
        session=db_session,
        cutoff=datetime.now(timezone.utc) - timedelta(days=180),
    )

    assert deleted_known == 1
    assert deleted_orphans == 0
    assert not file_path.exists()


@pytest.mark.asyncio
async def test_project_file_upload_rejects_unsupported_file_type(
    db_client,
    db_session,
    tmp_path,
    monkeypatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))
    monkeypatch.setattr(
        settings, "cors_origins", ["https://www.mein-kuechenexperte.de"]
    )
    studio = await seed_studio(db_session, slug="mein-kuechenexperte-upload-invalid")

    response = await db_client.post(
        "/uploads/project-file",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        data={
            "studio": studio.slug,
            "visitor_id": "visitor-upload-invalid",
            "consent_granted": "true",
            "consent_version": "widget-v1",
            "ai_analysis_consent": "true",
        },
        files={"file": ("notiz.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "unsupported_file_type"


@pytest.mark.asyncio
async def test_project_file_upload_requires_analysis_consent(
    db_client,
    db_session,
    tmp_path,
    monkeypatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))
    monkeypatch.setattr(
        settings, "cors_origins", ["https://www.mein-kuechenexperte.de"]
    )
    studio = await seed_studio(db_session, slug="mein-kuechenexperte-upload-consent")

    response = await db_client.post(
        "/uploads/project-file",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        data={
            "studio": studio.slug,
            "visitor_id": "visitor-upload-consent",
            "consent_granted": "true",
            "consent_version": "widget-v1",
            "ai_analysis_consent": "false",
        },
        files={"file": ("kueche.jpg", b"\xff\xd8\xffimage", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "upload_analysis_consent_required"


@pytest.mark.asyncio
async def test_project_file_upload_enforces_visitor_hour_limit(
    db_client,
    db_session,
    tmp_path,
    monkeypatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "enable_upload_ai_analysis", False)
    monkeypatch.setattr(settings, "max_uploads_per_visitor_hour", 1)
    monkeypatch.setattr(
        settings, "cors_origins", ["https://www.mein-kuechenexperte.de"]
    )
    studio = await seed_studio(db_session, slug="mein-kuechenexperte-upload-limit")

    body = {
        "studio": studio.slug,
        "visitor_id": "visitor-upload-limit",
        "consent_granted": "true",
        "consent_version": "widget-v1",
        "ai_analysis_consent": "true",
    }
    first = await db_client.post(
        "/uploads/project-file",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        data=body,
        files={"file": ("kueche-1.png", b"\x89PNG\r\n\x1a\none", "image/png")},
    )
    second = await db_client.post(
        "/uploads/project-file",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        data=body,
        files={"file": ("kueche-2.png", b"\x89PNG\r\n\x1a\ntwo", "image/png")},
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "upload_rate_limit_exceeded"
