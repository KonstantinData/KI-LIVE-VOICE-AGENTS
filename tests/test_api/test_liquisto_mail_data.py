"""External data preflight uses concrete CRM projection, not sample size alone."""
import json

import pytest

from src.api.services.liquisto_mail_data import check_external_projection
from tests.test_api.test_liquisto_regular_mail_openai import payload
from src.api.routes.liquisto_mail import build_mail_messages


def messages(body=None):
    body = payload() if body is None else body
    return build_mail_messages(prompt=body["prompt"], context=body["context"])


def test_concrete_current_task_projection_is_allowed():
    check_external_projection(messages())


@pytest.mark.parametrize("secret", [
    "sk-proj-" + "x" * 30, "password=private-value", "IBAN DE12345678901234567890",
    "Patientin: Diagnose HIV", "SSN: 123-45-6789", "Bearer " + "x" * 40,
    "-----BEGIN PRIVATE KEY-----", "politische Meinung: private details",
    "AKIAABCDEFGHIJKLMNOP", "ghp_" + "x" * 40, "biometric private fingerprint",
])
@pytest.mark.parametrize("location", ["prompt", "context"])
def test_sensitive_markers_block_before_external_transfer(secret, location):
    body = payload()
    if location == "prompt":
        body["prompt"] = secret
    else:
        record = json.loads(body["context"][0]["content"])[0]
        record["summary"] = secret
        body["context"][0]["content"] = json.dumps([record])
    with pytest.raises(ValueError):
        check_external_projection(messages(body))


@pytest.mark.parametrize("field", ["email", "notes", "password", "health", "private_metadata"])
def test_no_extra_sensitive_context_fields_are_exportable(field):
    body = payload()
    record = json.loads(body["context"][0]["content"])[0]
    record[field] = "unapproved-data"
    body["context"][0]["content"] = json.dumps([record])
    with pytest.raises(ValueError):
        check_external_projection(messages(body))


def test_plain_unstructured_context_is_not_an_external_projection():
    body = payload()
    body["context"][0]["content"] = "Unknown free-form source"
    with pytest.raises(ValueError):
        check_external_projection(messages(body))


def test_current_text_is_not_claimed_to_be_anonymized():
    body = payload()
    body["prompt"] = "Please respond to Alex at alex@example.invalid about inventory."
    checked = messages(body)
    check_external_projection(checked)
    assert "alex@example.invalid" in checked[1]["content"]


@pytest.mark.parametrize("source,record", [
    ("liquisto-business-purpose", {"company": "Liquisto", "purpose": "Transform excess inventory",
                                  "website": "https://liquisto.com",
                                  "source_policy": "registry/tenants/liquisto/assistant-sources.json"}),
    ("crm-companies", {"record_id": "company-test", "version": 1, "updated_at": None,
                       "name": "Synthetic manufacturer", "industry": "Machinery", "lifecycle_stage": None}),
    ("crm-deals", {"record_id": "deal-test", "version": 1, "updated_at": None,
                   "name": "Synthetic inventory", "pipeline_id": "pipeline-test", "stage_id": "stage-test",
                   "amount": {"amount_minor": 125000, "currency": "EUR"},
                   "expected_close_date": None, "probability_percent": 25.0}),
])
def test_other_actual_projected_source_shapes_are_allowed(source, record):
    body = payload()
    body["context"][0].update(source_id=source, content=json.dumps([record]))
    check_external_projection(messages(body))
