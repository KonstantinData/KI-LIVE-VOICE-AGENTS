"""Tests for the KnowledgeBase semantic search fallback behavior."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.embeddings import EmbeddingClient
from src.core.knowledge import KnowledgeBase


@pytest.mark.asyncio
async def test_search_returns_empty_list_when_embedding_fails(monkeypatch):
    """Knowledge search should not fail the chat when embeddings are unavailable."""

    async def fail_embed(self: EmbeddingClient, text: str) -> list[float]:
        raise RuntimeError("embedding provider unavailable")

    session = AsyncMock()
    monkeypatch.setattr(EmbeddingClient, "embed", fail_embed)

    knowledge = KnowledgeBase(session)
    result = await knowledge.search("Hallo", studio_id=uuid4())

    assert result == []
    session.execute.assert_not_called()
