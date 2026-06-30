"""Tests für die BaseAgent-Basisklasse."""

from unittest.mock import MagicMock

from src.agents._template.agent import TemplateAgent
from src.core.tool_registry import ToolRegistry


def test_template_agent_instantiation():
    """TemplateAgent kann mit einer Mock-Session instanziiert werden."""
    mock_session = MagicMock()
    agent = TemplateAgent(session=mock_session)
    assert agent is not None


def test_template_agent_get_tools():
    """get_tools() gibt eine ToolRegistry zurück."""
    mock_session = MagicMock()
    agent = TemplateAgent(session=mock_session)
    tools = agent.get_tools()
    assert isinstance(tools, ToolRegistry)


def test_template_agent_knowledge_categories():
    """get_knowledge_categories() gibt eine Liste zurück."""
    mock_session = MagicMock()
    agent = TemplateAgent(session=mock_session)
    categories = agent.get_knowledge_categories()
    assert isinstance(categories, list)


def test_template_agent_system_prompt():
    """get_system_prompt() gibt einen nicht-leeren String zurück."""
    mock_session = MagicMock()
    agent = TemplateAgent(session=mock_session)

    mock_studio = MagicMock()
    mock_studio.name = "Test Studio"

    prompt = agent.get_system_prompt(
        studio=mock_studio,
        knowledge_snippets=["Test Wissen"],
        lead_summary="Test Lead",
    )
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "Test Studio" in prompt
