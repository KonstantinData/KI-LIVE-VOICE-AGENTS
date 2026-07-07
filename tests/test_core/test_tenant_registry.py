"""Tests for tenant registry based runtime profile selection."""

import uuid

from src.api.services.voice_sessions import realtime_session_config
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
    assert "book-appointment" not in profile.live_voice_agent().tools
    assert "no-voice-pii-capture" in profile.live_voice_agent().policies


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
    """Realtime config includes tenant-selected model, voice, and policy metadata."""
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

    assert config["model"] == "gpt-realtime"
    assert config["audio"]["output"]["voice"] == "marin"
    assert config["metadata"]["tenant_id"] == "mein-kuechenexperte"
    assert config["metadata"]["agent_profile_id"] == "kea-project-intake"
    assert "Du bist KEA" in config["instructions"]
    assert "kein Kuechenfachberater" in config["instructions"]
    assert "Angebotsfragen" in config["instructions"]
    assert "niemals Lisa" not in config["instructions"]
    assert agent_display_name("mein-kuechenexperte") == "KEA"
