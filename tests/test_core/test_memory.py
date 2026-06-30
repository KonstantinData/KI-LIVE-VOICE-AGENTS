"""Tests für den MemoryManager."""

from unittest.mock import MagicMock

from src.core.memory import MemoryManager


def test_memory_manager_instantiation():
    """MemoryManager kann mit einer Mock-Session instanziiert werden."""
    mock_session = MagicMock()
    manager = MemoryManager(session=mock_session)
    assert manager is not None
