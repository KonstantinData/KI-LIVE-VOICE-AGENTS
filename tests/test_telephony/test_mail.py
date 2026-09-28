"""SMTP notifications without external network or real secrets."""

import smtplib
import ssl
from unittest.mock import MagicMock

import pytest

from src.telephony import mail


@pytest.fixture
def smtp(monkeypatch):
    monkeypatch.setenv("ANNA_DIRECT_SMTP", "true")
    values = {
        "SMTP_HOST": "ssl0.ovh.net", "SMTP_PORT": "587",
        "SMTP_SECURITY": "starttls", "SMTP_USER": mail.OWNER_MAILBOX,
        "SMTP_FROM_EMAIL": mail.OWNER_MAILBOX, "CONTACT_EMAIL": mail.OWNER_MAILBOX,
        "SMTP_PASS": "test-$PASSWORD-secret",
    }
    config = MagicMock(return_value=values)
    monkeypatch.setattr(mail, "dotenv_values", config)
    factory = MagicMock()
    client = factory.return_value.__enter__.return_value
    client.send_message.return_value = {}
    monkeypatch.setattr(mail.smtplib, "SMTP", factory)
    return factory, client, values, config


@pytest.mark.asyncio
async def test_notification_uses_verified_tls_and_fixed_recipient(smtp):
    factory, client, _, config = smtp
    assert await mail.send_phone_notification(
        summary="Bitte um Rückruf.", session_id="call-1",
        contact={"full_name": "Erika Beispiel", "email": "customer@example.test",
                 "phone": "+49 12345678", "transcript": "PRIVATE TRANSCRIPT",
                 "to": "attacker@example.test"},
    )
    config.assert_called_once_with(mail.SMTP_SECRET_PATH, interpolate=False)
    factory.assert_called_once_with("ssl0.ovh.net", 587, timeout=20)
    assert [call[0] for call in client.method_calls] == [
        "ehlo", "starttls", "ehlo", "login", "send_message"
    ]
    context = client.starttls.call_args.kwargs["context"]
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    client.login.assert_called_once_with(mail.OWNER_MAILBOX, "test-$PASSWORD-secret")
    message = client.send_message.call_args.args[0]
    assert client.send_message.call_args.kwargs["to_addrs"] == [mail.OWNER_MAILBOX]
    assert message["To"] == mail.OWNER_MAILBOX
    assert "customer@example.test" in message.get_content()
    assert "PRIVATE TRANSCRIPT" not in message.get_content()
    assert "attacker@example.test" not in str(message)


def test_connection_check_does_not_send(smtp):
    _, client, _, _ = smtp
    assert mail.check_smtp_connection()
    client.login.assert_called_once()
    client.send_message.assert_not_called()


@pytest.mark.parametrize("key,value", [
    ("SMTP_HOST", "attacker.example"), ("SMTP_PORT", "25"),
    ("SMTP_SECURITY", "none"), ("SMTP_USER", "other@example.test"),
    ("SMTP_FROM_EMAIL", "other@example.test"),
    ("CONTACT_EMAIL", "other@example.test"), ("SMTP_PASS", ""),
])
def test_invalid_config_fails_before_network(smtp, key, value):
    factory, _, values, _ = smtp
    values[key] = value
    with pytest.raises(mail.SMTPDeliveryError):
        mail.check_smtp_connection()
    factory.assert_not_called()


def test_disabled_fails_before_secret_read(smtp, monkeypatch):
    factory, _, _, config = smtp
    monkeypatch.delenv("ANNA_DIRECT_SMTP")
    with pytest.raises(mail.SMTPDeliveryError, match="smtp_not_enabled"):
        mail.check_smtp_connection()
    config.assert_not_called()
    factory.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["starttls", "login", "send_message"])
async def test_server_errors_do_not_leak_details(smtp, stage):
    _, client, _, _ = smtp
    getattr(client, stage).side_effect = smtplib.SMTPException("secret server details")
    with pytest.raises(mail.SMTPDeliveryError) as caught:
        await mail.send_phone_notification(summary="Rückruf", contact={}, session_id="1")
    assert str(caught.value) == "smtp_delivery_failed"
    assert caught.value.__suppress_context__
    if stage != "send_message":
        client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_recipient_refusal_is_not_success(smtp):
    smtp[1].send_message.return_value = {mail.OWNER_MAILBOX: (550, b"rejected")}
    with pytest.raises(mail.SMTPDeliveryError, match="smtp_delivery_failed"):
        await mail.send_phone_notification(summary="Rückruf", contact={}, session_id="1")


@pytest.mark.asyncio
async def test_empty_summary_does_not_connect(smtp):
    with pytest.raises(mail.SMTPDeliveryError, match="smtp_summary_required"):
        await mail.send_phone_notification(summary="  ", contact={}, session_id="1")
    smtp[0].assert_not_called()


@pytest.mark.asyncio
async def test_customer_summary_uses_single_confirmed_recipient_and_public_copy(smtp):
    assert await mail.send_customer_summary(
        summary="Sie wünschen einen Rückruf am Mittwoch.",
        full_name="Erika Beispiel", email="erika+call@example.test",
        consent_confirmed=True, email_confirmed=True, session_id="PRIVATE-CALL-ID",
    )
    client = smtp[1]
    message = client.send_message.call_args.args[0]
    assert client.send_message.call_args.kwargs == {
        "from_addr": mail.OWNER_MAILBOX, "to_addrs": ["erika+call@example.test"],
    }
    assert message["To"] == "erika+call@example.test"
    assert message["Reply-To"] == mail.OWNER_MAILBOX
    assert message["Cc"] is None and message["Bcc"] is None
    content = message.get_content()
    assert "Guten Tag Erika Beispiel," in content
    assert "Sie wünschen einen Rückruf am Mittwoch." in content
    for internal in ("PRIVATE-CALL-ID", "Weitere Hinweise", "Kontaktweg", "Transkript"):
        assert internal not in content
    assert "weitergeleitet" not in content
    assert "zugestellt" not in content


@pytest.mark.asyncio
@pytest.mark.parametrize("consent,confirmed", [
    (False, True), (True, False), (False, False), ("true", True), (True, 1),
])
async def test_customer_requires_explicit_confirmations(smtp, consent, confirmed):
    with pytest.raises(mail.SMTPDeliveryError, match="smtp_customer_confirmation_required"):
        await mail.send_customer_summary(
            summary="Rückruf", full_name="Erika Beispiel", email="erika@example.test",
            consent_confirmed=consent, email_confirmed=confirmed, session_id="1",
        )
    smtp[0].assert_not_called()


@pytest.mark.parametrize("address", [
    "a@example.test\r\nBcc: attacker@example.test", "a@example.test\n",
    "a@example.test,b@example.test", "a@example.test;b@example.test",
    "Erika <a@example.test>", "a@example.test (Erika)", " a@example.test",
    "a@example.test ", "ü@example.test", "a@exämple.test", "a@example",
    "a..b@example.test", ".a@example.test", "a.@example.test", "a@-example.test",
    "a@example-.test", "a@example..test", "a@@example.test", "", None,
    f"{'a' * 65}@example.test", f"a@{'b' * 64}.test",
])
def test_recipient_validation_rejects_malicious_or_invalid_addresses(smtp, address):
    with pytest.raises(mail.SMTPDeliveryError, match="smtp_invalid_recipient"):
        mail._deliver(None, address)
    smtp[0].assert_not_called()
    smtp[3].assert_not_called()


@pytest.mark.asyncio
async def test_customer_address_is_validated_before_message_construction(smtp):
    with pytest.raises(mail.SMTPDeliveryError, match="smtp_invalid_recipient"):
        await mail.send_customer_summary(
            summary="Rückruf", full_name="Erika", email="a@example.test\r\nBcc: bad@a.test",
            consent_confirmed=True, email_confirmed=True, session_id="1",
        )
    smtp[0].assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("summary,name,error", [
    (" ", "Erika", "smtp_summary_required"),
    ("Rückruf", " ", "smtp_customer_name_required"),
])
async def test_customer_requires_content_and_name(smtp, summary, name, error):
    with pytest.raises(mail.SMTPDeliveryError, match=error):
        await mail.send_customer_summary(
            summary=summary, full_name=name, email="erika@example.test",
            consent_confirmed=True, email_confirmed=True, session_id="1",
        )
    smtp[0].assert_not_called()


@pytest.mark.asyncio
async def test_customer_refusal_is_not_success(smtp):
    smtp[1].send_message.return_value = {"erika@example.test": (550, b"rejected")}
    with pytest.raises(mail.SMTPDeliveryError, match="smtp_delivery_failed"):
        await mail.send_customer_summary(
            summary="Rückruf", full_name="Erika", email="erika@example.test",
            consent_confirmed=True, email_confirmed=True, session_id="1",
        )
