"""Direct delivery does not imply CRM capture or customer email delivery."""

import pytest

from src.telephony.contact_handoff import submit_phone_contact_handoff, PhoneContactHandoffError
from src.telephony.profiles import phone_session_config
from src.tenants.registry import get_tenant_profile


@pytest.mark.asyncio
async def test_phone_only_direct_delivery_bypasses_crm_and_transcript(monkeypatch):
    monkeypatch.setenv("ANNA_DIRECT_SMTP", "true")
    sent = []

    async def send(**kwargs):
        sent.append(kwargs)
        return True

    def forbidden(*args, **kwargs):
        pytest.fail("Direct SMTP must not call the legacy CRM mail endpoint")

    monkeypatch.setattr("src.telephony.mail.send_phone_notification", send)
    monkeypatch.setattr("src.telephony.contact_handoff.httpx.AsyncClient", forbidden)
    agent = get_tenant_profile("mein-kuechenexperte").phone_agent("anna-phone-assistant")
    args = dict(first_name="Erika", last_name="Muster", email="", phone="+4930123456",
                conversation_summary="Bitte zurückrufen", contact_consent_confirmed=True,
                transcript_consent_confirmed=False)
    result = await submit_phone_contact_handoff(tenant_id="mein-kuechenexperte", agent=agent,
        arguments=args, transcript="PRIVATE_TRANSCRIPT", contact_secret="", session_id="test")
    assert result == dict(success=True, internal_email_sent=True, customer_email_sent=False,
                         crm_captured=False, customer_summary_requested=False)
    assert "PRIVATE_TRANSCRIPT" not in str(sent)
    assert sent[0]["contact"]["phone"] == "+4930123456"
    args["contact_consent_confirmed"] = False
    with pytest.raises(PhoneContactHandoffError, match="contact_consent_required"):
        await submit_phone_contact_handoff(tenant_id="mein-kuechenexperte", agent=agent,
            arguments=args, transcript="", contact_secret="", session_id="test")
    assert len(sent) == 1


def test_direct_prompt_and_tool_describe_actual_delivery(monkeypatch):
    monkeypatch.setenv("ANNA_DIRECT_SMTP", "true")
    session, _, _ = phone_session_config("mein-kuechenexperte", "anna-phone-assistant")
    assert "customer_summary_consent_confirmed" in session["instructions"]
    assert "email_confirmed" in session["tools"][0]["parameters"]["required"]
    assert "KEIN CRM-Eintrag" in session["instructions"]
    assert "E-Mail-Adresse darf leer bleiben" in session["tools"][0]["description"]
    monkeypatch.delenv("ANNA_DIRECT_SMTP")
    legacy, _, _ = phone_session_config("mein-kuechenexperte", "anna-phone-assistant")
    assert "fordert die Zusammenfassung" in legacy["tools"][0]["description"]


@pytest.mark.asyncio
@pytest.mark.parametrize("internal_ok,customer_ok", [(True, True), (True, False),
                                                   (False, True), (False, False)])
async def test_independent_customer_and_owner_outcomes(monkeypatch, internal_ok, customer_ok):
    from src.telephony.mail import SMTPDeliveryError
    monkeypatch.setenv("ANNA_DIRECT_SMTP", "true")
    calls = []

    async def internal(**kwargs):
        calls.append("internal")
        if not internal_ok:
            raise SMTPDeliveryError("smtp_delivery_failed")
        return True

    async def customer(**kwargs):
        calls.append("customer")
        assert kwargs["consent_confirmed"] is True
        assert kwargs["email_confirmed"] is True
        assert "INTERNAL_ONLY" not in str(kwargs)
        if not customer_ok:
            raise SMTPDeliveryError("smtp_delivery_failed")
        return True

    monkeypatch.setattr("src.telephony.mail.send_phone_notification", internal)
    monkeypatch.setattr("src.telephony.mail.send_customer_summary", customer)
    agent = get_tenant_profile("mein-kuechenexperte").phone_agent("anna-phone-assistant")
    result = await submit_phone_contact_handoff(tenant_id="mein-kuechenexperte", agent=agent,
        arguments=dict(first_name="Erika", last_name="Muster", email="erika@example.test",
            conversation_summary="Bitte zurückrufen", contact_consent_confirmed=True,
            customer_summary_consent_confirmed=True, email_confirmed=True,
            additional_notes="INTERNAL_ONLY"), transcript="PRIVATE_TRANSCRIPT",
        contact_secret="", session_id="test")
    assert calls == ["internal", "customer"]
    assert result["success"] is (internal_ok and customer_ok)
    assert result["internal_email_sent"] is internal_ok
    assert result["customer_email_sent"] is customer_ok
    assert result["customer_summary_requested"] is True


@pytest.mark.asyncio
async def test_customer_confirmation_required_before_either_send(monkeypatch):
    monkeypatch.setenv("ANNA_DIRECT_SMTP", "true")

    async def forbidden(**kwargs):
        pytest.fail("No email may be sent before recipient validation")

    monkeypatch.setattr("src.telephony.mail.send_phone_notification", forbidden)
    monkeypatch.setattr("src.telephony.mail.send_customer_summary", forbidden)
    agent = get_tenant_profile("mein-kuechenexperte").phone_agent("anna-phone-assistant")
    with pytest.raises(PhoneContactHandoffError, match="confirmed_customer_email_required"):
        await submit_phone_contact_handoff(tenant_id="mein-kuechenexperte", agent=agent,
            arguments=dict(first_name="Erika", last_name="Muster", email="erika@example.test",
                conversation_summary="Rückruf", contact_consent_confirmed=True,
                customer_summary_consent_confirmed=True, email_confirmed=False),
            transcript="", contact_secret="", session_id="test")
