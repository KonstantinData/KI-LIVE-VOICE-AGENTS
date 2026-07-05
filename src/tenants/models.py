"""
Tenant Profile Models
=====================
What:    Typed contracts for local tenant runtime profiles.
Does:    Parses registry JSON into immutable Pydantic models.
Why:     Live Voice Agents need tenant-scoped identity, policies, tools, and UI
         copy without hard-coding tenant names in runtime code.
Who:     Widget config, voice routes, upload routes, and tests.
Depends: pydantic
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model that rejects unknown registry fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class HostnameRecord(StrictModel):
    """Public hostname bound to one tenant surface."""

    hostname: str
    purpose: str
    expected_origin: str


class PublicWidgetProfile(StrictModel):
    """Customer-facing widget identity and feature defaults."""

    agent_name: str
    agent_subtitle: str
    welcome_message: str
    privacy_url: str
    retention_days: int = Field(gt=0)
    voice_enabled: bool
    upload_enabled: bool


class ContactHandoffPolicy(StrictModel):
    """PII handoff policy for voice sessions."""

    secure_form_required: bool
    voice_pii_collection_allowed: bool


class LiveVoiceAgentProfile(StrictModel):
    """Tenant-selected live voice runtime profile."""

    id: str
    agent_type: str
    display_name: str
    prompt_profile: str
    enabled: bool
    model: str
    voice: str
    skills: tuple[str, ...]
    tools: tuple[str, ...]
    knowledge_scopes: tuple[str, ...]
    data_scopes: tuple[str, ...]
    policies: tuple[str, ...]
    validators: tuple[str, ...]
    contact_handoff: ContactHandoffPolicy


class UploadPolicy(StrictModel):
    """Tenant upload policy for project files and photos."""

    enabled: bool
    ai_analysis_allowed: bool
    allowed_content_types: tuple[str, ...]


class ScopeConfig(StrictModel):
    """Tenant knowledge or data scope config."""

    scope_id: str
    indexes: tuple[str, ...]


class DataSource(StrictModel):
    """Tenant-bound external or internal data source."""

    id: str
    tenant_id: str
    type: str
    display_name: str
    access_modes: tuple[str, ...]
    status: str
    sensitivity: str


class TenantProfile(StrictModel):
    """Authoritative runtime profile for one tenant."""

    contract_version: str
    tenant_id: str
    studio_slug: str
    display_name: str
    status: str
    default_locale: str
    hostnames: tuple[HostnameRecord, ...]
    public_widget: PublicWidgetProfile
    live_voice_agents: tuple[LiveVoiceAgentProfile, ...]
    upload_policy: UploadPolicy | None = None
    knowledge: ScopeConfig | None = None
    data_sources: tuple[DataSource, ...] = ()
    policy_bundle: tuple[str, ...]
    validators: tuple[str, ...]

    @property
    def is_active(self) -> bool:
        """Returns whether this profile can be used at runtime."""
        return self.status in {"setup", "active"}

    def live_voice_agent(self, agent_id: str | None = None) -> LiveVoiceAgentProfile:
        """Returns the selected live voice agent profile for the tenant."""
        if agent_id is not None:
            for agent in self.live_voice_agents:
                if agent.id == agent_id:
                    return agent
            raise ValueError(f"Unknown live voice agent profile: {agent_id}")
        for agent in self.live_voice_agents:
            if agent.enabled:
                return agent
        raise ValueError("Tenant has no enabled live voice agent profile.")
