"""Opaque technical references: synthetic data, no real keys or connections."""
import copy
import json
import re
import sqlite3

import pytest

from src.api.routes.liquisto_mail import build_mail_messages
from src.api.services import liquisto_mail_references as references
from src.api.services.liquisto_mail_data import SENSITIVE, check_external_projection
from src.api.services.liquisto_mail_openai import request_bytes
from tests.test_api import test_liquisto_regular_mail_openai as provider_fixtures
from tests.test_api.test_liquisto_mail_route import post, signed
from tests.test_api.test_liquisto_regular_mail_openai import payload

regular = provider_fixtures.regular
setup = provider_fixtures.setup


def messages(body=None):
    body = payload() if body is None else body
    return build_mail_messages(prompt=body["prompt"], context=body["context"])


def projected(result):
    return json.loads(result[1]["content"])


def with_id(value, *, nested=False):
    body = payload()
    record = json.loads(body["context"][0]["content"])[0]
    if nested:
        record["related_records"] = [{"record_type": "company", "record_id": value}]
    else:
        record["record_id"] = value
    body["context"][0]["content"] = json.dumps([record])
    return body


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("original", [
    "task-" + "a" * 20, "task-company-intelligence-" + "a" * 40,
    "sk-" + "a" * 20, "prefixsk-proj-" + "a" * 20,
    "password=synthetic-only", "IBAN synthetic-only", "a" * 80,
    "identifier-äöü", "ref-" + "0" * 24,
])
def test_only_designated_ids_become_independent_refs_without_secret_transfer(original, nested):
    source_messages = messages(with_id(original, nested=nested))
    before = copy.deepcopy(source_messages)
    result = references.prepare_external_reference_messages(source_messages)
    assert source_messages == before
    record = projected(result)["context"][0]["content"][0]
    token = record["related_records"][0]["record_id"] if nested else record["record_id"]
    assert re.fullmatch(r"ref-[0-9a-f]{24}", token)
    assert original not in request_bytes(result).decode()
    check_external_projection(result)


@pytest.mark.parametrize("location", ["prompt", "summary", "label", "priority"])
@pytest.mark.parametrize("secret", [
    "sk-" + "a" * 20, "prefixsk-" + "a" * 20, "_sk-" + "a" * 20,
    "äsk-" + "a" * 20, "password=synthetic-only", "Patientin Diagnose HIV", "a" * 48,
])
def test_retained_text_still_denies_standalone_and_embedded_secret_markers(location, secret):
    body = with_id("task-" + "a" * 20)
    if location == "prompt":
        body["prompt"] = secret
    elif location == "label":
        body["context"][0]["label"] = secret
    else:
        record = json.loads(body["context"][0]["content"])[0]
        record[location] = secret
        body["context"][0]["content"] = json.dumps([record])
    with pytest.raises(ValueError):
        references.prepare_external_reference_messages(messages(body))
    assert SENSITIVE.search(secret)


@pytest.mark.parametrize("location", ["prompt", "summary", "label"])
def test_original_id_repeated_in_retained_text_denies_without_text_rewriting(location):
    original = "company-synthetic-identity"
    body = with_id(original)
    text = "Discuss " + original
    if location == "prompt":
        body["prompt"] = text
    elif location == "label":
        body["context"][0]["label"] = text
    else:
        record = json.loads(body["context"][0]["content"])[0]
        record[location] = text
        body["context"][0]["content"] = json.dumps([record])
    with pytest.raises(ValueError):
        references.prepare_external_reference_messages(messages(body))


def graph():
    company = {"record_id": "shared-synthetic-id", "version": 1, "updated_at": None,
               "name": "Manufacturer", "industry": "Machinery", "lifecycle_stage": None}
    deal = {"record_id": "shared-synthetic-id", "version": 2, "updated_at": None,
            "name": "Inventory", "pipeline_id": "pipeline-synthetic", "stage_id": "stage-synthetic",
            "amount": None, "expected_close_date": None, "probability_percent": None}
    body = payload()
    task = json.loads(body["context"][0]["content"])[0]
    task.update(record_id="task-synthetic-graph", related_records=[
        {"record_type": "company", "record_id": company["record_id"]},
        {"record_type": "deal", "record_id": deal["record_id"]},
        {"record_type": "company", "record_id": company["record_id"]},
        {"record_type": "activity", "record_id": "task-synthetic-graph"},
        {"record_type": "contact", "record_id": "unseen-contact-synthetic"},
    ])
    body["context"] = [{"source_id": sid, "label": label, "observed_at": "2026-10-11T11:00:00Z",
                        "content": json.dumps([record])}
                       for sid, label, record in [("crm-open-tasks", "Tasks", task),
                                                  ("crm-companies", "Companies", company),
                                                  ("crm-deals", "Deals", deal)]]
    return body


def test_graph_binding_is_type_specific_and_preserves_all_content_and_order():
    body = graph()
    result = references.prepare_external_reference_messages(messages(body))
    data = projected(result)
    by_source = {source["source_id"]: source["content"][0] for source in data["context"]}
    task = by_source["crm-open-tasks"]
    links = task["related_records"]
    assert links[0]["record_id"] == links[2]["record_id"] == by_source["crm-companies"]["record_id"]
    assert links[1]["record_id"] == by_source["crm-deals"]["record_id"] != links[0]["record_id"]
    assert links[3]["record_id"] == task["record_id"]
    assert links[4]["record_id"] not in {task["record_id"], links[0]["record_id"], links[1]["record_id"]}
    assert [s["source_id"] for s in data["context"]] == [s["source_id"] for s in body["context"]]
    for before_source, after_source in zip(body["context"], data["context"], strict=True):
        before = json.loads(before_source["content"])[0]
        after = after_source["content"][0]
        for key in before.keys() - {"record_id", "related_records"}:
            assert after[key] == before[key]
    assert [r["record_type"] for r in links] == ["company", "deal", "company", "activity", "contact"]


def test_references_are_new_for_each_request_and_never_derived_from_original():
    body = graph()
    first = projected(references.prepare_external_reference_messages(messages(body)))
    second = projected(references.prepare_external_reference_messages(messages(body)))
    assert first["context"][0]["content"][0]["record_id"] != second["context"][0]["content"][0]["record_id"]


def test_concrete_false_positive_is_fixed_without_changing_the_marker_rule():
    original = "task-" + "a" * 20
    before = messages(with_id(original))
    assert SENSITIVE.search(original)
    with pytest.raises(ValueError):
        check_external_projection(before)
    after = references.prepare_external_reference_messages(before)
    check_external_projection(after)
    assert original not in request_bytes(after).decode()
    # The exact same marker remains denied in retained text.
    contaminated = with_id(original)
    contaminated["prompt"] = original
    with pytest.raises(ValueError):
        references.prepare_external_reference_messages(messages(contaminated))


@pytest.mark.parametrize("bad", [None, 7, True, [], {}, "", " ", "a" * 241, "id\n", "id\x00"])
@pytest.mark.parametrize("nested", [False, True])
def test_malformed_id_slots_deny_before_randomness(bad, nested, monkeypatch):
    monkeypatch.setattr(references.secrets, "token_hex", lambda _: pytest.fail("Alias minted"))
    with pytest.raises(ValueError):
        references.prepare_external_reference_messages(messages(with_id(bad, nested=nested)))


@pytest.mark.parametrize("change", ["extra_field", "unknown_source", "unknown_reference_type", "extra_reference_field"])
def test_no_free_text_or_unknown_field_can_claim_technical_id_exemption(change):
    body = with_id("task-synthetic-metadata", nested=True)
    record = json.loads(body["context"][0]["content"])[0]
    if change == "extra_field":
        record["private_metadata"] = {"record_id": "sk-" + "a" * 20}
    elif change == "unknown_source":
        body["context"][0]["source_id"] = "unapproved-source"
    elif change == "unknown_reference_type":
        record["related_records"][0]["record_type"] = "summary"
    else:
        record["related_records"][0]["secret"] = "sk-" + "a" * 20
    body["context"][0]["content"] = json.dumps([record])
    with pytest.raises(ValueError):
        references.prepare_external_reference_messages(messages(body))


def test_random_collision_is_retried_and_distinct_bindings_remain_distinct(monkeypatch):
    tokens = iter(["0" * 24, "0" * 24, "1" * 24, "2" * 24, "3" * 24])
    monkeypatch.setattr(references.secrets, "token_hex", lambda _: next(tokens))
    data = projected(references.prepare_external_reference_messages(messages(graph())))
    task = data["context"][0]["content"][0]
    assert task["record_id"] != task["related_records"][0]["record_id"]


def test_persistent_random_collision_denies_in_bounded_time(monkeypatch):
    monkeypatch.setattr(references.secrets, "token_hex", lambda _: "0" * 24)
    with pytest.raises(ValueError):
        references.prepare_external_reference_messages(messages(graph()))


def test_random_token_cannot_reuse_an_original_id(monkeypatch):
    original = "ref-" + "0" * 24
    tokens = iter(["0" * 24, "1" * 24])
    monkeypatch.setattr(references.secrets, "token_hex", lambda _: next(tokens))
    result = references.prepare_external_reference_messages(messages(with_id(original)))
    assert projected(result)["context"][0]["content"][0]["record_id"] == "ref-" + "1" * 24
    assert original not in request_bytes(result).decode()


def test_random_token_does_not_collide_with_legitimate_business_text(monkeypatch):
    body = payload()
    body["prompt"] = "Discuss SKU ref-" + "0" * 24
    tokens = iter(["0" * 24, "1" * 24])
    monkeypatch.setattr(references.secrets, "token_hex", lambda _: next(tokens))
    result = references.prepare_external_reference_messages(messages(body))
    assert projected(result)["prompt"] == body["prompt"]
    assert references.prepared_reference_tokens(result) == {"ref-" + "1" * 24}


def test_duplicate_json_properties_and_reapplying_preparation_deny():
    original = messages()
    original[1]["content"] = '{"prompt":"Synthetic","prompt":"Duplicate","context":[]}'
    with pytest.raises(ValueError):
        references.prepare_external_reference_messages(original)
    prepared = references.prepare_external_reference_messages(messages())
    with pytest.raises(ValueError):
        references.prepare_external_reference_messages(prepared)


@pytest.mark.asyncio
@pytest.mark.parametrize("original", [
    "task-" + "a" * 20, "task-company-intelligence-" + "a" * 40,
    "sk-" + "a" * 20, "prefixsk-proj-" + "a" * 20, "password=synthetic-only",
])
async def test_signed_regular_route_answers_without_exporting_original_id(regular, original):
    setup, requests, _ = regular
    body = with_id(original)
    record = json.loads(body["context"][0]["content"])[0]
    record["related_records"] = [
        {"record_type": "activity", "record_id": original},
        {"record_type": "company", "record_id": "sk-" + "b" * 20},
    ]
    body["context"][0]["content"] = json.dumps([record])
    result = await post(setup, body)
    assert result.status_code == 200
    assert len(requests) == 1
    outgoing = json.loads(requests[0].content)
    actual = projected(outgoing["input"])["context"][0]["content"][0]
    assert re.fullmatch(r"ref-[0-9a-f]{24}", actual["record_id"])
    assert actual["record_id"] == actual["related_records"][0]["record_id"]
    assert actual["related_records"][1]["record_id"] != actual["record_id"]
    assert actual["summary"] == record["summary"]
    for raw_id in (original, "sk-" + "b" * 20):
        assert raw_id not in requests[0].content.decode()
        assert raw_id not in result.text
    assert outgoing["model"] == "gpt-6-luna" and outgoing["store"] is False
    assert "tools" not in outgoing and "previous_response_id" not in outgoing
    assert provider_fixtures.rows(setup)[0][1:] == (20_000, 0)
    assert (await post(setup, body)).status_code == 409
    assert len(requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("location", ["prompt", "summary"])
@pytest.mark.parametrize("secret", ["sk-" + "a" * 20, "prefixsk-" + "a" * 20, "password=synthetic-only"])
async def test_signed_free_text_still_denies_before_budget_key_and_mock_http(regular, monkeypatch,
                                                                          location, secret):
    setup, requests, _ = regular
    body = with_id("task-" + "b" * 20)
    if location == "prompt":
        body["prompt"] = secret
    else:
        record = json.loads(body["context"][0]["content"])[0]
        record["summary"] = secret
        body["context"][0]["content"] = json.dumps([record])
    provider = provider_fixtures.provider
    monkeypatch.setattr(provider, "protected_openai_key", lambda _: pytest.fail("Key read"))
    monkeypatch.setattr(provider, "mail_budget", lambda _: pytest.fail("Budget reservation"))
    result = await post(setup, body)
    assert result.status_code == 502
    assert secret not in result.text and requests == []
    with sqlite3.connect(setup[1].replay_path) as db:
        assert db.execute("SELECT COUNT(*) FROM mail_receipts").fetchone()[0] == 1
        assert db.execute("SELECT name FROM sqlite_master WHERE name='mail_openai_months'").fetchone() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["bearer", "signature", "payload_binding", "source_metadata"])
async def test_reference_preparation_is_after_authentication_and_provenance_checks(regular,
                                                                                monkeypatch, failure):
    setup, requests, _ = regular
    monkeypatch.setattr(references, "prepare_external_reference_messages",
                        lambda _: pytest.fail("Unauthenticated reference preparation"))
    body = with_id("task-" + "a" * 20)
    raw = json.dumps(body).encode()
    header = signed(raw, body)
    args = {}
    if failure == "bearer":
        args["bearer"] = "invalid"
        expected = 401
    elif failure == "signature":
        receipt = json.loads(header)
        receipt["signature"] = "0" * 64
        args["receipt"] = json.dumps(receipt)
        expected = 403
    elif failure == "payload_binding":
        body["prompt"] = "Another synthetic question."
        args["receipt"] = header
        expected = 403
    else:
        body["context"][0]["system"] = "liquisto-unapproved"
        expected = 422
    assert (await post(setup, body, **args)).status_code == expected
    assert requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["Aufgabe ref-" + "0" * 24, "Quelle: ref-" + "0" * 24])
async def test_minted_reference_echo_denies_before_any_mail_answer_is_accepted(regular, monkeypatch, answer):
    setup, requests, outcomes = regular
    monkeypatch.setattr(references.secrets, "token_hex", lambda _: "0" * 24)
    outcomes[:] = [(200, provider_fixtures.completion(answer))]
    result = await post(setup, payload())
    assert result.status_code == 502
    assert "ref-" + "0" * 24 not in result.text
    assert len(requests) == 1
    assert (await post(setup, payload())).status_code == 409
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_legitimate_ref_shaped_business_text_and_source_citation_are_not_amputated(regular,
                                                                                     monkeypatch):
    setup, requests, outcomes = regular
    sku = "ref-" + "0" * 24
    body = payload()
    body["prompt"] = "Prüfe Artikel " + sku
    monkeypatch.setattr(references.secrets, "token_hex", lambda _: "1" * 24)
    answer = "Laut Open tasks: Review inventory. Artikel " + sku + " ist in der Frage genannt."
    outcomes[:] = [(200, provider_fixtures.completion(answer))]
    result = await post(setup, body)
    assert result.status_code == 200
    assert result.json()["answer"] == answer
    actual = projected(json.loads(requests[0].content)["input"])
    assert actual["prompt"] == body["prompt"]
    assert actual["context"][0]["label"] == "Open tasks"
    assert actual["context"][0]["content"][0]["summary"] == "Review inventory"


@pytest.mark.asyncio
@pytest.mark.parametrize("fail", [False, True])
async def test_original_ids_and_marked_secrets_do_not_appear_in_logs_or_errors(regular, caplog,
                                                                          capsys, fail):
    caplog.set_level("DEBUG")
    setup, requests, _ = regular
    original = "prefixsk-" + "a" * 20
    body = with_id(original)
    if fail:
        body["prompt"] = "password=synthetic-prohibited"
    result = await post(setup, body)
    assert result.status_code == (502 if fail else 200)
    captured = capsys.readouterr()
    surfaces = result.text + caplog.text + captured.out + captured.err
    for secret in [original, "password=synthetic-prohibited"]:
        assert secret not in surfaces
    if requests:
        assert original not in requests[0].content.decode()
