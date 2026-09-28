"""Load Anna's curated public knowledge independently of website-agent content."""

from datetime import date
import json

from src.tenants.knowledge import TenantKnowledgeChunk, TenantKnowledgeSource
from src.tenants.registry import TENANT_REGISTRY_DIR

TENANT_ID = "mein-kuechenexperte"
SCOPE_ID = "mein-kuechenexperte-anna-knowledge"
KNOWLEDGE_PATH = TENANT_REGISTRY_DIR / TENANT_ID / "knowledge" / "anna.json"


def load_anna_knowledge() -> TenantKnowledgeSource:
    """Read on each call so curated updates do not require a knowledge cache reset."""
    source = TenantKnowledgeSource.model_validate(
        json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    )
    if source.tenant_id != TENANT_ID or source.scope_id != SCOPE_ID:
        raise ValueError("Anna knowledge identity mismatch")
    ids = [chunk.id for chunk in source.chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("Anna knowledge contains duplicate chunk identifiers")
    return source


def usable_public_fact(chunk: TenantKnowledgeChunk, *, today: date | None = None) -> bool:
    """Withhold unreviewed, expired, private, or untraceable facts from conversations."""
    metadata = chunk.metadata
    if metadata.get("sensitivity") != "public" or metadata.get("status") != "approved":
        return False
    if not metadata.get("source_repo") or not metadata.get("source_url", "").startswith(
        "https://mein-kuechenexperte.de/"
    ):
        return False
    try:
        reviewed = date.fromisoformat(metadata["reviewed_on"])
        expires = date.fromisoformat(metadata["valid_until"])
    except (KeyError, ValueError):
        return False
    return reviewed <= (today or date.today()) <= expires
