"""Tests for public project file uploads from the widget."""

from __future__ import annotations

from types import SimpleNamespace
import hmac
import time
import uuid

import pytest
from sqlalchemy import select

from src.api.config import get_settings
from src.db.models.conversation import Conversation
from src.db.models.message import Message
from src.db.models.studio import Studio


async def seed_studio(db_session, *, slug: str | None = None) -> Studio:
    """Creates a widget runtime studio for upload tests."""
    studio = Studio(
        id=uuid.uuid4(),
        name="Mein Küchenexperte",
        slug=slug or f"upload-studio-{uuid.uuid4().hex}",
        api_key=f"upload-key-{uuid.uuid4()}",
        config={"agent_name": "KEA", "upload_enabled": True},
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
async def test_project_file_download_requires_signed_crm_access(
    db_client,
    db_session,
    tmp_path,
    monkeypatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "enable_upload_ai_analysis", False)
    monkeypatch.setattr(settings, "crm_upload_access_secret", "download-secret")
    monkeypatch.setattr(settings, "crm_contact_handoff_secret", "")
    monkeypatch.setattr(
        settings, "cors_origins", ["https://www.mein-kuechenexperte.de"]
    )
    studio = await seed_studio(db_session, slug="mein-kuechenexperte-download")

    upload_response = await db_client.post(
        "/uploads/project-file",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        data={
            "studio": studio.slug,
            "visitor_id": "visitor-download",
            "consent_granted": "true",
            "consent_version": "widget-v1",
            "ai_analysis_consent": "true",
        },
        files={"file": ("kueche.png", b"\x89PNG\r\n\x1a\ndownload", "image/png")},
    )
    assert upload_response.status_code == 200
    upload = upload_response.json()
    expires = int(time.time()) + 300
    canonical = (
        f"{studio.slug}\n{upload['conversation_id']}\n{upload['file_id']}\n{expires}"
    ).encode("utf-8")
    signature = hmac.new(b"download-secret", canonical, "sha256").hexdigest()

    download_response = await db_client.get(
        f"/uploads/project-file/{upload['file_id']}/content",
        params={
            "tenant_id": studio.slug,
            "conversation_id": upload["conversation_id"],
            "expires": str(expires),
            "signature": signature,
        },
    )

    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "image/png"
    assert download_response.content.startswith(b"\x89PNG")

    denied_response = await db_client.get(
        f"/uploads/project-file/{upload['file_id']}/content",
        params={
            "tenant_id": studio.slug,
            "conversation_id": upload["conversation_id"],
            "expires": str(expires),
            "signature": "0" * 64,
        },
    )
    assert denied_response.status_code == 403


@pytest.mark.asyncio
async def test_project_file_download_accepts_crm_secret_aliases(
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
    studio = await seed_studio(db_session, slug="mein-kuechenexperte-aliases")

    upload_response = await db_client.post(
        "/uploads/project-file",
        headers={"Origin": "https://www.mein-kuechenexperte.de"},
        data={
            "studio": studio.slug,
            "visitor_id": "visitor-download-alias",
            "consent_granted": "true",
            "consent_version": "widget-v1",
            "ai_analysis_consent": "true",
        },
        files={"file": ("kueche.png", b"\x89PNG\r\n\x1a\nalias", "image/png")},
    )
    assert upload_response.status_code == 200
    upload = upload_response.json()

    monkeypatch.setattr(settings, "crm_upload_access_secret", "runtime-secret")
    monkeypatch.setattr(settings, "crm_contact_handoff_secret", "agent-secret")
    expires = int(time.time()) + 300
    canonical = (
        f"{studio.slug}\n{upload['conversation_id']}\n{upload['file_id']}\n{expires}"
    ).encode("utf-8")
    agent_signature = hmac.new(b"agent-secret", canonical, "sha256").hexdigest()

    agent_secret_response = await db_client.get(
        f"/uploads/project-file/{upload['file_id']}/content",
        params={
            "tenant_id": studio.slug,
            "conversation_id": upload["conversation_id"],
            "expires": str(expires),
            "signature": agent_signature,
        },
    )
    assert agent_secret_response.status_code == 200

    monkeypatch.setattr(settings, "crm_upload_access_secret", "")
    monkeypatch.setattr(settings, "crm_contact_handoff_secret", "")
    monkeypatch.setenv("VOICE_UPLOAD_ACCESS_SECRET", "voice-secret")
    voice_signature = hmac.new(b"voice-secret", canonical, "sha256").hexdigest()

    voice_secret_response = await db_client.get(
        f"/uploads/project-file/{upload['file_id']}/content",
        params={
            "tenant_id": studio.slug,
            "conversation_id": upload["conversation_id"],
            "expires": str(expires),
            "signature": voice_signature,
        },
    )
    assert voice_secret_response.status_code == 200


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
    usage_events: list[dict] = []

    async def fake_analysis(**kwargs):
        assert kwargs["content_type"] == "application/pdf"
        from src.api.services.project_uploads import UploadAnalysisResult

        return UploadAnalysisResult(
            summary="PDF summary",
            usage={
                "prompt_tokens": 1200,
                "completion_tokens": 120,
                "total_tokens": 1320,
            },
            model="gpt-4o-mini",
        )

    monkeypatch.setattr("src.api.routes.uploads._analyze_project_upload", fake_analysis)

    async def fake_usage_handoff(**kwargs):
        usage_events.append(kwargs)
        return "usage-ledger-1"

    monkeypatch.setattr(
        "src.api.routes.uploads.post_openai_usage_to_crm", fake_usage_handoff
    )
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
    assert len(usage_events) == 1
    event = usage_events[0]
    assert event["channel_type"] == "upload"
    assert event["component"] == "project_upload_analysis"
    assert event["model"] == "gpt-4o-mini"
    assert event["usage"]["prompt_tokens"] == 1200
    assert event["metadata"]["content_type"] == "application/pdf"


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
                model="gpt-4o-mini",
                usage=SimpleNamespace(
                    model_dump=lambda mode="json": {
                        "prompt_tokens": 2000,
                        "completion_tokens": 100,
                        "total_tokens": 2100,
                    }
                ),
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="Grundriss mit Maßangaben erkannt."
                        )
                    )
                ],
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

    assert result is not None
    assert result.summary == "Grundriss mit Maßangaben erkannt."
    assert result.model == "gpt-4o-mini"
    user_message = captured["messages"][1]
    assert user_message["content"][1]["type"] == "image_url"
