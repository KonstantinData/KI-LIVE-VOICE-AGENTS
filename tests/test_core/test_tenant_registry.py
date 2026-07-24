"""Tests for tenant registry based runtime profile selection."""

import uuid

from src.api.services.voice_sessions import realtime_session_config, voice_enabled
from src.db.models.conversation import Conversation
from src.db.models.studio import Studio
from src.tenants.registry import (
    agent_display_name,
    get_tenant_profile_for_studio,
    widget_config_from_profile,
)


def test_mein_kuechenexperte_profile_selects_kea_widget_identity():
    """The tenant profile owns the public widget identity."""
    profile = get_tenant_profile_for_studio("mein-kuechenexperte")

    assert profile is not None
    assert profile.tenant_id == "mein-kuechenexperte"
    assert profile.public_widget.agent_name == "KEA"
    assert profile.live_voice_agent().agent_type == "live-voice"
    assert profile.live_voice_agent().tools == ()
    assert "book-appointment" not in profile.live_voice_agent().tools
    assert "tenant-lead-write" not in profile.live_voice_agent().data_scopes
    assert "tenant-crm-handoff-write" in profile.live_voice_agent().data_scopes
    assert "no-voice-pii-capture" in profile.live_voice_agent().policies
    assert (
        profile.live_voice_agent().contact_handoff.crm_target == "mein-kuechenexperte"
    )
    assert profile.live_voice_agent().contact_handoff.usage_endpoint.endswith(
        "/agent-usage-webhook"
    )


def test_liquisto_profile_registers_olivia_without_public_voice_or_handoff():
    """Olivia is active for text while internal voice awaits employee auth."""
    profile = get_tenant_profile_for_studio("liquisto")

    assert profile is not None
    assert profile.tenant_id == "liquisto"
    assert profile.display_name == "Liquisto"
    assert profile.status == "active"
    assert profile.public_widget.agent_name == "Olivia"
    assert profile.public_widget.voice_enabled is False
    assert profile.public_widget.upload_enabled is False
    assert profile.public_widget.contact_form_enabled is False
    voice = profile.live_voice_agent("liquisto-assistant")
    assert voice.display_name == "Olivia"
    assert voice.enabled is True
    assert voice.audience == "internal-authenticated"
    assert voice.tools == ("open_liquisto_destination",)
    assert voice.contact_handoff is None
    assert not any("write" in scope for scope in voice.data_scopes)
    assert "navigation-only" in voice.policies
    assert "no-free-url" in voice.policies
    assert "no-browser-automation" in voice.policies
    assert "no-mutation" in voice.policies
    assistant = profile.assistant_agent("liquisto-assistant")
    assert assistant.allowed_modes == ("inform-and-prepare",)
    assert assistant.tools == ()
    kea_profile = get_tenant_profile_for_studio("mein-kuechenexperte")
    assert kea_profile is not None
    assert "open_liquisto_destination" not in kea_profile.live_voice_agent().tools


def test_widget_config_registry_overrides_legacy_db_agent_name():
    """Tenant registry prevents legacy DB values from leaking into widget copy."""
    config = widget_config_from_profile(
        studio_slug="mein-kuechenexperte",
        studio_name="Mein Küchenexperte",
        db_config={"agent_name": "Lisa", "voice_enabled": False},
    )

    assert config["agent_name"] == "KEA"
    assert config["agent_subtitle"] == "Küchen Expert Assistent"
    assert config["voice_enabled"] is True


def test_realtime_session_config_uses_tenant_runtime_profile():
    """Realtime config includes tenant-selected model and voice."""
    studio = Studio(
        id=uuid.uuid4(),
        name="Mein Küchenexperte",
        slug="mein-kuechenexperte",
        api_key="test",
        is_active=True,
        config={"agent_name": "Lisa"},
    )
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor",
        channel="voice",
        status="active",
    )

    config = realtime_session_config(
        studio=studio,
        conversation=conversation,
        tools=[],
        lead_summary=None,
        address_mode="sie",
    )

    assert config["model"] == "gpt-realtime-2.1"
    assert config["audio"]["output"]["voice"] == "shimmer"
    assert "metadata" not in config
    assert "Du bist KEA" in config["instructions"]
    assert "kein Kuechenfachberater" in config["instructions"]
    assert "Angebotsfragen" in config["instructions"]
    assert "niemals Lisa" not in config["instructions"]
    assert agent_display_name("mein-kuechenexperte") == "KEA"


def test_liquisto_realtime_prompt_uses_olivia_without_end_customer_intake():
    """The prepared voice config uses Olivia's dedicated internal prompt."""
    studio = Studio(
        id=uuid.uuid4(),
        name="Liquisto",
        slug="liquisto",
        api_key="test",
        is_active=True,
        config={"agent_name": "Wrong Legacy Name"},
    )
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor",
        channel="voice",
        status="active",
    )

    config = realtime_session_config(
        studio=studio,
        conversation=conversation,
        tools=[],
        lead_summary=None,
        address_mode="sie",
        agent_id="liquisto-assistant",
    )

    assert config["model"] == "gpt-realtime-2.1"
    assert "Du bist Olivia" in config["instructions"]
    assert "Transforming Excess Inventory" in config["instructions"]
    assert "persoenliche Assistenz" in config["instructions"]
    assert "KEA KOMMUNIKATIONSVERTRAG" not in config["instructions"]
    assert "ANGEBOTSORIENTIERUNG MEIN KÜCHENEXPERTE" not in config["instructions"]
    assert "kein Kuechenfachberater" not in config["instructions"]
    assert "Kontaktformular" not in config["instructions"]
    assert "Aus Datenschutzgruenden" not in config["instructions"]
    assert "tools" not in config
    assert voice_enabled(studio, "liquisto-assistant") is False
    assert voice_enabled(studio, "kea-project-intake") is False


def test_public_voice_rejects_internal_agent_even_if_widget_flag_is_misconfigured(
    monkeypatch,
):
    """An internal Olivia profile can never become a public widget agent."""
    profile = get_tenant_profile_for_studio("liquisto")
    assert profile is not None
    public_widget = profile.public_widget.model_copy(update={"voice_enabled": True})
    misconfigured = profile.model_copy(update={"public_widget": public_widget})
    monkeypatch.setattr(
        "src.api.services.voice_sessions.get_tenant_profile_for_studio",
        lambda _studio_slug: misconfigured,
    )
    studio = Studio(
        id=uuid.uuid4(),
        name="Liquisto",
        slug="liquisto",
        api_key="test",
        is_active=True,
        config={},
    )

    assert voice_enabled(studio, "liquisto-assistant") is False
