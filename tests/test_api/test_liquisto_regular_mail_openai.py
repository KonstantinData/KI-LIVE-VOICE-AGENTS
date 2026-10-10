"""Regular mail contract and provider failures; synthetic HTTP only."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from src.api.services import liquisto_mail_provider as provider
from tests.test_api import test_liquisto_mail_route as route_fixtures
from tests.test_api.test_liquisto_mail_route import post, signed

setup = route_fixtures.setup


def payload():
    body = route_fixtures.payload()
    body["context"][0]["content"] = json.dumps([{
        "record_id": "synthetic-task", "version": 1, "updated_at": None,
        "summary": "Review inventory", "occurred_at": "2026-10-10T12:00:00Z",
        "status": "open", "priority": None, "due_at": None, "related_records": [],
    }])
    return body


def completion(answer="Zu deinen Aufträgen liegen mir keine Statusdaten vor. Welchen Auftrag meinst du?"):
    return {
        "status": "completed", "usage": {"input_tokens": 1000, "output_tokens": 24},
        "output": [{"type": "message", "role": "assistant", "status": "completed",
                    "content": [{"type": "output_text", "annotations": [],
                                 "text": json.dumps({"answer": answer, "prepared_actions": []})}]}],
    }


@pytest.fixture
def regular(setup, tmp_path, monkeypatch):
    key = tmp_path / "olivia-openai.env"
    key.write_text("OLIVIA_OPENAI_API_KEY=fixture-only-never-live\n")
    key.chmod(0o600)
    setup[1].provider = "openai"
    setup[1].openai_key_file = str(key)
    requests, outcomes = [], [(200, completion())]
    original = httpx.AsyncClient

    def handle(request):
        requests.append(request)
        status, body = outcomes[-1]
        if status == "timeout":
            raise httpx.ReadTimeout("sensitive-provider-details")
        return httpx.Response(status, json=body)

    monkeypatch.setattr(provider.httpx, "AsyncClient",
                        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
    return setup, requests, outcomes


def rows(setup):
    with sqlite3.connect(setup[1].replay_path) as db:
        return db.execute("SELECT month,reserved,blocked FROM mail_openai_months").fetchall()


@pytest.mark.asyncio
@pytest.mark.parametrize("recipient", [
    "konstantin@liquisto.com", "konstantin.milonas@condata.io", "aernout@liquisto.com",
])
async def test_existing_authenticated_reply_one_openai_call_regular_contract(regular, recipient):
    setup, requests, _ = regular
    body = payload()
    body["recipient"] = recipient
    result = await post(setup, body)
    assert result.status_code == 200
    assert result.json() == {"contract_version": "olivia-mail-answer-v1",
                             "answer": "Zu deinen Aufträgen liegen mir keine Statusdaten vor. Welchen Auftrag meinst du?"}
    assert setup[2] == []  # No local model fallback or parallel generation.
    assert len(requests) == 1
    assert str(requests[0].url) == provider.ENDPOINT
    outgoing = json.loads(requests[0].content)
    assert outgoing["model"] == "gpt-6-luna" and outgoing["store"] is False
    assert outgoing["max_output_tokens"] == 512
    assert outgoing["service_tier"] == "default"
    assert "tools" not in outgoing and "previous_response_id" not in outgoing
    projected = json.loads(outgoing["input"][1]["content"])
    assert projected["prompt"] == body["prompt"]
    assert projected["context"][0]["content"] == json.loads(body["context"][0]["content"])
    assert projected["context"][0]["model_projection"] == {
        "provided_records": 1, "shown_records": 1, "truncated": False,
    }
    for secret in (recipient, "actual-principal", "reviewed-profile", "n" * 43):
        assert secret not in requests[0].content.decode()
    assert rows(setup)[0][1:] == (provider.RESERVATION_MICRO_USD, 0)
    assert (await post(setup, body)).status_code == 409
    assert len(requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("recipient", "someone@liquisto.com"), ("tenant_id", "foreign-tenant"),
    ("source_ids", ["ungranted-source"]), ("provider", "openai"),
])
async def test_unapproved_contract_before_key_or_http(regular, monkeypatch, field, value):
    setup, requests, _ = regular
    monkeypatch.setattr(provider, "protected_openai_key", lambda _: pytest.fail("Key read"))
    body = payload()
    body[field] = value
    assert (await post(setup, body)).status_code == 422
    assert requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["bearer", "receipt"])
async def test_bad_auth_before_key_or_http(regular, monkeypatch, failure):
    setup, requests, _ = regular
    monkeypatch.setattr(provider, "protected_openai_key", lambda _: pytest.fail("Key read"))
    args = {"bearer": "invalid"} if failure == "bearer" else {"receipt": "{}"}
    assert (await post(setup, **args)).status_code == (401 if failure == "bearer" else 422)
    assert requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status,body,expected", [
    (403, {"secret": "sensitive-provider-details"}, 502),
    (429, {"error": {"code": "rate_limit_exceeded"}}, 429),
    ("timeout", {}, 502), (200, {}, 502),
    (200, completion(""), 502),
])
async def test_failures_consumed_without_retry_fallback_or_detail_leak(regular, status, body, expected):
    setup, requests, outcomes = regular
    outcomes[:] = [(status, body)]
    result = await post(setup, payload())
    assert result.status_code == expected
    assert "sensitive-provider-details" not in result.text
    assert setup[2] == [] and len(requests) == 1
    assert rows(setup)[0][1:] == (provider.RESERVATION_MICRO_USD, 0)
    assert (await post(setup, payload())).status_code == 409
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_spend_limit_429_stops_new_messages_before_key_http(regular, monkeypatch):
    setup, requests, outcomes = regular
    outcomes[:] = [(429, {"error": {"code": "project_spend_limit_exceeded"}})]
    assert (await post(setup, payload())).status_code == 429
    assert rows(setup)[0][1:] == (provider.RESERVATION_MICRO_USD, 1)
    monkeypatch.setattr(provider, "protected_openai_key", lambda _: pytest.fail("Stopped key read"))
    body = payload()
    body["message_key"] = "new-message"
    raw = json.dumps(body).encode()
    receipt = signed(raw, body, nonce="m" * 43)
    assert (await post(setup, body, raw=raw, receipt=receipt)).status_code == 429
    assert len(requests) == 1 and setup[2] == []


def budget_file(tmp_path):
    tmp_path.chmod(0o700)
    path = tmp_path / "existing-receipts.sqlite"
    path.touch(mode=0o600)
    return path


def test_atomic_monthly_cap_across_concurrent_workers_and_restart(tmp_path, monkeypatch):
    path = budget_file(tmp_path)
    monkeypatch.setattr(provider, "month", lambda: "2026-10")
    provider.mail_budget(path)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE mail_openai_months SET reserved=?", (24_960_000,))

    def attempt(_):
        try:
            provider.mail_budget(path)
            return True
        except provider.RegularMailBudgetStop:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))
    assert sum(results) == 2
    with pytest.raises(provider.RegularMailBudgetStop):
        provider.mail_budget(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT reserved FROM mail_openai_months").fetchone()[0] == 25_000_000
    monkeypatch.setattr(provider, "month", lambda: "2026-11")
    assert provider.mail_budget(path) == "2026-11"
    monkeypatch.setattr(provider, "month", lambda: "2026-10")
    with pytest.raises(provider.RegularMailBudgetStop):
        provider.mail_budget(path)


@pytest.mark.parametrize("content", ["OPENAI_API_KEY=fixture-only", "", "OLIVIA_OPENAI_API_KEY=x\nOLIVIA_OPENAI_API_KEY=y", "OLIVIA_OPENAI_API_KEY=bad key"])
def test_only_single_dedicated_protected_key_fixture(tmp_path, content):
    key = tmp_path / "fixture.env"
    key.write_text(content)
    key.chmod(0o600)
    with pytest.raises(ValueError):
        provider.protected_openai_key(key)


def test_missing_receipt_store_never_creates_budget(tmp_path):
    path = tmp_path / "missing.sqlite"
    with pytest.raises(provider.RegularMailProviderError):
        provider.mail_budget(path)
    assert not path.exists()


@pytest.mark.asyncio
async def test_sensitive_projection_never_reads_key_or_calls_provider(regular, monkeypatch):
    setup, requests, _ = regular
    monkeypatch.setattr(provider, "protected_openai_key", lambda _: pytest.fail("Key read"))
    body = payload()
    body["prompt"] = "password=do-not-export"
    result = await post(setup, body)
    assert result.status_code == 502
    assert "do-not-export" not in result.text and requests == []
    with sqlite3.connect(setup[1].replay_path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name='mail_openai_months'").fetchone() is None
