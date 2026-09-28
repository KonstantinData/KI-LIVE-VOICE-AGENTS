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

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    contact_form_enabled: bool = True


class ContactHandoffPolicy(StrictModel):
    """PII handoff policy for voice sessions."""

    secure_form_required: bool
    voice_pii_collection_allowed: bool
    crm_target: str
    contact_endpoint: str
    usage_endpoint: str


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
    audience: Literal["public", "internal-authenticated"] = "public"
    contact_handoff: ContactHandoffPolicy | None = None

    @model_validator(mode="after")
    def validate_audience_capabilities(self) -> "LiveVoiceAgentProfile":
        """Keeps public handoff and internal no-handoff profiles fail closed."""
        if self.audience == "public" and self.contact_handoff is None:
            raise ValueError("public voice agents require contact_handoff")
        if self.audience == "internal-authenticated" and self.contact_handoff is not None:
            raise ValueError("internal voice agents must not configure contact_handoff")
        return self


class PhoneAgentProfile(StrictModel):
    """Explicit opt-in for an inbound telephone agent, separate from browser voice."""

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    agent_type: Literal["phone-assistant"] = "phone-assistant"
    display_name: str = Field(min_length=1)
    prompt_profile: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    enabled: bool = False
    adapter: Literal["fritzbox-sip"]
    model: str = Field(min_length=1)
    voice: str = Field(min_length=1)
    greeting: str = Field(min_length=1)
    max_call_seconds: int = Field(default=600, ge=30, le=1800)
    knowledge_scopes: tuple[str, ...] = ()
    tools: tuple[Literal["submit_phone_contact_handoff"], ...] = ()
    data_scopes: tuple[str, ...] = ()
    policies: tuple[str, ...] = ()
    validators: tuple[str, ...] = ()
    contact_handoff: ContactHandoffPolicy | None = None
    store_audio: Literal[False] = False
    store_transcript: Literal[False] = False

    @model_validator(mode="after")
    def validate_contact_handoff(self) -> "PhoneAgentProfile":
        """Keep telephone PII collection behind one explicit, consent-gated grant."""
        enabled = "submit_phone_contact_handoff" in self.tools
        if enabled != (self.contact_handoff is not None):
            raise ValueError("Phone contact tool and handoff policy must be configured together")
        if enabled:
            assert self.contact_handoff is not None
            required = {
                "tenant-crm-handoff-write",
                "phone-contact-data-write",
            }
            if not required.issubset(self.data_scopes):
                raise ValueError("Phone contact handoff requires explicit data scopes")
            if self.contact_handoff.secure_form_required:
                raise ValueError("Telephone handoff cannot require a browser form")
            if not self.contact_handoff.voice_pii_collection_allowed:
                raise ValueError("Telephone contact handoff requires voice PII permission")
        return self


class AssistantAgentProfile(StrictModel):
    """Tenant-selected internal text assistant profile."""

    id: str
    agent_type: Literal["text-assistant"]
    display_name: str
    prompt_profile: str
    enabled: bool
    provider: Literal["openai-compatible-local"]
    model_env: Literal["LIQUISTO_ASSISTANT_LLM_MODEL"]
    allowed_surfaces: tuple[Literal["cockpit", "crm", "trade", "control"], ...]
    allowed_modes: tuple[Literal["inform-and-prepare"], ...]
    tools: tuple[str, ...]
    knowledge_scopes: tuple[str, ...]
    policies: tuple[str, ...]
    validators: tuple[str, ...]


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
    system: str
    required_permission: str
    allowed_classifications: tuple[Literal["public", "internal"], ...]


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
    assistant_agents: tuple[AssistantAgentProfile, ...] = ()
    phone_agents: tuple[PhoneAgentProfile, ...] = ()
    upload_policy: UploadPolicy | None = None
    knowledge: ScopeConfig | None = None
    data_sources: tuple[DataSource, ...] = ()
    policy_bundle: tuple[str, ...]
    validators: tuple[str, ...]

    @model_validator(mode="after")
    def validate_phone_agent_ids(self) -> "TenantProfile":
        """Phone identities cannot alias browser agents or each other."""
        other_ids = {agent.id for agent in (*self.live_voice_agents, *self.assistant_agents)}
        phone_ids = [agent.id for agent in self.phone_agents]
        if len(phone_ids) != len(set(phone_ids)) or other_ids.intersection(phone_ids):
            raise ValueError("Phone agent IDs must be unique and separate from other channels")
        return self

    def phone_agent(self, agent_id: str) -> PhoneAgentProfile:
        """Requires an active tenant and an explicitly enabled phone identity."""
        if not self.is_active:
            raise ValueError("Tenant is not active")
        for agent in self.phone_agents:
            if agent.id == agent_id and agent.enabled:
                return agent
        raise ValueError("Unknown or disabled phone agent")

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

    def assistant_agent(self, agent_id: str) -> AssistantAgentProfile:
        """Returns one explicitly selected internal assistant profile."""
        for agent in self.assistant_agents:
            if agent.id == agent_id and agent.enabled:
                return agent
        raise ValueError(f"Unknown or disabled assistant agent profile: {agent_id}")
