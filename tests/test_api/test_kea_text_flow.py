"""Tests for the deterministic KEA text flow."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from src.api.services.kea_text_flow import KeaTextFlow
from src.db.models.conversation import Conversation
from src.db.models.message import Message
from tests.test_api.upload_helpers import seed_studio


async def _conversation(db_session, visitor_id: str = "kea-flow-visitor") -> Conversation:
    studio = await seed_studio(db_session)
    conversation = Conversation(
        studio_id=studio.id,
        visitor_id=visitor_id,
        channel="widget",
        status="active",
    )
    db_session.add(conversation)
    await db_session.flush()
    return conversation


async def _messages(db_session, conversation: Conversation) -> list[Message]:
    result = await db_session.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_kea_text_flow_starts_with_clean_main_paths(db_session):
    conversation = await _conversation(db_session)
    response = await KeaTextFlow(db_session).start(conversation)

    assert "Ich bin KEA" in response.content
    assert [choice.id for choice in response.choices] == [
        "start_build",
        "start_buy",
        "start_offer",
        "start_free",
    ]
    assert "Beratungs-Assistent" not in response.content


@pytest.mark.asyncio
async def test_kea_text_flow_offer_path_reaches_summary(db_session):
    conversation = await _conversation(db_session)
    flow = KeaTextFlow(db_session)

    await flow.start(conversation)
    response = await flow.handle(
        conversation,
        message_text="",
        action_id="start_offer",
        action_label="Ich habe ein Angebot und möchte es besser einschätzen können",
    )
    assert "Angebot" in response.content
    assert [choice.id for choice in response.choices] == [
        "offer_plan",
        "offer_scope",
        "offer_price",
        "offer_multi",
    ]

    await flow.handle(
        conversation,
        message_text="",
        action_id="offer_price",
        action_label="Preis / Vergleichbarkeit einordnen",
    )
    await flow.handle(
        conversation,
        message_text="",
        action_id="offer_soon",
        action_label="Ich will bald entscheiden",
    )
    await flow.handle(
        conversation,
        message_text="",
        action_id="offer_week",
        action_label="In 1 Woche",
    )
    summary = await flow.handle(
        conversation,
        message_text="",
        action_id="offer_skip",
        action_label="Ohne Zusatz weiter",
    )

    assert "Zwischenstand" in summary.content
    assert "Angebot / Planung einschätzen" in summary.content
    assert "preis vergleichbarkeit" in summary.content
    assert [choice.id for choice in summary.choices] == [
        "next_upload",
        "next_contact",
        "back_start",
    ]


@pytest.mark.asyncio
async def test_kea_text_flow_handles_strategy_check_and_upload_intents(db_session):
    conversation = await _conversation(db_session)
    flow = KeaTextFlow(db_session)

    await flow.start(conversation)
    price = await flow.handle(
        conversation,
        message_text="Was kostet der Strategie-Check?",
    )
    assert "42,80" not in price.content
    assert "Vorgespräch" in price.content
    assert "Preis" in price.content
    assert [choice.id for choice in price.choices] == [
        "next_contact",
        "back_start",
    ]

    upload = await flow.handle(
        conversation,
        message_text="Ich möchte ein PDF hochladen",
    )
    assert "Upload-Bereich im Chatfenster" in upload.content
    assert upload.choices[0].id == "back_start"

    messages = await _messages(db_session, conversation)
    assert any(message.tool_calls for message in messages if message.role == "assistant")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Was kostet die Planung mit meinen Fotos?", "service-pricing"),
        ("Ist ein Quick-Check kostenlos?", "service-pricing"),
        ("Planen Sie auch Backkitchen und Wohnräume?", "planning-services"),
        ("Übernehmen Sie Lieferung und Montage?", "service-boundaries"),
        ("Welche Unterlagen brauche ich?", "project-documents"),
        ("Wie läuft das Vorgespräch ab?", "consultation-process"),
        ("Wie lautet Ihre E-Mail-Adresse?", "public-contact"),
    ],
)
async def test_kea_text_flow_answers_website_questions_and_keeps_handoff_working(
    db_session, question, expected
):
    """Public text answers use curated facts and retain the next-step actions."""
    from src.tenants.knowledge import get_tenant_knowledge_for_studio

    conversation = await _conversation(db_session)
    flow = KeaTextFlow(db_session)
    response = await flow.handle(conversation, message_text=question)
    source = get_tenant_knowledge_for_studio("mein-kuechenexperte")
    chunk = next(item for item in source.chunks if item.id == expected)
    assert response.content == chunk.content
    assert conversation.metadata_["kea_text_flow"]["node"] == f"website_{expected}"
    handoff = await flow.handle(conversation, message_text="", action_id="next_contact")
    assert "Kontaktformular" in handoff.content


def test_kea_text_flow_does_not_invent_missing_website_facts(monkeypatch):
    """Missing curated content must not revive obsolete fixed-price promises."""
    monkeypatch.setattr(
        "src.api.services.kea_text_flow.get_tenant_knowledge_for_studio", lambda _: None
    )
    response = KeaTextFlow(None)._global_intent("Was kostet der Strategie-Check?")
    assert "keine gesicherten Informationen" in response.text
    assert "42,80" not in response.text
