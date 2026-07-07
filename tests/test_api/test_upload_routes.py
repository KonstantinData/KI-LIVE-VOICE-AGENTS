"""Tests for public project file uploads from the widget."""

from __future__ import annotations

from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import select

from src.api.config import get_settings
from src.db.models.conversation import Conversation
from src.db.models.message import Message
from tests.test_api.upload_helpers import auth_headers as get_auth_headers
from tests.test_api.upload_helpers import seed_studio


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
    monkeypatch.setattr(
        settings, "cors_origins", ["https://www.mein-kuechenexperte.de"]
    )
    studio = await seed_studio(db_session)
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
    conversation = await db_session.get(
        Conversation, uuid.UUID(payload["conversation_id"])
    )
    assert conversation is not None
    messages = (
        (
            await db_session.execute(
                select(Message).where(Message.conversation_id == conversation.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(messages) == 1
    assert "Projektdatei hochgeladen" in messages[0].content
    assert messages[0].tool_calls[0]["relative_path"].endswith(".png")
    assert messages[0].tool_calls[0]["ai_analysis_requested"] is True


@pytest.mark.asyncio
async def test_project_file_upload_supports_protected_dashboard_download(
    db_client,
    db_session,
    tmp_path,
    monkeypatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "enable_upload_ai_analysis", False)
    monkeypatch.setattr(
        settings, "cors_origins", ["https://www.mein-kuechenexperte.de"]
    )
    studio = await seed_studio(db_session)
    headers = {"Origin": "https://www.mein-kuechenexperte.de"}
    png_bytes = b"\x89PNG\r\n\x1a\nprivate-dashboard-file"

    upload = await db_client.post(
        "/uploads/project-file",
        headers=headers,
        data={
            "studio": studio.slug,
            "visitor_id": "visitor-dashboard-download",
            "consent_granted": "true",
            "consent_version": "widget-v1",
            "ai_analysis_consent": "true",
        },
        files={"file": ("kueche.png", png_bytes, "image/png")},
    )
    assert upload.status_code == 200

    auth_headers = await get_auth_headers(db_client)
    file_id = upload.json()["file_id"]
    list_response = await db_client.get(
        "/uploads/project-files",
        headers=auth_headers,
    )
    download_response = await db_client.get(
        f"/uploads/project-files/{file_id}",
        headers=auth_headers,
    )

    assert list_response.status_code == 200
    assert list_response.json()[0]["file_id"] == file_id
    assert download_response.status_code == 200
    assert download_response.content == png_bytes


@pytest.mark.asyncio
async def test_project_file_upload_uses_explicit_conversation_id(
    db_client,
    db_session,
    tmp_path,
    monkeypatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "enable_upload_ai_analysis", False)
    monkeypatch.setattr(
        settings, "cors_origins", ["https://www.mein-kuechenexperte.de"]
    )
    studio = await seed_studio(db_session, slug="mein-kuechenexperte-explicit")
    current_conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor-explicit",
        status="active",
    )
    other_conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor-explicit",
        status="active",
    )
    db_session.add_all([current_conversation, other_conversation])
    await db_session.flush()

    response = await db_client.post(
        "/uploads/project-file",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        data={
            "studio": studio.slug,
            "visitor_id": "visitor-explicit",
            "conversation_id": str(current_conversation.id),
            "consent_granted": "true",
            "consent_version": "widget-v1",
            "ai_analysis_consent": "true",
        },
        files={"file": ("kueche.png", b"\x89PNG\r\n\x1a\nexplicit", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["conversation_id"] == str(current_conversation.id)
    messages = (
        (
            await db_session.execute(
                select(Message).where(
                    Message.conversation_id == current_conversation.id
                )
            )
        )
        .scalars()
        .all()
    )
    other_messages = (
        (
            await db_session.execute(
                select(Message).where(Message.conversation_id == other_conversation.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(messages) == 1
    assert other_messages == []


@pytest.mark.asyncio
async def test_pdf_project_file_upload_runs_analysis_path(
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
    studio = await seed_studio(db_session, slug="mein-kuechenexperte-pdf")

    async def fake_analysis(**kwargs):
        assert kwargs["content_type"] == "application/pdf"
        return "PDF summary"

    monkeypatch.setattr("src.api.routes.uploads._analyze_project_upload", fake_analysis)
    response = await db_client.post(
        "/uploads/project-file",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        data={
            "studio": studio.slug,
            "visitor_id": "visitor-pdf",
            "consent_granted": "true",
            "consent_version": "widget-v1",
            "ai_analysis_consent": "true",
        },
        files={"file": ("plan.pdf", b"%PDF-1.4\n%test", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["analysis_summary"] == "PDF summary"


@pytest.mark.asyncio
async def test_pdf_upload_analysis_uses_rendered_pages_when_text_is_empty(monkeypatch):
    """PDF analysis falls back to vision when a plan has no extractable text."""
    settings = get_settings()
    monkeypatch.setattr(settings, "enable_upload_ai_analysis", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_chat_model", "gpt-4o-mini")
    monkeypatch.setattr(
        "src.api.services.project_uploads.extract_pdf_text", lambda data: ""
    )
    monkeypatch.setattr(
        "src.api.services.project_uploads.render_pdf_pages_as_data_urls",
        lambda data: ["data:image/png;base64,test"],
    )
    captured: dict[str, object] = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="Grundriss mit Maßangaben erkannt."
                        )
                    )
                ]
            )

    class FakeOpenAI:
        def __init__(self, *, api_key: str):
            assert api_key == "sk-test"
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("src.api.services.project_uploads.AsyncOpenAI", FakeOpenAI)

    from src.api.services.project_uploads import analyze_pdf_upload

    result = await analyze_pdf_upload(
        data=b"%PDF-1.4",
        filename="grundriss.pdf",
        agent_name="KEA",
    )

    assert result == "Grundriss mit Maßangaben erkannt."
    user_message = captured["messages"][1]
    assert user_message["content"][1]["type"] == "image_url"
