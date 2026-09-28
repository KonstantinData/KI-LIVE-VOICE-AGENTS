"""Anna telephone contact handoff tests without network or credentials."""

import pytest

from src.telephony.contact_handoff import (
    PhoneContactHandoffError,
    submit_phone_contact_handoff,
)
from src.tenants.registry import get_tenant_profile


def arguments(**changes):
    result = {
        "first_name": "Erika",
        "last_name": "Musterfrau",
        "email": "erika@example.test",
        "phone": "+49 30 123456",
        "conversation_summary": "Interesse an einer Küchenplanung.",
        "best_reachability": "werktags vormittags",
        "preferred_channel": "email",
        "contact_consent_confirmed": True,
        "transcript_consent_confirmed": True,
    }
    result.update(changes)
    return result


@pytest.mark.asyncio
async def test_phone_handoff_forwards_tenant_contact_summary_and_transcript(monkeypatch):
    captured = {}

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"success": True, "capture_id": "capture-1"}

    class Client:
        def __init__(self, **kwargs):
            captured["client"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            captured.update(url=url, **kwargs)
            return Response()

    monkeypatch.setattr("src.telephony.contact_handoff.httpx.AsyncClient", Client)
    agent = get_tenant_profile("mein-kuechenexperte").phone_agent("anna-phone-assistant")
    result = await submit_phone_contact_handoff(
        tenant_id="mein-kuechenexperte",
        agent=agent,
        arguments=arguments(),
        transcript="Anrufer: Guten Tag.\nAnna: Guten Tag.",
        contact_secret="test-secret",
        session_id="session-1",
    )
    assert result == {
        "success": True,
        "crm_captured": True,
        "customer_summary_requested": True,
    }
    assert captured["url"].endswith("/anna-voice-handoff")
    assert captured["headers"]["X-Anna-Webhook-Secret"] == "test-secret"
    payload = captured["json"]
    assert payload["tenant_id"] == "mein-kuechenexperte"
    assert payload["agent_id"] == "anna-phone-assistant"
    assert payload["session_id"] == payload["conversation_id"] == "session-1"
    assert payload["contact"]["email"] == "erika@example.test"
    assert payload["contact"]["full_name"] == "Erika Musterfrau"
    assert payload["customer_summary"] == "Interesse an einer Küchenplanung."
    assert "Anrufer: Guten Tag." in payload["transcript"]
    assert payload["consent"]["transcript_processing_accepted"] is True
    assert payload["consent"]["contact_capture_accepted"] is True
    assert payload["consent"]["customer_summary_email_accepted"] is True
    assert payload["consent"]["version"] == "anna-phone-consent-v1"
    assert payload["transcript_confidence"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("changes,error", [
    ({"contact_consent_confirmed": False}, "contact_consent_required"),
    ({"transcript_consent_confirmed": False}, "transcript_consent_required"),
    ({"email": "invalid"}, "invalid_email"),
])
async def test_phone_handoff_fails_closed_before_network(changes, error):
    agent = get_tenant_profile("mein-kuechenexperte").phone_agent("anna-phone-assistant")
    with pytest.raises(PhoneContactHandoffError, match=error):
        await submit_phone_contact_handoff(
            tenant_id="mein-kuechenexperte",
            agent=agent,
            arguments=arguments(**changes),
            transcript="Anrufer: Test",
            contact_secret="test-secret",
            session_id="session-1",
        )
