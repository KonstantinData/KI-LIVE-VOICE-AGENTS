"""Bounded OpenAI pilot for Olivia mail; no tools, retrieval, or conversation state."""
from __future__ import annotations

import asyncio
import json

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr

MODEL = "gpt-6-luna"
ENDPOINT = "https://api.openai.com/v1/responses"
MAX_INPUT_BYTES = 24_000
MAX_OUTPUT_TOKENS = 512
MAX_RESPONSE_BYTES = 64_000


class MailOpenAIError(Exception):
    """A sanitized provider failure; never retain HTTP bodies or credentials."""


class MailDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    answer: str = Field(min_length=1, max_length=6000)
    prepared_actions: list = Field(max_length=0)


def _unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate JSON property")
        result[name] = value
    return result


def parse_json(raw):
    return json.loads(raw, object_pairs_hook=_unique_object)


def request_bytes(messages: list[dict[str, str]]) -> bytes:
    """Only an isolated system instruction and a bounded untrusted user projection."""
    if len(messages) != 2 or [item.get("role") for item in messages] != ["system", "user"]:
        raise MailOpenAIError("mail_openai_input_invalid")
    if any(set(item) != {"role", "content"} or not isinstance(item["content"], str)
           for item in messages):
        raise MailOpenAIError("mail_openai_input_invalid")
    body = {
        "model": MODEL,
        "input": messages,
        "reasoning": {"effort": "none"},
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "store": False,
        "service_tier": "default",
        "text": {"format": {
            "type": "json_schema", "name": "olivia_mail_answer", "strict": True,
            "schema": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "answer": {"type": "string"},
                    "prepared_actions": {
                        "type": "array", "items": {"type": "string"}, "maxItems": 0,
                    },
                },
                "required": ["answer", "prepared_actions"],
            },
        }},
    }
    encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_INPUT_BYTES:
        raise MailOpenAIError("mail_openai_input_too_large")
    return encoded


def parse_answer(raw: bytes) -> str:
    """Reject refusals, incomplete answers, action calls, and unstructured output."""
    body = parse_json(raw.decode("utf-8", errors="strict"))
    if body.get("status") != "completed" or body.get("error") or body.get("incomplete_details"):
        raise ValueError("incomplete response")
    output = body["output"]
    if len(output) != 1 or output[0].get("type") != "message":
        raise ValueError("unexpected output")
    message = output[0]
    if message.get("role") != "assistant" or message.get("status") != "completed":
        raise ValueError("unexpected message")
    content = message["content"]
    if len(content) != 1 or content[0].get("type") != "output_text":
        raise ValueError("unexpected content")
    # Tools are disabled. Citations or other provider annotations indicate drift.
    if content[0].get("annotations"):
        raise ValueError("unexpected annotations")
    draft = MailDraft.model_validate(parse_json(content[0]["text"]))
    if not draft.answer.strip() or "\x00" in draft.answer or len(draft.answer.split()) > 60:
        raise ValueError("invalid answer")
    return draft.answer


async def generate_answer(api_key: SecretStr, encoded: bytes) -> str:
    """One attempt only. No redirects, proxy inheritance, SDK retries, or fallbacks."""
    if not api_key.get_secret_value().strip() or len(encoded) > MAX_INPUT_BYTES:
        raise MailOpenAIError("mail_openai_configuration_unavailable")
    try:
        async with asyncio.timeout(20), httpx.AsyncClient(
            timeout=httpx.Timeout(20), follow_redirects=False, trust_env=False,
        ) as client:
            async with client.stream(
                "POST", ENDPOINT, content=encoded,
                headers={"Authorization": "Bearer " + api_key.get_secret_value(),
                         "Content-Type": "application/json"},
            ) as response:
                if response.status_code != 200:
                    raise ValueError("provider status denied")
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise ValueError("provider response too large")
        return parse_answer(bytes(raw))
    except Exception:
        raise MailOpenAIError("mail_openai_generation_unavailable") from None
