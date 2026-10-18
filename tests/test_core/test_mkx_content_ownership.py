"""Content selection and role separation, without claiming live model behavior."""

import re

import pytest

from src.agents.mein_kuechenexperte.kea.prompts.conversation_contract import (
    KEA_CONVERSATION_CONTRACT,
)
from src.agents.mein_kuechenexperte.kea.system_prompt import build_kea_system_prompt
from src.agents.mein_kuechenexperte.kea.voice_prompt import build_kea_voice_prompt
from src.agents.mein_kuechenexperte.mia import build_mia_system_prompt, build_mia_voice_prompt
from src.agents.mein_kuechenexperte.shared import knowledge
from src.agents.mein_kuechenexperte.shared.conversation import build_conversation_style
from src.db.models.studio import Studio
from src.tenants.knowledge import TenantKnowledgeChunk, TenantKnowledgeError


@pytest.fixture
def studio():
    return Studio(slug="mein-kuechenexperte", name="Mein Küchenexperte", api_key="test")


def test_new_or_agent_specific_chunks_are_not_implicitly_shared(studio, monkeypatch):
    source = knowledge.get_tenant_knowledge_for_studio(studio.slug)
    assert source is not None
    extra = TenantKnowledgeChunk(
        id="future-agent-policy", category="studio", title="Future policy",
        content="Future agent must always request contact first.",
    )
    updated = source.model_copy(update={"chunks": (*source.chunks, extra)})
    monkeypatch.setattr(knowledge, "get_tenant_knowledge_for_studio", lambda _: updated)

    shared = knowledge.get_mkx_business_context(studio)

    assert "Honorar und kostenloses Vorgespräch" in shared
    assert "Future policy" not in shared
    assert "Projektaufnahme durch KEA" not in shared
    assert "Persoenliche Kontaktdaten" not in shared
    assert "soll KEA" not in shared


@pytest.mark.parametrize("builder", [build_mia_system_prompt, build_mia_voice_prompt])
def test_mia_never_inherits_kea_intake_knowledge(studio, builder):
    prompt = builder(studio)
    assert "KEA-Aufnahme und Übergabe" not in prompt
    assert KEA_CONVERSATION_CONTRACT not in prompt
    assert "MIA, die KI-Planungsassistentin" in prompt
    assert "Mein Küchenexperte" in prompt


@pytest.mark.parametrize("address_mode", ["du", "sie"])
def test_kea_text_and_voice_compose_one_contract_and_address_policy(studio, address_mode):
    text = build_kea_system_prompt(studio, address_mode=address_mode)
    voice = build_kea_voice_prompt(studio, address_mode=address_mode)
    shared_style = build_conversation_style(address_mode)
    for prompt in (text, voice):
        assert prompt.count(KEA_CONVERSATION_CONTRACT) == 1
        assert prompt.count(shared_style) == 1
        assert "höchstens zwei" not in prompt
        assert "Du erstellst keine Küchenentwürfe" in prompt
        assert "Projektaufnahme durch KEA" in prompt
        assert "120 Sekunden Erstgespräch" not in prompt
    assert voice.startswith(text)
    if address_mode == "du":
        assert "Meintest du" in voice
        assert "Meinten Sie" not in voice
        assert "Nutze gern die Pause" in voice
    else:
        assert "Meinten Sie" in voice
        assert "Meintest du" not in voice
        assert "Nutzen Sie gern die Pause" in voice


def test_shared_conversation_style_does_not_assign_workflow_or_capabilities():
    style = build_conversation_style()
    for marker in ("KEA", "MIA", "Anna", "Kontaktformular", "Kalender", "120", "Entwurf"):
        assert not re.search(rf"\b{re.escape(marker)}\b", style)
    assert "maximal eine Hauptfrage" in style


@pytest.mark.parametrize("source_mode", ["missing", "foreign", "no-business-facts"])
def test_shared_knowledge_rejects_invalid_or_unusable_sources(studio, monkeypatch, source_mode):
    source = knowledge.get_tenant_knowledge_for_studio(studio.slug)
    if source_mode == "missing":
        invalid = None
    elif source_mode == "foreign":
        invalid = source.model_copy(update={"tenant_id": "another-tenant"})
    else:
        invalid = source.model_copy(update={"chunks": ()})
    monkeypatch.setattr(knowledge, "get_tenant_knowledge_for_studio", lambda _: invalid)
    with pytest.raises(TenantKnowledgeError):
        knowledge.get_mkx_business_context(studio)
