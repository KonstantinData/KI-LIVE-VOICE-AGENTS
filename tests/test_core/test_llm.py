"""Tests für den LLM-Wrapper (mit Mocks — kein echter API-Call)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.types import LLMResponse


def test_llm_response_model():
    """LLMResponse kann korrekt instanziiert werden."""
    response = LLMResponse(
        content="Hallo!",
        tool_calls=[],
        input_tokens=10,
        output_tokens=5,
        stop_reason="end_turn",
    )
    assert response.content == "Hallo!"
    assert response.input_tokens == 10
    assert response.stop_reason == "end_turn"


@pytest.mark.asyncio
@patch("src.core.llm.AsyncOpenAI")
async def test_llm_client_chat(mock_openai_class):
    """LLMClient.chat() ruft die OpenAI API auf und gibt LLMResponse zurück."""
    # Mock aufbauen
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test-Antwort"
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].finish_reason = "stop"
    mock_response.usage.prompt_tokens = 20
    mock_response.usage.completion_tokens = 10

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_openai_class.return_value = mock_client

    from src.core.llm import LLMClient

    llm = LLMClient()
    llm._client = mock_client

    response = await llm.chat(
        system_prompt="Du bist ein Test-Agent.",
        messages=[{"role": "user", "content": "Hallo"}],
    )

    assert isinstance(response, LLMResponse)
    assert response.content == "Test-Antwort"
    assert response.input_tokens == 20
