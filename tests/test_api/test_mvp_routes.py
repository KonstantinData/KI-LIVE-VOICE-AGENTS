"""Tests for production MVP API routes."""

import uuid

import pytest

from src.db.models.conversation import Conversation
from src.db.models.conversation_cost_event import ConversationCostEvent
from src.db.models.lead import Lead
from src.db.models.message import Message
from src.db.models.studio import Studio


async def _auth_headers(client) -> dict[str, str]:
    """Logs in with explicit test bootstrap credentials and returns auth headers."""
    response = await client.post(
        "/auth/login",
        json={"username": "admin", "password": "secret"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _seed_studio(db_session) -> Studio:
    """Creates the default test studio."""
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
async def test_current_studio_requires_auth(db_client, db_session):
    """Protected tenant endpoints require bearer auth."""
    await _seed_studio(db_session)
    response = await db_client.get("/studios/current")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_current_studio_returns_token_tenant(db_client, db_session):
    """The authenticated admin token resolves to the configured studio."""
    await _seed_studio(db_session)
    headers = await _auth_headers(db_client)

    response = await db_client.get("/studios/current", headers=headers)

    assert response.status_code == 200
    assert response.json()["slug"] == "mein-kuechenexperte"


@pytest.mark.asyncio
async def test_leads_are_tenant_scoped(db_client, db_session):
    """Lead list returns only rows from the authenticated studio."""
    studio = await _seed_studio(db_session)
    other_studio = Studio(
        id=uuid.uuid4(),
        name="Other",
        slug="other",
        api_key="other-key",
        is_active=True,
    )
    db_session.add(other_studio)
    db_session.add_all([
        Lead(
            id=uuid.uuid4(),
            studio_id=studio.id,
            visitor_id="v1",
            status="qualified",
            score=80,
            name="Test Lead",
        ),
        Lead(
            id=uuid.uuid4(),
            studio_id=other_studio.id,
            visitor_id="v2",
            status="qualified",
            score=99,
            name="Other Lead",
        ),
    ])
    await db_session.flush()
    headers = await _auth_headers(db_client)

    response = await db_client.get("/leads/", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Lead"


@pytest.mark.asyncio
async def test_dashboard_stats_count_current_studio(db_client, db_session):
    """Dashboard stats aggregate only current studio records."""
    studio = await _seed_studio(db_session)
    lead = Lead(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="v1",
        status="qualified",
        score=75,
    )
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        lead_id=lead.id,
        visitor_id="v1",
        status="active",
    )
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="assistant",
        content="Hallo",
    )
    db_session.add_all([lead, conversation, message])
    await db_session.flush()
    headers = await _auth_headers(db_client)

    response = await db_client.get("/dashboard/stats", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["leads_total"] == 1
    assert data["leads_qualified"] == 1
    assert data["active_conversations"] == 1
    assert data["average_lead_score"] == 75


@pytest.mark.asyncio
async def test_dashboard_cost_report_is_tenant_scoped(db_client, db_session):
    """Dashboard cost report aggregates only the authenticated studio."""
    studio = await _seed_studio(db_session)
    other_studio = Studio(
        id=uuid.uuid4(),
        name="Other",
        slug="other-costs",
        api_key="other-cost-key",
        is_active=True,
    )
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="v-cost",
        channel="voice",
        status="active",
    )
    other_conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=other_studio.id,
        visitor_id="v-other",
        channel="voice",
        status="active",
    )
    db_session.add_all([
        other_studio,
        conversation,
        other_conversation,
        ConversationCostEvent(
            id=uuid.uuid4(),
            studio_id=studio.id,
            conversation_id=conversation.id,
            event_type="realtime_response",
            channel="voice",
            component="voice_realtime",
            provider="openai",
            model="gpt-realtime-2.1",
            total_tokens=100,
            input_audio_tokens=20,
            output_audio_tokens=30,
            estimated_cost_usd=0.01,
            pricing_snapshot="test",
        ),
        ConversationCostEvent(
            id=uuid.uuid4(),
            studio_id=studio.id,
            conversation_id=conversation.id,
            event_type="upload_analysis",
            channel="voice",
            component="project_upload_analysis",
            provider="openai",
            model="gpt-4o-mini",
            total_tokens=50,
            input_image_tokens=10,
            estimated_cost_usd=0.02,
            pricing_snapshot="test",
        ),
        ConversationCostEvent(
            id=uuid.uuid4(),
            studio_id=other_studio.id,
            conversation_id=other_conversation.id,
            event_type="realtime_response",
            channel="voice",
            component="voice_realtime",
            provider="openai",
            model="gpt-realtime-2.1",
            total_tokens=999,
            estimated_cost_usd=9.99,
            pricing_snapshot="test",
        ),
    ])
    await db_session.flush()
    headers = await _auth_headers(db_client)

    response = await db_client.get("/dashboard/costs?days=30", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["event_count"] == 2
    assert data["summary"]["conversation_count"] == 1
    assert data["summary"]["total_tokens"] == 150
    assert data["summary"]["input_audio_tokens"] == 20
    assert data["summary"]["output_audio_tokens"] == 30
    assert data["summary"]["input_image_tokens"] == 10
    assert data["summary"]["estimated_cost_usd"] == 0.03
    assert {row["name"] for row in data["by_component"]} == {
        "voice_realtime",
        "project_upload_analysis",
    }
    assert len(data["top_conversations"]) == 1
    assert data["top_conversations"][0]["visitor_id"] == "v-cost"


@pytest.mark.asyncio
async def test_conversation_messages_are_available(db_client, db_session):
    """Admin can fetch messages for a tenant-owned conversation."""
    studio = await _seed_studio(db_session)
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="v1",
        status="active",
    )
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="user",
        content="Ich brauche eine Küche.",
    )
    db_session.add_all([conversation, message])
    await db_session.flush()
    headers = await _auth_headers(db_client)

    response = await db_client.get(
        f"/conversations/{conversation.id}/messages",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()[0]["content"] == "Ich brauche eine Küche."


@pytest.mark.asyncio
async def test_widget_config_is_public_for_active_studio(db_client, db_session):
    """Widget config exposes safe public fields without auth."""
    await _seed_studio(db_session)

    response = await db_client.get("/widget-config/?studio=mein-kuechenexperte")

    assert response.status_code == 200
    data = response.json()
    assert data["studio"] == "mein-kuechenexperte"
    assert data["agent_name"] == "KEA"
    assert data["agent_subtitle"] == "Küchen Expert Assistent"
    assert data["voice_enabled"] is True


@pytest.mark.asyncio
async def test_gdpr_export_and_delete_subject_data(db_client, db_session):
    """GDPR endpoints export and delete tenant-owned visitor data."""
    studio = await _seed_studio(db_session)
    lead = Lead(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor-gdpr",
        status="qualified",
        score=60,
        email="customer@example.test",
    )
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        lead_id=lead.id,
        visitor_id="visitor-gdpr",
        status="active",
    )
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="user",
        content="Bitte exportieren.",
    )
    db_session.add_all([lead, conversation, message])
    await db_session.flush()
    headers = await _auth_headers(db_client)

    export_response = await db_client.get(
        "/gdpr/export?visitor_id=visitor-gdpr",
        headers=headers,
    )
    assert export_response.status_code == 200
    exported = export_response.json()
    assert len(exported["leads"]) == 1
    assert len(exported["messages"]) == 1

    delete_response = await db_client.delete(
        "/gdpr/delete?visitor_id=visitor-gdpr",
        headers=headers,
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"]["leads"] == 1

    export_after_delete = await db_client.get(
        "/gdpr/export?visitor_id=visitor-gdpr",
        headers=headers,
    )
    assert export_after_delete.status_code == 200
    assert export_after_delete.json()["leads"] == []
