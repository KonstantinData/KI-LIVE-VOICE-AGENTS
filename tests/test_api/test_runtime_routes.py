"""Tests for the public runtime API surface."""

import uuid

import pytest

from src.db.models.studio import Studio


async def _seed_studio(db_session) -> Studio:
    """Creates the default public widget studio."""
    studio = Studio(
        id=uuid.uuid4(),
        name="Mein Küchenexperte",
        slug="mein-kuechenexperte",
        api_key="test-api-key",
        config={"primary_color": "#2563eb", "agent_name": "KEA"},
        is_active=True,
    )
    db_session.add(studio)
    await db_session.flush()
    return studio


@pytest.mark.asyncio
async def test_widget_config_is_public_for_active_studio(db_client, db_session):
    """Widget config exposes safe public fields without dashboard auth."""
    await _seed_studio(db_session)

    response = await db_client.get("/widget-config/?studio=mein-kuechenexperte")

    assert response.status_code == 200
    data = response.json()
    assert data["studio"] == "mein-kuechenexperte"
    assert data["agent_name"] == "KEA"
    assert data["agent_subtitle"] == "Küchen Expert Assistent"
    assert data["voice_enabled"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/auth/login",
        "/studios/current",
        "/leads/",
        "/dashboard/stats",
        "/dashboard/costs",
        "/conversations/00000000-0000-0000-0000-000000000000/messages",
        "/gdpr/export?visitor_id=test",
        "/uploads/project-files",
    ],
)
async def test_crm_admin_routes_are_not_exposed(db_client, path):
    """CRM and dashboard endpoints are not served by the voice-agent backend."""
    response = await db_client.get(path)
    assert response.status_code == 404
