"""Bounded OpenAI pilot for Olivia mail; no tools, retrieval, or conversation state."""
from __future__ import annotations

import asyncio
import json

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from src.api.services.liquisto_openai_budget import OpenAIHttpBudget

MODEL = "gpt-6-luna"
ENDPOINT = "https://api.openai.com/v1/responses"
COUNT_ENDPOINT = ENDPOINT + "/input_tokens"
MAX_INPUT_BYTES = 24_000
MAX_INPUT_TOKENS = 8192
MAX_OUTPUT_TOKENS = 512
MAX_RESPONSE_BYTES = 64_000
PRICE_SNAPSHOT = "openai-gpt-6-luna-standard-20261010"
# Micro-USD per million tokens, above cache-write and regional standard rates.
INPUT_PRICE_CEILING = 250_000
OUTPUT_PRICE_CEILING = 600_000
BUDGET_MICRO_USD = 100_000
MAX_ATTEMPTS = 5
RESERVATION_MICRO_USD = 10_000


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


def response_text(raw: bytes, *, expected_input_tokens: int, max_output_tokens: int) -> str:
    """Reject refusals, incomplete answers, action calls, and token-accounting drift."""
    body = parse_json(raw.decode("utf-8", errors="strict"))
    if body.get("status") != "completed" or body.get("error") or body.get("incomplete_details"):
        raise ValueError("incomplete response")
    usage = body.get("usage", {})
    if (type(usage.get("input_tokens")) is not int
            or usage["input_tokens"] != expected_input_tokens
            or type(usage.get("output_tokens")) is not int
            or not 0 < usage["output_tokens"] <= max_output_tokens):
        raise ValueError("provider usage drift")
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
    return content[0]["text"]


def validate_draft(value) -> str:
    draft = MailDraft.model_validate(value)
    if not draft.answer.strip() or "\x00" in draft.answer or len(draft.answer.split()) > 60:
        raise ValueError("invalid answer")
    return draft.answer


async def generate_answer(api_key: SecretStr, encoded: bytes, *, budget: OpenAIHttpBudget) -> str:
    try:
        body = parse_json(encoded)
        if encoded != request_bytes(body["input"]):
            raise ValueError
        raw, count = await generate_response(api_key, encoded, budget=budget)
        return validate_draft(parse_json(response_text(raw, expected_input_tokens=count,
                                                       max_output_tokens=MAX_OUTPUT_TOKENS)))
    except Exception:
        raise MailOpenAIError("mail_openai_generation_unavailable") from None


async def generate_response(api_key: SecretStr, encoded: bytes, *, budget: OpenAIHttpBudget) -> tuple[bytes, int]:
    """One attempt only. No redirects, proxy inheritance, SDK retries, or fallbacks."""
    if not api_key.get_secret_value().strip() or len(encoded) > MAX_INPUT_BYTES:
        raise MailOpenAIError("mail_openai_configuration_unavailable")
    try:
        body = parse_json(encoded)
        if (body["model"] != MODEL or body["store"] is not False
                or body["service_tier"] != "default" or body["reasoning"] != {"effort": "none"}
                or body["max_output_tokens"] not in {MAX_OUTPUT_TOKENS, 5 * MAX_OUTPUT_TOKENS}
                or set(body) != {"model", "input", "reasoning", "max_output_tokens", "store", "service_tier", "text"}):
            raise ValueError("provider contract drift")
        count_payload = json.dumps(
            {name: body[name] for name in ("model", "input", "text", "reasoning")},
            ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")
        async with asyncio.timeout(20), httpx.AsyncClient(
            timeout=httpx.Timeout(20), follow_redirects=False, trust_env=False,
        ) as client:
            headers = {"Authorization": "Bearer " + api_key.get_secret_value(),
                       "Content-Type": "application/json"}

            async def bounded_post(url, payload, limit):
                budget.reserve("count" if url == COUNT_ENDPOINT else "generate")
                async with client.stream("POST", url, content=payload, headers=headers) as response:
                    if response.status_code != 200:
                        raise ValueError("provider status denied")
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        raw.extend(chunk)
                        if len(raw) > limit:
                            raise ValueError("provider response too large")
                return bytes(raw)

            # The official counter includes role boundaries and the output schema.
            # Send exactly the same token-bearing fields; no local tokenizer estimate.
            count = parse_json(await bounded_post(COUNT_ENDPOINT, count_payload, 1024))
            if (set(count) != {"object", "input_tokens"}
                    or count["object"] != "response.input_tokens"
                    or type(count["input_tokens"]) is not int
                    or not 1 <= count["input_tokens"] <= MAX_INPUT_TOKENS):
                raise ValueError("provider token count denied")
            raw = await bounded_post(ENDPOINT, encoded, MAX_RESPONSE_BYTES)
        return raw, count["input_tokens"]
    except Exception:
        raise MailOpenAIError("mail_openai_generation_unavailable") from None
