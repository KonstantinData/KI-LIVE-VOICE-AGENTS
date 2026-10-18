"""Compose KEA's role, neutral style and explicitly selected tenant knowledge."""

from src.agents.mein_kuechenexperte.kea.profile import get_kea_profile
from src.agents.mein_kuechenexperte.kea.prompts.conversation_contract import (
    KEA_CONVERSATION_CONTRACT,
)
from src.agents.mein_kuechenexperte.kea.prompts.identity import KEA_IDENTITY
from src.agents.mein_kuechenexperte.kea.prompts.rules import KEA_RULES, KEA_TOOL_INSTRUCTIONS
from src.agents.mein_kuechenexperte.kea.prompts.tonality import KEA_TONALITY
from src.agents.mein_kuechenexperte.shared.conversation import build_conversation_style
from src.agents.mein_kuechenexperte.shared.knowledge import get_mkx_business_context
from src.db.models.studio import Studio
from src.tenants.knowledge import (
    TenantKnowledgeError,
    format_tenant_knowledge_for_prompt,
    get_tenant_knowledge_for_studio,
)


def _get_studio_knowledge(studio: Studio) -> str:
    """Select business facts and KEA-owned intake instructions separately."""
    get_kea_profile(studio)
    source = get_tenant_knowledge_for_studio(studio.slug)
    if source is None:
        raise TenantKnowledgeError("KEA tenant knowledge is not available.")
    intake_chunks = tuple(
        chunk for chunk in source.chunks
        if chunk.id in {"project-intake-scope", "secure-contact-handoff", "customer-values"}
    )
    intake = source.model_copy(update={"chunks": intake_chunks})
    return (
        get_mkx_business_context(studio)
        + "\n\n## KEA-Aufnahme und Übergabe\n\n"
        + format_tenant_knowledge_for_prompt(intake)
    )


def build_kea_system_prompt(
    studio: Studio,
    knowledge_snippets: list[str] | None = None,
    lead_summary: str | None = None,
    address_mode: str = "sie",
) -> str:
    """Build KEA's text prompt without inheriting another MKX agent's workflow."""
    profile = get_kea_profile(studio)
    sections = [
        KEA_IDENTITY.format(studio_name=studio.name, agent_name=profile.display_name),
        build_conversation_style(address_mode),
        KEA_TONALITY,
        KEA_CONVERSATION_CONTRACT,
        _get_studio_knowledge(studio),
        KEA_RULES,
        KEA_TOOL_INSTRUCTIONS,
    ]
    if knowledge_snippets:
        snippets_text = "\n\n---\n\n".join(knowledge_snippets)
        sections.append(f"## Zusätzliches Wissen aus deiner Wissensbasis\n\n{snippets_text}")
    if lead_summary:
        sections.append(f"## Was aus früheren Sessions bekannt ist\n\n{lead_summary}")
    return "\n\n".join(sections)
