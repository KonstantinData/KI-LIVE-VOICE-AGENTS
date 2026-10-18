"""Explicitly selected MKX business facts, excluding agent instructions."""

from src.db.models.studio import Studio
from src.tenants.knowledge import (
    TenantKnowledgeError,
    format_tenant_knowledge_for_prompt,
    get_tenant_knowledge_for_studio,
)

# New chunks require an explicit content ownership decision before reuse.
BUSINESS_CHUNK_IDS = frozenset({
    "studio-positioning",
    "kitchen-offer-guidance",
    "service-pricing",
    "planning-services",
    "service-boundaries",
    "public-contact",
    "project-documents",
    "consultation-process",
    "project-types",
    "independent-kitchen-consulting-value",
})


def get_mkx_business_context(studio: Studio) -> str:
    """Load allowlisted facts without sharing KEA's intake or handoff policy."""
    if studio.slug != "mein-kuechenexperte":
        raise ValueError("MKX business context is only available for mein-kuechenexperte.")
    source = get_tenant_knowledge_for_studio(studio.slug)
    if source is None:
        raise TenantKnowledgeError("MKX tenant knowledge is not available.")
    if source.tenant_id != "mein-kuechenexperte":
        raise TenantKnowledgeError("MKX tenant knowledge ownership does not match.")
    chunks = tuple(chunk for chunk in source.chunks if chunk.id in BUSINESS_CHUNK_IDS)
    if not chunks:
        raise TenantKnowledgeError("MKX business facts are not available.")
    selected = source.model_copy(update={"chunks": chunks})
    return (
        f"## MKX-Geschäftskontext: {studio.name}\n\n"
        f"Knowledge Scope: {source.scope_id}\n\n"
        "Die folgenden Fakten beschreiben die professionellen Leistungen von MKX. "
        "Aufgabe und Ablauf des jeweiligen KI-Assistenten sind davon getrennt.\n\n"
        f"{format_tenant_knowledge_for_prompt(selected)}"
    )
