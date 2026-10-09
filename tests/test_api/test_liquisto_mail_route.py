"""Mail generation authentication, receipt integrity and durable no-retry proofs."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routes import liquisto_mail as route

TOKEN = "dedicated-runtime-test-token-0123456789"
KEY = bytes.fromhex("f1" * 32)


def test_control_crm_python_known_raw_key_signature_vector():
    receipt = {
        "contract_version": "0.1.0", "operation": "respond", "tenant_id": "liquisto",
        "agent_id": "liquisto-assistant", "principal_id": "fixture-principal",
        "recipient": "konstantin@liquisto.com", "profile_id": "fixture-reviewed-profile",
        "profile_sha256": "22" * 32, "message_key": "fixture-message",
        "source_ids": ["crm-open-tasks"], "payload_sha256": "33" * 32,
        "nonce": "00000000-0000-4000-8000-000000000001", "expires_at": 1900000000,
    }
    expected = "adf4689b45a92f60700a992aba544d22b9a77cabd0d019d73de3ed5894a1964f"
    canonical = route.canonical_receipt(receipt)
    assert hmac.new(bytes.fromhex("11" * 32), canonical, hashlib.sha256).hexdigest() == expected
    assert hmac.new(("11" * 32).encode(), canonical, hashlib.sha256).hexdigest() != expected


@pytest.fixture
def setup(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    key = tmp_path / "key"
    key.write_text(KEY.hex())
    key.chmod(0o600)
    settings = route.MailSettings(
        enabled=True, runtime_token=TOKEN, receipt_key_path=str(key),
        replay_path=str(tmp_path / "replay.sqlite"),
    )
    monkeypatch.setattr(route, "get_mail_settings", lambda: settings)
    monkeypatch.setattr(route, "build_liquisto_assistant_messages", lambda **args: [
        {"role": "system", "content": "Shared persona"},
        {"role": "user", "content": args["prompt"]},
    ])
    monkeypatch.setattr(route.LiquistoAssistantRuntimeConfig, "from_settings", lambda _: object())
    calls = []

    class Client:
        def __init__(self, _):
            pass

        async def respond(self, messages):
            calls.append(messages)
            return response.answer

    response = SimpleNamespace(answer='{"answer":"Die offenen Aufgaben sind zusammengefasst.",'
                                     '"prepared_actions":[]}')
    monkeypatch.setattr(route, "LocalOpenAICompatibleClient", Client)
    app = FastAPI()
    app.include_router(route.router)
    return app, settings, calls, response


def payload():
    return {
        "contract_version": "olivia-mail-respond-v1", "tenant_id": "liquisto",
        "agent_id": "liquisto-assistant", "principal_id": "actual-principal",
        "recipient": "konstantin@liquisto.com", "profile_id": "reviewed-profile",
        "profile_sha256": "a" * 64, "message_key": "message-123", "source_ids": ["crm-open-tasks"],
        "prompt": "Bitte fasse meine offenen Aufgaben zusammen.",
        "context": [{"source_id": "crm-open-tasks", "label": "Open tasks", "system": "liquisto-crm",
                     "permission": "crm:read", "observed_at": "2026-10-09T12:00:00Z",
                     "classification": "internal", "content": "Synthetic minimized projection."}],
    }


def signed(raw, body, **changes):
    receipt = {
        **{key: body[key] for key in ("tenant_id", "agent_id", "principal_id", "recipient",
                                      "profile_id", "profile_sha256", "message_key", "source_ids")},
        "contract_version": "0.1.0", "operation": "respond",
        "payload_sha256": hashlib.sha256(raw).hexdigest(), "nonce": "n" * 43,
        "expires_at": int(time.time()) + 60,
    }
    receipt.update(changes)
    signature = hmac.new(KEY, route.canonical_receipt(receipt), hashlib.sha256).hexdigest()
    return json.dumps({"receipt": receipt, "signature": signature})


async def post(setup, body=None, *, raw=None, receipt=None, bearer=TOKEN,
               content_type="application/json"):
    body = payload() if body is None else body
    raw = json.dumps(body).encode() if raw is None else raw
    header = signed(raw, body) if receipt is None else receipt
    async with AsyncClient(transport=ASGITransport(app=setup[0]), base_url="http://test") as client:
        headers = {
            "Authorization": "Bearer " + bearer, "X-Olivia-Mail-Receipt": header,
        }
        if content_type is not None:
            headers["Content-Type"] = content_type
        return await client.post("/assistant/mail/respond", content=raw, headers=headers)


@pytest.mark.asyncio
async def test_only_answer_no_tools_and_no_memory(setup):
    result = await post(setup)
    assert result.status_code == 200
    assert set(result.json()) == {"contract_version", "answer"}
    assert len(setup[2]) == 1
    assert "prepared_actions muss []" in setup[2][0][0]["content"]
    assert "tool" not in result.json()


@pytest.mark.asyncio
@pytest.mark.parametrize("bearer", ["", "ordinary-conversation-token", "memory-runtime-token"])
async def test_other_channels_never_authorize_mail(setup, bearer):
    assert (await post(setup, bearer=bearer)).status_code == 401
    assert not setup[2]


@pytest.mark.asyncio
async def test_default_disabled_and_incomplete_configuration(setup):
    assert route.MailSettings().enabled is False
    setup[1].enabled = False
    assert (await post(setup)).status_code == 503
    setup[1].enabled = True
    setup[1].runtime_token = ""
    assert (await post(setup)).status_code == 503
    assert not setup[2]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [
    {"principal_id": "other-principal"}, {"recipient": "aernout@liquisto.com"},
    {"profile_id": "other-profile"}, {"profile_sha256": "b" * 64},
    {"source_ids": ["crm-companies"]}, {"message_key": "different-message"},
    {"payload_sha256": "c" * 64},
    {"expires_at": 1}, {"expires_at": 32_000_000_000},
])
async def test_signed_receipt_does_not_allow_changed_binding_or_expiry(setup, change):
    body = payload()
    raw = json.dumps(body).encode()
    assert (await post(setup, body, raw=raw, receipt=signed(raw, body, **change))).status_code == 403
    assert not setup[2]


@pytest.mark.asyncio
async def test_exact_bytes_and_signature(setup):
    body = payload()
    raw = json.dumps(body).encode()
    receipt = signed(raw, body)
    assert (await post(setup, body, raw=raw + b" ", receipt=receipt)).status_code == 403
    envelope = json.loads(receipt)
    envelope["signature"] = "0" * 64
    assert (await post(setup, body, raw=raw, receipt=json.dumps(envelope))).status_code == 403
    assert not setup[2]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [
    {"tenant_id": "foreign"}, {"recipient": "outsider@example.com"}, {"tools": ["send"]},
    {"source_ids": ["tasks", "tasks"]}, {"source_ids": ["companies"]},
    {"context": []}, {"prepared_actions": []},
])
async def test_extra_foreign_or_unbound_contract_fields(setup, change):
    body = payload()
    body.update(change)
    assert (await post(setup, body)).status_code == 422
    assert not setup[2]


@pytest.mark.asyncio
async def test_wrong_receipt_operation_and_extra_fields(setup):
    body = payload()
    raw = json.dumps(body).encode()
    assert (await post(setup, body, receipt=signed(raw, body, operation="send"))).status_code == 422
    assert (await post(setup, body, receipt=signed(raw, body, role="owner"))).status_code == 422
    assert not setup[2]


@pytest.mark.asyncio
async def test_replay_durable_and_new_nonce_same_message_blocked(setup):
    body = payload()
    assert (await post(setup, body)).status_code == 200
    assert (await post(setup, body)).status_code == 409
    raw = json.dumps(body).encode()
    assert (await post(setup, body, receipt=signed(raw, body, nonce="x" * 43))).status_code == 409
    assert len(setup[2]) == 1
    with route.sqlite3.connect(setup[1].replay_path) as db:
        record = db.execute("SELECT * FROM mail_receipts").fetchone()
        assert all(len(value) == 64 for value in record)
        assert body["prompt"] not in str(record)


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", [
    '{"answer":"Ok","prepared_actions":[],"command":"mutate"}',
    'I have completed a mutation.',
    '{"answer":"Ok","answer":"duplicate","prepared_actions":[]}',
    '{"answer":"Ok","prepared_actions":[{"kind":"email"}]}',
])
async def test_provider_failure_consumes_receipt_no_regeneration(setup, answer):
    setup[3].answer = answer
    assert (await post(setup)).status_code == 502
    assert (await post(setup)).status_code == 409
    assert len(setup[2]) == 1


@pytest.mark.asyncio
async def test_even_schema_valid_prepared_action_cannot_escape_mail_route(setup):
    setup[3].answer = json.dumps({
        "answer": "Ein Entwurf.", "prepared_actions": [{
            "draft_id": "draft-one", "authority_mode": "draft-only", "kind": "email",
            "title": "Synthetic draft", "target_system": "email",
            "source_ids": ["crm-open-tasks"], "prepared_at": "2026-10-09T12:00:00Z",
            "preview": "Synthetic draft", "expected_effect": "Synthetic effect",
            "risks": [], "missing_information": [], "execution_status": "not-executable",
        }],
    })
    route.ProviderDraft.model_validate_json(setup[3].answer)
    assert (await post(setup)).status_code == 502
    assert len(setup[2]) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("expiry", [True, "2026-10-09T12:00:00Z", "1800000000"])
async def test_expiry_is_strict_integer(setup, expiry):
    body = payload()
    raw = json.dumps(body).encode()
    assert (await post(setup, body, receipt=signed(raw, body, expires_at=expiry))).status_code == 422
    assert not setup[2]


@pytest.mark.asyncio
async def test_reused_conversation_service_credential_fails_configuration(setup, monkeypatch):
    monkeypatch.setattr(route.get_settings(), "liquisto_assistant_service_token", TOKEN)
    assert (await post(setup)).status_code == 503
    assert not setup[2]


@pytest.mark.asyncio
async def test_duplicate_json_properties_and_body_limit(setup):
    body = payload()
    raw = json.dumps(body).encode()
    raw = raw[:-1] + b', "prompt":"changed"}'
    assert (await post(setup, body, raw=raw)).status_code == 422
    assert (await post(setup, body, raw=b" " * 48001)).status_code == 413
    assert not setup[2]


@pytest.mark.asyncio
async def test_secret_file_and_replay_path_fail_closed(setup):
    setup[1].receipt_key_path = "relative-file"
    assert (await post(setup)).status_code == 403
    assert not setup[2]


@pytest.mark.asyncio
@pytest.mark.parametrize("content_type", [None, "text/plain", "application/json; charset=utf-16"])
async def test_missing_or_non_utf8_json_content_type_denied(setup, content_type):
    assert (await post(setup, content_type=content_type)).status_code == 415
    assert not setup[2]


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [b"\xff", '{"x":1}'.encode("utf-16"), b'\xef\xbb\xbf{}'])
async def test_actual_payload_bytes_must_be_strict_utf8_without_bom(setup, raw):
    assert (await post(setup, raw=raw)).status_code == 422
    assert not setup[2]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [
    {"classification": "public"}, {"permission": "tenant:read"},
    {"permission": "admin:read"}, {"system": "liquisto-other"},
])
async def test_crm_sources_cannot_be_relabelled_to_broader_public_metadata(setup, change):
    body = payload()
    body["context"][0].update(change)
    assert (await post(setup, body)).status_code == 422
    assert not setup[2]


@pytest.mark.asyncio
async def test_business_purpose_exact_public_metadata_is_accepted(setup):
    body = payload()
    body["source_ids"] = ["liquisto-business-purpose"]
    body["context"][0].update({
        "source_id": "liquisto-business-purpose", "system": "liquisto-tenant-registry",
        "permission": "tenant:read", "classification": "public",
    })
    assert (await post(setup, body, content_type="application/json; charset=utf-8")).status_code == 200
