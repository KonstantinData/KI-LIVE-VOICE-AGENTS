"""Private provider adapter; HTTP is always mocked and keys are invented."""

import json

import httpx
import pytest
from pydantic import SecretStr

from src.api.services import liquisto_direct_draft as direct
from src.api.services.liquisto_mail_openai import MailOpenAIError


def response():
    return {
        "status": "completed",
        "usage": {"input_tokens": 1024, "output_tokens": 20},
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "annotations": [],
                        "text": json.dumps(
                            {
                                "answer": "Welchen Auftrag meinst du?",
                                "prepared_actions": [],
                            }
                        ),
                    }
                ],
            }
        ],
    }


def test_default_off_never_calls_authority_key_or_http(monkeypatch):
    def forbidden(*_a, **_k):
        pytest.fail("inactive port called")

    monkeypatch.setattr(direct.httpx, "AsyncClient", forbidden)
    provider = direct.DirectDraftProvider(key_supplier=forbidden)
    with pytest.raises(MailOpenAIError, match="disabled"):
        provider.draft(b"not even parsed", before_http=forbidden)


def test_debit_denial_precedes_key_and_http(monkeypatch):
    monkeypatch.setattr(
        direct.httpx, "AsyncClient", lambda **_: pytest.fail("HTTP client opened")
    )
    provider = direct.DirectDraftProvider(
        enabled=True, key_supplier=lambda: pytest.fail("key read")
    )

    def denied():
        raise ValueError("synthetic quota/authority denial")

    with pytest.raises(MailOpenAIError, match="no_retry"):
        provider.draft(b'{"subject":"Fixture","new_text":"Hallo"}', before_http=denied)


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "access",
        "timeout",
        "redirect",
        "usage",
        "output-usage",
        "refusal",
        "actions",
        "annotations",
        "long",
        "oversize",
        "malformed",
    ],
)
def test_one_call_fixed_model_no_store_tools_counter_or_fallback(monkeypatch, failure):
    events, requests = [], []
    body = response()
    if failure == "usage":
        body["usage"]["input_tokens"] = 24577
    elif failure == "output-usage":
        body["usage"]["output_tokens"] = 513
    elif failure == "refusal":
        body["output"][0]["content"][0]["type"] = "refusal"
    elif failure == "annotations":
        body["output"][0]["content"][0]["annotations"] = [
            {"url": "https://example.invalid"}
        ]
    elif failure in {"actions", "long"}:
        draft = {
            "answer": "word " * 61 if failure == "long" else "Fixture.",
            "prepared_actions": ["send"] if failure == "actions" else [],
        }
        body["output"][0]["content"][0]["text"] = json.dumps(draft)

    def handle(request):
        events.append("http")
        requests.append(request)
        assert str(request.url) == direct.ENDPOINT
        if failure == "timeout":
            raise httpx.ReadTimeout("synthetic-private-provider-error", request=request)
        if failure == "oversize":
            return httpx.Response(200, content=b"x" * 64001)
        if failure == "malformed":
            return httpx.Response(200, content=b"not JSON")
        return httpx.Response(
            403 if failure == "access" else 302 if failure == "redirect" else 200,
            json=body,
        )

    original = httpx.AsyncClient

    def client(**kwargs):
        assert kwargs["follow_redirects"] is False and kwargs["trust_env"] is False
        return original(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(direct.httpx, "AsyncClient", client)

    def key():
        events.append("key")
        return SecretStr("fixture-only-key")

    provider = direct.DirectDraftProvider(enabled=True, key_supplier=key)

    def debit():
        events.append("debit")
        return lambda: None

    raw = b'{"subject":"Fixture","new_text":"Hallo"}'
    if failure:
        with pytest.raises(MailOpenAIError, match="no_retry") as error:
            provider.draft(raw, before_http=debit)
        assert "private-provider" not in str(error.value)
    else:
        assert provider.draft(raw, before_http=debit) == "Welchen Auftrag meinst du?"
    assert events == ["debit", "key", "http"] and len(requests) == 1
    sent = json.loads(requests[0].content)
    assert sent["model"] == "gpt-6-luna" and sent["store"] is False
    assert sent["reasoning"] == {"effort": "none"} and sent["service_tier"] == "default"
    assert sent["max_output_tokens"] == 512 and len(requests[0].content) <= 8192
    assert set(sent) == {
        "model",
        "input",
        "reasoning",
        "store",
        "service_tier",
        "max_output_tokens",
        "text",
    }
    projected = json.loads(sent["input"][1]["content"])
    assert projected["context"] == []
    assert json.loads(projected["prompt"]) == {
        "subject": "Fixture",
        "new_text": "Hallo",
    }


@pytest.mark.parametrize(
    "raw",
    [
        b'{"subject":"Fixture","new_text":"Hallo","context":[]}',
        b'{"subject":"Fixture","new_text":"Hallo","new_text":"other"}',
        b'{"subject":"Fixture","new_text":null}',
        b'{"subject":"Fixture","new_text":true}',
        b'{"subject":"Fixture\\nInjected","new_text":"Hallo"}',
        json.dumps(
            {"subject": "Fixture", "new_text": "🙂" * 2000}, ensure_ascii=False
        ).encode(),
    ],
)
def test_closed_projection_denies_before_debit_key_or_http(raw, monkeypatch):
    def forbidden(*_a, **_k):
        pytest.fail("input denial must precede I/O")

    monkeypatch.setattr(direct.httpx, "AsyncClient", forbidden)
    provider = direct.DirectDraftProvider(enabled=True, key_supplier=forbidden)
    with pytest.raises(MailOpenAIError):
        provider.draft(raw, before_http=forbidden)


def test_conservative_generation_bound_fits_the_host_reservation():
    assert ((8192 + 16384) * 250000 + 512 * 600000 + 999999) // 1000000 == 6452 < 10000
