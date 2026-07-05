"""Tests für die BaseAgent-Basisklasse."""

from unittest.mock import MagicMock
import uuid

from src.agents.lisa.agent import LisaAgent
from src.agents.lisa.system_prompt import build_lisa_system_prompt
from src.agents._template.agent import TemplateAgent
from src.core.tool_registry import ToolRegistry
from src.db.models.conversation import Conversation
from src.db.models.studio import Studio


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


def test_kea_system_prompt_contains_controlled_intake_contract():
    """The text prompt keeps KEA in guided intake instead of expert consulting."""
    studio = Studio(
        id=uuid.uuid4(),
        name="Mein Küchenexperte",
        slug="mein-kuechenexperte",
        api_key="test",
        is_active=True,
        config={},
    )

    prompt = build_lisa_system_prompt(
        studio=studio,
        knowledge_snippets=["Quick-Check hilft bei der ersten Einordnung."],
        lead_summary=None,
    )

    assert "kontrollierte Projekt-Einordnung" in prompt
    assert "Fragen zu Angeboten" in prompt
    assert "never promise" in prompt
    assert "KI-KUECHENBERATER" in prompt
    assert "keine verbindliche Küchenberatung" in prompt


def test_kea_text_agent_disables_appointment_tool_for_mein_kuechenexperte():
    """KEA may capture intent, but does not book expert-consulting appointments."""
    agent = LisaAgent(session=MagicMock())
    studio = Studio(
        id=uuid.uuid4(),
        name="Mein Küchenexperte",
        slug="mein-kuechenexperte",
        api_key="test",
        is_active=True,
        config={},
    )
    conversation = Conversation(
        id=uuid.uuid4(),
        studio_id=studio.id,
        visitor_id="visitor",
        channel="widget",
        status="active",
    )

    tools = agent.get_contextual_tools(conversation, studio)

    assert "extract_lead_data" in tools.names
    assert "book_appointment" not in tools.names
