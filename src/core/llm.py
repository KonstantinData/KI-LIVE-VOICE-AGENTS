"""
OpenAI LLM Wrapper
==================
What:    Wrapper around OpenAI chat completions for agent interactions.
Does:    Handles chat completions, tool calls, retry logic, and token tracking.
Why:     Centralizes all LLM communication and keeps provider usage consistent.
Who:     BaseAgent and any agent that needs LLM responses.
Depends: openai, structlog, src.api.config, src.core.types
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog
from openai import APIStatusError, AsyncOpenAI, RateLimitError

from src.api.config import get_settings
from src.core.types import LLMResponse

log = structlog.get_logger()
settings = get_settings()


class LLMClient:
    """OpenAI-backed LLM client with tool calling support."""

    def __init__(self) -> None:
        self._client = (
            AsyncOpenAI(api_key=settings.openai_api_key)
            if settings.openai_api_key
            else None
        )
        self._model = settings.openai_chat_model
        self._max_tokens = settings.openai_chat_max_tokens

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_retries: int = 3,
    ) -> LLMResponse:
        """Calls OpenAI and returns a structured response."""
        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is required for chat completions")

        openai_messages = self._to_openai_messages(system_prompt, messages)
        for attempt in range(max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=openai_messages,
                    tools=tools,
                    max_tokens=self._max_tokens,
                )
                choice = response.choices[0]
                message = choice.message
                tool_calls = []
                for tool_call in message.tool_calls or []:
                    arguments = tool_call.function.arguments or "{}"
                    try:
                        parsed_arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        parsed_arguments = {}
                    tool_calls.append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "input": parsed_arguments,
                    })

                usage = response.usage
                log.info(
                    "llm.response",
                    provider="openai",
                    model=self._model,
                    input_tokens=usage.prompt_tokens if usage else 0,
                    output_tokens=usage.completion_tokens if usage else 0,
                    stop_reason=choice.finish_reason,
                )
                return LLMResponse(
                    content=message.content or "",
                    tool_calls=tool_calls,
                    input_tokens=usage.prompt_tokens if usage else 0,
                    output_tokens=usage.completion_tokens if usage else 0,
                    stop_reason=choice.finish_reason or "stop",
                )
            except RateLimitError:
                wait = 2**attempt
                log.warning("llm.rate_limit", provider="openai", attempt=attempt, wait=wait)
                if attempt >= max_retries - 1:
                    raise
                await asyncio.sleep(wait)
            except APIStatusError as exc:
                log.error("llm.api_error", provider="openai", status=exc.status_code, message=str(exc))
                raise

        raise RuntimeError("Max retries exceeded")

    def _to_openai_messages(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Normalizes internal message dictionaries for OpenAI chat completions."""
        normalized: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for message in messages:
            role = str(message.get("role", "user"))
            if role == "tool":
                normalized.append({
                    "role": "tool",
                    "tool_call_id": str(message.get("tool_call_id", "")),
                    "content": str(message.get("content", "")),
                })
                continue
            item: dict[str, Any] = {
                "role": role if role in {"user", "assistant", "system"} else "user",
                "content": message.get("content", ""),
            }
            if message.get("tool_calls"):
                item["tool_calls"] = message["tool_calls"]
            normalized.append(item)
        return normalized
