"""
Tenant Runtime Knowledge Loader
===============================
What:    Loads tenant-scoped runtime knowledge from registry/tenants.
Does:    Validates versioned JSON chunks before they are used in prompts or imports.
Why:     Runtime agents need tenant-owned knowledge without hard-coded tenant facts.
Who:     Agent prompt builders and future knowledge seeding/import tasks.
Depends: json, pathlib, pydantic, src.tenants.registry
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.tenants.registry import TENANT_REGISTRY_DIR, get_tenant_profile_for_studio


class TenantKnowledgeError(ValueError):
    """Raised when tenant runtime knowledge is missing or invalid."""


class TenantKnowledgeChunk(BaseModel):
    """One tenant-owned knowledge chunk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    category: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)


class TenantKnowledgeSource(BaseModel):
    """Versioned tenant knowledge source file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: str
    tenant_id: str
    scope_id: str
    chunks: tuple[TenantKnowledgeChunk, ...]


def _knowledge_path(tenant_id: str) -> Path:
    return TENANT_REGISTRY_DIR / tenant_id / "knowledge" / "chunks.json"


@lru_cache(maxsize=128)
def get_tenant_knowledge_source(tenant_id: str) -> TenantKnowledgeSource | None:
    """Loads the tenant's registry-backed runtime knowledge source, if present."""
    path = _knowledge_path(tenant_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        source = TenantKnowledgeSource.model_validate(data)
    except Exception as exc:
        raise TenantKnowledgeError(
            f"Tenant knowledge source is invalid: {tenant_id}"
        ) from exc
    if source.tenant_id != tenant_id:
        raise TenantKnowledgeError(
            f"Tenant knowledge source tenant_id mismatch: {tenant_id}"
        )
    return source


def get_tenant_knowledge_for_studio(studio_slug: str) -> TenantKnowledgeSource | None:
    """Returns the registry-backed runtime knowledge source for a studio slug."""
    profile = get_tenant_profile_for_studio(studio_slug)
    if profile is None or profile.knowledge is None:
        return None

    source = get_tenant_knowledge_source(profile.tenant_id)
    if source is None:
        return None
    if source.scope_id != profile.knowledge.scope_id:
        raise TenantKnowledgeError(
            f"Tenant knowledge source scope_id mismatch: {profile.tenant_id}"
        )
    return source


def format_tenant_knowledge_for_prompt(source: TenantKnowledgeSource) -> str:
    """Formats tenant knowledge chunks as compact prompt context."""
    sections = [
        f"### {chunk.title}\nKategorie: {chunk.category}\n{chunk.content}"
        for chunk in source.chunks
    ]
    return "\n\n".join(sections)
