"""Tests for registry-backed tenant runtime knowledge."""

import uuid

from src.agents.lisa.system_prompt import build_lisa_system_prompt
from src.db.models.studio import Studio
from src.tenants.knowledge import get_tenant_knowledge_for_studio


def test_mein_kuechenexperte_runtime_knowledge_source_matches_profile():
    """Tenant runtime knowledge is loaded through the tenant registry scope."""
    source = get_tenant_knowledge_for_studio("mein-kuechenexperte")

    assert source is not None
    assert source.tenant_id == "mein-kuechenexperte"
    assert source.scope_id == "mein-kuechenexperte-studio-knowledge"
    assert {chunk.category for chunk in source.chunks} <= {
        "faq",
        "sortiment",
        "referenzen",
        "aktionen",
        "studio",
    }
    assert any(chunk.id == "secure-contact-handoff" for chunk in source.chunks)


def test_lisa_prompt_includes_registry_backed_runtime_knowledge():
    """KEA receives tenant registry knowledge in the runtime system prompt."""
    studio = Studio(
        id=uuid.uuid4(),
        name="Mein Küchenexperte",
        slug="mein-kuechenexperte",
        api_key="test",
        is_active=True,
        config={},
    )

    prompt = build_lisa_system_prompt(
        studio=studio,
        knowledge_snippets=[],
        lead_summary=None,
    )

    assert "Knowledge Scope: mein-kuechenexperte-studio-knowledge" in prompt
    assert "Projektaufnahme durch KEA" in prompt
    assert "Persoenliche Kontaktdaten" in prompt
    assert "Musterstraße" not in prompt
