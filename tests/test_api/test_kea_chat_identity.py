"""Reject unconfigured chat tenants before creating or dispatching a conversation."""

from unittest.mock import AsyncMock, MagicMock
from contextlib import asynccontextmanager
import json

import pytest
from fastapi import WebSocketDisconnect
from sqlalchemy import select

from src.api.websocket import chat_handler
from src.db.models.conversation import Conversation
from src.db.models.message import Message
from src.db.models.studio import Studio


@pytest.mark.asyncio
@pytest.mark.parametrize("slug", ["unknown-studio", "mein-kuechenexperte"])
async def test_missing_chat_profile_does_not_fall_back_to_kea(monkeypatch, slug):
    studio = Studio(slug=slug, name="Test", is_active=True)
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = studio
    session.execute = AsyncMock(return_value=result)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    monkeypatch.setattr(chat_handler, "AsyncSessionLocal", lambda: context)
    monkeypatch.setattr(chat_handler, "get_tenant_profile_for_studio", lambda _: None)
    monkeypatch.setattr(chat_handler, "_origin_allowed", lambda _: True)
    monkeypatch.setattr(chat_handler, "manager", MagicMock(connect=AsyncMock()))
    websocket = AsyncMock()
    websocket.headers = {}

    await chat_handler.handle_chat(websocket, slug, "test-visitor", consent_given=True)

    websocket.close.assert_awaited_once_with(code=4003)
    session.add.assert_not_called()
    websocket.receive_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_kea_websocket_preserves_deterministic_chat_and_closes_without_llm(
    db_session, monkeypatch,
):
    """Exercise the moved flow through the transport and persist a real test turn."""
    studio = Studio(
        slug="mein-kuechenexperte", name="Mein Küchenexperte", api_key="test",
        is_active=True, config={},
    )
    db_session.add(studio)
    await db_session.flush()

    @asynccontextmanager
    async def session_context():
        yield db_session

    monkeypatch.setattr(chat_handler, "AsyncSessionLocal", session_context)
    monkeypatch.setattr(chat_handler, "_origin_allowed", lambda _: True)
    monkeypatch.setattr(chat_handler, "manager", MagicMock(connect=AsyncMock()))
    llm_chat = AsyncMock(side_effect=AssertionError("Deterministic chat must not call an LLM"))
    monkeypatch.setattr("src.core.llm.LLMClient.chat", llm_chat)
    websocket = AsyncMock()
    websocket.headers = {}
    websocket.receive_text.side_effect = [
        json.dumps({"message": "Ich möchte eine neue Küche."}), WebSocketDisconnect(),
    ]

    await chat_handler.handle_chat(
        websocket, studio.slug, "test-visitor", consent_given=True,
    )

    sent = [call.args[0] for call in websocket.send_json.await_args_list]
    assert sent[0]["type"] == "session"
    replies = [item for item in sent if item["type"] == "message"]
    assert len(replies) == 2
    assert "KEA" in replies[0]["content"]
    assert replies[0]["choices"]
    assert not any(item["type"] == "error" for item in sent)
    conversation = (await db_session.execute(select(Conversation))).scalar_one()
    assert conversation.status == "closed"
    assert conversation.summary
    messages = (await db_session.execute(select(Message))).scalars().all()
    assert [message.role for message in messages].count("user") == 1
    llm_chat.assert_not_awaited()
