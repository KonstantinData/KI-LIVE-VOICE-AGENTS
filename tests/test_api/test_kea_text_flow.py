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
    assert "42,80 EUR" in price.content
    assert [choice.id for choice in price.choices] == [
        "buy_budget",
        "buy_studio",
        "offer_price",
    ]

    upload = await flow.handle(
        conversation,
        message_text="Ich möchte ein PDF hochladen",
    )
    assert "Upload-Bereich im Widget" in upload.content
    assert upload.choices[0].id == "back_start"

    messages = await _messages(db_session, conversation)
    assert any(message.tool_calls for message in messages if message.role == "assistant")
