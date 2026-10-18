"""Regression tests for KEA's tenant/profile boundary and summary identity."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from src.agents.mein_kuechenexperte.kea import KeaAgent
from src.agents.mein_kuechenexperte.kea import profile as kea_profile
from src.agents.mein_kuechenexperte.kea import system_prompt
from src.agents.mein_kuechenexperte.kea.voice_prompt import build_kea_voice_prompt
from src.api.services.voice_sessions import realtime_session_config, voice_enabled
from src.db.models.conversation import Conversation
from src.db.models.studio import Studio
from src.tenants.knowledge import TenantKnowledgeError


@pytest.fixture
def studio():
    return Studio(
        id=uuid.uuid4(), slug="mein-kuechenexperte", name="Mein Küchenexperte",
        api_key="test", is_active=True, config={"agent_name": "Legacy Name"},
    )


@pytest.fixture
def conversation(studio):
    return Conversation(
        id=uuid.uuid4(), studio_id=studio.id, visitor_id="test-visitor",
        channel="voice", status="active",
    )


@pytest.mark.parametrize("slug", ["unknown-studio", "liquisto"])
def test_kea_prompt_builders_reject_other_tenants(studio, slug):
    studio.slug = slug
    for builder in (system_prompt.build_kea_system_prompt, build_kea_voice_prompt):
        with pytest.raises(ValueError, match="only available"):
            builder(studio)


def test_kea_requires_registered_profile(studio, monkeypatch):
    monkeypatch.setattr(kea_profile, "get_tenant_profile_for_studio", lambda _: None)
    with pytest.raises(ValueError, match="tenant profile"):
        system_prompt.build_kea_system_prompt(studio)


def test_kea_text_and_voice_use_profile_identity(studio, monkeypatch):
    profile = kea_profile.get_tenant_profile_for_studio(studio.slug)
    voice = profile.live_voice_agent("kea-project-intake")
    renamed = voice.model_copy(update={"display_name": "Profile Name"})
    updated = profile.model_copy(update={"live_voice_agents": (renamed,)})
    monkeypatch.setattr(kea_profile, "get_tenant_profile_for_studio", lambda _: updated)
    for builder in (system_prompt.build_kea_system_prompt, build_kea_voice_prompt):
        assert "Du bist Profile Name" in builder(studio)


def test_missing_knowledge_never_uses_placeholder_facts(studio, monkeypatch):
    monkeypatch.setattr(system_prompt, "get_tenant_knowledge_for_studio", lambda _: None)
    for builder in (system_prompt.build_kea_system_prompt, build_kea_voice_prompt):
        with pytest.raises(TenantKnowledgeError, match="not available"):
            builder(studio)


@pytest.mark.parametrize("agent_id", ["mia-kitchen-design", "anna", "unknown-agent"])
def test_unavailable_agents_do_not_fall_back_to_kea(studio, conversation, agent_id):
    with pytest.raises(ValueError, match="not available"):
        realtime_session_config(studio, conversation, [], None, agent_id=agent_id)


def test_unregistered_studio_cannot_use_legacy_voice_fallback(studio, conversation):
    studio.slug = "unknown-studio"
    studio.config = {"voice_enabled": True, "agent_name": "KEA"}
    assert voice_enabled(studio) is False
    with pytest.raises(ValueError, match="not available"):
        realtime_session_config(studio, conversation, [], None)


@pytest.mark.asyncio
async def test_summary_uses_kea_speaker_identity(studio, conversation, monkeypatch):
    session = MagicMock()
    result = MagicMock()
    session.execute = AsyncMock(return_value=result)
    result.scalars.return_value.all.return_value = [
        SimpleNamespace(role="user", content="Eine neue Küche."),
        SimpleNamespace(role="assistant", content="Welche Projektphase?"),
    ]
    llm = SimpleNamespace(chat=AsyncMock(return_value=SimpleNamespace(content="Summary")))
    monkeypatch.setattr(
        "src.agents.mein_kuechenexperte.kea.agent.LLMClient", lambda: llm,
    )

    await KeaAgent(session).finalize_conversation(conversation, studio)

    transcript = llm.chat.call_args.kwargs["messages"][0]["content"]
    assert "KEA: Welche Projektphase?" in transcript
    assert "Lisa:" not in transcript
    assert conversation.summary == "Summary"
    assert conversation.status == "closed"
