"""
Claude API Wrapper
==================
What:    Wrapper around Anthropic's Claude API for LLM interactions.
Does:    Handles chat completions with tool use, retry logic, token tracking, and prompt caching.
Why:     Centralizes all LLM communication; provides consistent error handling and observability.
Who:     BaseAgent (via process_message), any agent that needs LLM responses.
Depends: anthropic, structlog, src.api.config, src.core.types
"""

import asyncio
from typing import Any

import structlog
from anthropic import AsyncAnthropic, APIStatusError, RateLimitError
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from src.api.config import get_settings
from src.core.types import LLMResponse

log = structlog.get_logger()
settings = get_settings()


class LLMClient:
    """
    Wrapper um die Anthropic Claude API.

    - Unterstützt Tool Use (function calling)
    - Retry-Logic mit Exponential Backoff bei Rate-Limits
    - Token-Counting für Kostentracking
    - Prompt Caching für System-Prompts
    """

    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.anthropic_model
        self._max_tokens = settings.anthropic_max_tokens
        self._openai_model = settings.openai_chat_model

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_retries: int = 3,
    ) -> LLMResponse:
        """
        Calls Claude and returns a structured response.

        Implements retry logic with exponential backoff for rate limit errors.
        Uses prompt caching for system prompts to reduce costs.
        
        Args:
            system_prompt: System prompt defining agent behavior
            messages: Conversation history in Claude format
            tools: Optional list of tool definitions for function calling
            max_retries: Maximum number of retry attempts on rate limit
            
        Returns:
            LLMResponse with content, tool calls, and token usage
            
        Raises:
            RateLimitError: If max retries exceeded
            APIStatusError: On other API errors
        """
        for attempt in range(max_retries):
            try:
                kwargs: dict[str, Any] = {
                    "model": self._model,
                    "max_tokens": self._max_tokens,
                    "system": [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    "messages": messages,
                }
                if tools:
                    kwargs["tools"] = tools

                response = await self._client.messages.create(**kwargs)

                # NOTE: Claude returns content blocks that can be either text or tool_use.
                # We extract both types and return them in a structured format.
                content_text = ""
                tool_calls: list[dict[str, Any]] = []

                for block in response.content:
                    if block.type == "text":
                        content_text = block.text
                    elif block.type == "tool_use":
                        tool_calls.append({
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })

                log.info(
                    "llm.response",
                    model=self._model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    stop_reason=response.stop_reason,
                )

                return LLMResponse(
                    content=content_text,
                    tool_calls=tool_calls,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    stop_reason=response.stop_reason or "end_turn",
                )

            except RateLimitError:
                wait = 2**attempt
                log.warning("llm.rate_limit", attempt=attempt, wait=wait)
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait)
                else:
                    raise
            except APIStatusError as e:
                log.error("llm.api_error", status=e.status_code, message=str(e))
                if settings.openai_api_key:
                    return await self._chat_with_openai_fallback(
                        system_prompt=system_prompt,
                        messages=messages,
                    )
                raise

        msg = "Max Retries überschritten"
        raise RuntimeError(msg)

    async def _chat_with_openai_fallback(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
    ) -> LLMResponse:
        """
        Calls OpenAI Chat Completions when Anthropic is unavailable.

        Args:
            system_prompt: System prompt defining agent behavior
            messages: Conversation history

        Returns:
            LLMResponse with text content and token usage
        """
        openai_messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt}
        ]
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            openai_messages.append({"role": role, "content": content})

        response = await self._openai_client.chat.completions.create(
            model=self._openai_model,
            messages=openai_messages,
            max_tokens=self._max_tokens,
        )
        content = response.choices[0].message.content or ""
        usage = response.usage

        log.warning(
            "llm.openai_fallback_response",
            model=self._openai_model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )
        return LLMResponse(
            content=content,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            stop_reason=response.choices[0].finish_reason or "stop",
        )
