"""Tests for public project file uploads from the widget."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from src.api.config import get_settings
from src.db.models.conversation import Conversation
from src.db.models.message import Message
from src.db.models.studio import Studio


async def _seed_studio(db_session, slug: str = "mein-kuechenexperte") -> Studio:
    studio = Studio(
        id=uuid.uuid4(),
        name="Mein Küchenexperte",
        slug=slug,
        api_key=f"test-api-key-{uuid.uuid4()}",
        config={"agent_name": "KEA"},
        is_active=True,
    )
    db_session.add(studio)
    await db_session.flush()
    return studio


@pytest.mark.asyncio
async def test_project_file_upload_stores_private_file_and_message(
    db_client,
    db_session,
    tmp_path,
    monkeypatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "enable_upload_ai_analysis", False)
    monkeypatch.setattr(settings, "cors_origins", ["https://www.mein-kuechenexperte.de"])
    studio = await _seed_studio(db_session)
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"test-image"

    response = await db_client.post(
        "/uploads/project-file",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        data={
            "studio": studio.slug,
            "visitor_id": "visitor-upload",
            "consent_granted": "true",
            "consent_version": "widget-v1",
            "ai_analysis_consent": "true",
        },
        files={"file": ("kueche.png", png_bytes, "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["content_type"] == "image/png"
    assert (tmp_path / studio.slug).exists()
    conversation = await db_session.get(Conversation, uuid.UUID(payload["conversation_id"]))
    assert conversation is not None
    messages = (
        await db_session.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
    ).scalars().all()
    assert len(messages) == 1
    assert "Projektdatei hochgeladen" in messages[0].content
    assert messages[0].tool_calls[0]["relative_path"].endswith(".png")
    assert messages[0].tool_calls[0]["ai_analysis_requested"] is True


@pytest.mark.asyncio
async def test_project_file_upload_rejects_unsupported_file_type(
    db_client,
    db_session,
    tmp_path,
    monkeypatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "cors_origins", ["https://www.mein-kuechenexperte.de"])
    studio = await _seed_studio(db_session, slug="mein-kuechenexperte-upload-invalid")

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
    monkeypatch.setattr(settings, "cors_origins", ["https://www.mein-kuechenexperte.de"])
    studio = await _seed_studio(db_session, slug="mein-kuechenexperte-upload-consent")

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
    monkeypatch.setattr(settings, "cors_origins", ["https://www.mein-kuechenexperte.de"])
    studio = await _seed_studio(db_session, slug="mein-kuechenexperte-upload-limit")

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
