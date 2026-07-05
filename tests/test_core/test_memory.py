"""Tests für den MemoryManager."""

from unittest.mock import MagicMock
import uuid

import pytest

from src.core.memory import MemoryManager
from src.db.models.conversation import Conversation
from src.db.models.message import Message
from src.db.models.studio import Studio


def test_memory_manager_instantiation():
    """MemoryManager kann mit einer Mock-Session instanziiert werden."""
    mock_session = MagicMock()
    manager = MemoryManager(session=mock_session)
    assert manager is not None


@pytest.mark.asyncio
async def test_memory_context_includes_prior_visitor_sessions(db_session):
    """Agent context includes compact history from earlier sessions of the visitor."""
    studio = Studio(
        id=uuid.uuid4(),
        name="Mein Küchenexperte",
        slug="memory-studio",
        api_key=f"memory-{uuid.uuid4()}",
        is_active=True,
    )
    previous = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor-memory",
        status="closed",
        summary="Der Besucher plant eine grifflose Küche mit Insel.",
    )
    current = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor-memory",
        status="active",
    )
    upload = Message(
        id=uuid.uuid4(),
        conversation_id=previous.id,
        role="user",
        content="Der Kunde hat eine Projektdatei hochgeladen: grundriss.pdf (application/pdf, 1234 Bytes).",
    )
    db_session.add_all([studio, previous, current, upload])
    await db_session.flush()

    context = await MemoryManager(db_session).get_context(current.id, studio.id)

    assert context.lead_summary is not None
    assert "grifflose Küche" in context.lead_summary
    assert "grundriss.pdf" in context.lead_summary
