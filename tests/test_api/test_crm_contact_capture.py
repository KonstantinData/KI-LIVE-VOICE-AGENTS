"""Tests for the secure CRM contact-capture intake API."""

import pytest

from src.api.config import get_settings
from src.api.routes import crm_contact_capture


def _accepted_payload() -> dict:
    return {
        "tenant_id": "mein-kuechenexperte",
        "channel_type": "contact_form",
        "purpose": "contact_request",
        "case_id": "MKX-TEST",
        "decision": "accepted",
        "validation_errors": [],
        "contact_handoff": {
            "first_name": "Max",
            "last_name": "Mustermann",
            "full_name": "Max Mustermann",
            "email": "max@example.com",
            "phone": "+49 123",
            "preferred_channel": "email",
        },
        "consent": {"state": "allowed", "source": "contact_form_privacy_checkbox"},
        "linked_context": {},
        "source": {"source_page": "/kontakt"},
        "audit_context": {"decision": "accepted"},
        "retention": {"contains_pii": True, "policy_request": "crm_contact_capture_pii"},
    }


@pytest.fixture(autouse=True)
def _crm_intake_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "crm_contact_capture_intake_secret", "test-secret")
    monkeypatch.setattr(
        settings,
        "crm_contact_capture_database_url",
        "postgresql://mkx_crm_writer:secret@127.0.0.1:5432/mkx_crm",
    )


@pytest.mark.asyncio
async def test_crm_contact_capture_accepts_sanitized_handoff(db_client, monkeypatch):
    """Accepted sanitized handoffs are persisted through the intake route."""
    captured = {}

    async def fake_persist(payload):
        captured["payload"] = payload
        return "ledger-1"

    monkeypatch.setattr(crm_contact_capture, "persist_crm_contact_capture", fake_persist)

    response = await db_client.post(
        "/crm/contact-captures",
        headers={"X-CRM-INTAKE-SECRET": "test-secret"},
        json=_accepted_payload(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "ledger_id": "ledger-1",
        "decision": "accepted",
    }
    assert captured["payload"].tenant_id == "mein-kuechenexperte"
    assert captured["payload"].contact_handoff.email == "max@example.com"


@pytest.mark.asyncio
async def test_crm_contact_capture_rejects_missing_secret(db_client, monkeypatch):
    """The endpoint requires the server-to-server intake secret."""

    async def fake_persist(payload):
        return "ledger-1"

    monkeypatch.setattr(crm_contact_capture, "persist_crm_contact_capture", fake_persist)

    response = await db_client.post("/crm/contact-captures", json=_accepted_payload())

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_crm_contact_capture_rejects_cross_tenant_payload(db_client):
    """Cross-tenant payloads are rejected before persistence."""
    payload = _accepted_payload()
    payload["tenant_id"] = "other-tenant"

    response = await db_client.post(
        "/crm/contact-captures",
        headers={"X-CRM-INTAKE-SECRET": "test-secret"},
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_crm_contact_capture_rejects_raw_payload_fields(db_client):
    """Raw channel payloads and transcripts must not enter the intake API."""
    payload = _accepted_payload()
    payload["raw_payload"] = {"message": "must not be accepted"}

    response = await db_client.post(
        "/crm/contact-captures",
        headers={"X-CRM-INTAKE-SECRET": "test-secret"},
        json=payload,
    )

    assert response.status_code == 422

    payload = _accepted_payload()
    payload["source"]["transcript"] = "raw transcript text"

    response = await db_client.post(
        "/crm/contact-captures",
        headers={"X-CRM-INTAKE-SECRET": "test-secret"},
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_crm_contact_capture_allows_rejected_without_contact_handoff(
    db_client,
    monkeypatch,
):
    """Rejected captures may be ledged without accepted contact handoff JSON."""
    captured = {}

    async def fake_persist(payload):
        captured["payload"] = payload
        return "ledger-rejected"

    monkeypatch.setattr(crm_contact_capture, "persist_crm_contact_capture", fake_persist)
    payload = _accepted_payload()
    payload["decision"] = "rejected"
    payload["validation_errors"] = ["missing_consent"]
    payload["contact_handoff"] = None
    payload["consent"] = {"state": "missing"}

    response = await db_client.post(
        "/crm/contact-captures",
        headers={"X-CRM-INTAKE-SECRET": "test-secret"},
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "rejected"
    assert captured["payload"].contact_handoff is None


@pytest.mark.asyncio
async def test_crm_contact_capture_returns_503_when_database_is_unavailable(
    db_client,
    monkeypatch,
):
    """Database failures fail closed with a controlled 503 response."""

    async def fake_connect(url):
        raise ValueError("invalid database URL")

    monkeypatch.setattr(crm_contact_capture.asyncpg, "connect", fake_connect)

    response = await db_client.post(
        "/crm/contact-captures",
        headers={"X-CRM-INTAKE-SECRET": "test-secret"},
        json=_accepted_payload(),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "crm_contact_capture_database_unavailable"
