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


def test_liquisto_profile_is_registered_in_setup_mode():
    """Liquisto is present but not runtime-enabled until its handoff is tenant-aware."""
    profile = get_tenant_profile_for_studio("liquisto")

    assert profile is not None
    assert profile.tenant_id == "liquisto"
    assert profile.display_name == "Liquisto"
    assert profile.status == "setup"
    assert profile.public_widget.agent_name == "Liquisto"
    assert profile.public_widget.voice_enabled is False
    assert profile.public_widget.upload_enabled is False
    assert profile.live_voice_agent("liquisto-intake").enabled is False
    assert profile.live_voice_agent("liquisto-intake").tools == ()
    assert (
        profile.live_voice_agent("liquisto-intake").contact_handoff.crm_target
        == "liquisto"
    )
    assert profile.live_voice_agent(
        "liquisto-intake"
    ).contact_handoff.contact_endpoint == "https://liquisto.cloud/agent-lead-webhook"


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


def test_liquisto_realtime_prompt_does_not_receive_kea_contract():
    """Tenant-neutral voice prompts do not inherit KEA-specific contracts."""
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
        agent_id="liquisto-intake",
    )

    assert config["model"] == "gpt-realtime-2.1"
    assert "Du bist Liquisto" in config["instructions"]
    assert "KEA KOMMUNIKATIONSVERTRAG" not in config["instructions"]
    assert "ANGEBOTSORIENTIERUNG MEIN KÜCHENEXPERTE" not in config["instructions"]
    assert "kein Kuechenfachberater" not in config["instructions"]
    assert voice_enabled(studio, "liquisto-intake") is False
    assert voice_enabled(studio, "kea-project-intake") is False
