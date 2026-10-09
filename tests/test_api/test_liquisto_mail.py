"""No live provider access: every transport is a strict in-memory mock."""
from dataclasses import FrozenInstanceError, replace
from email import message_from_bytes
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.api.services import liquisto_mail as mail


class FakeSMTP:
    def __init__(self):
        self.calls = []
        self.refused = {}
        self.failure = None

    def ehlo(self):
        self.calls.append("ehlo")

    def starttls(self, *, context):
        assert context.verify_mode == mail.ssl.CERT_REQUIRED
        assert context.check_hostname
        self.calls.append("starttls")

    def login(self, username, password):
        assert username == mail.MAILBOX
        assert password == "test-only-fixture"
        self.calls.append("login")

    def sendmail(self, sender, recipients, payload):
        self.calls.append((sender, recipients, payload))
        if self.failure:
            raise self.failure
        return self.refused

    def close(self):
        self.calls.append("close")


@pytest.fixture
def setup(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    credentials = tmp_path / "credentials.json"
    credentials.write_text('{"username":"olivia@liquisto.cloud","password":"test-only-fixture"}')
    credentials.chmod(0o600)
    profile = mail.ImmutableMailProfile(
        "sealed-test-profile", "liquisto", "liquisto-assistant", mail.MAILBOX,
        frozenset({mail.SEND, mail.INSPECT}), mail.APPROVED_RECIPIENTS,
        frozenset({"fixture-approved-work-output"}), mail.POLICY_VERSION,
    )
    smtp = FakeSMTP()

    def connect(host, port, *, timeout):
        assert (host, port, timeout) == ("ssl0.ovh.net", 587, 20)
        smtp.calls.append("connect")
        return smtp

    monkeypatch.setattr(mail.smtplib, "SMTP", connect)
    transport = mail.OliviaMailTransport(credentials, tmp_path / "outbox.sqlite", lambda p, c: p == profile)
    return transport, profile, smtp


def send(transport, profile, **kwargs):
    values = dict(to=("konstantin@liquisto.com",), subject="Work output", body="Synthetic test output.",
                  idempotency_key="test-idempotency-0001")
    values.update(kwargs)
    return transport.send_text(profile, **values)


def test_fixed_sender_tls_and_hidden_bcc_envelope(setup):
    transport, profile, smtp = setup
    result = send(transport, profile, cc=("aernout@liquisto.com",), bcc=("konstantin.milonas@condata.io",))
    assert result == mail.MailResult("accepted", False)
    assert smtp.calls[:5] == ["connect", "ehlo", "starttls", "ehlo", "login"]
    sender, envelope, raw = next(c for c in smtp.calls if isinstance(c, tuple))
    message = message_from_bytes(raw)
    assert sender == mail.MAILBOX == message["From"]
    assert set(envelope) == mail.APPROVED_RECIPIENTS
    assert message["Bcc"] is None
    assert not message.is_multipart()


def test_host_thread_capability_message_id_is_bound_to_retry(setup):
    transport, profile, smtp = setup
    token = "x" * 43
    assert send(transport, profile, thread_capability=token, thread_invitation=True).status == "accepted"
    raw = next(c[2] for c in smtp.calls if isinstance(c, tuple))
    assert message_from_bytes(raw)["Message-ID"] == f"<olivia-thread.{token}@liquisto.cloud>"
    assert send(transport, profile, thread_capability=token, thread_invitation=True).replayed is True
    with pytest.raises(mail.MailDenied):
        send(transport, profile, thread_capability="y" * 43)
    with pytest.raises(mail.MailDenied):
        send(transport, profile)
    with pytest.raises(mail.MailDenied):
        send(transport, profile, thread_capability=token, thread_invitation=False)


def test_two_replies_have_unique_message_ids_and_same_anchor(setup):
    transport, profile, smtp = setup
    token = "x" * 43
    send(transport, profile, thread_capability=token)
    send(transport, profile, thread_capability=token, idempotency_key="test-idempotency-0002")
    messages = [message_from_bytes(c[2]) for c in smtp.calls if isinstance(c, tuple)]
    assert len(messages) == 2
    assert messages[0]["Message-ID"] != messages[1]["Message-ID"]
    anchor = f"<olivia-thread.{token}@liquisto.cloud>"
    for message in messages:
        assert message["Message-ID"] != anchor
        assert message["In-Reply-To"] == message["References"] == anchor


@pytest.mark.parametrize("values", [
    {"thread_invitation": True}, {"thread_invitation": 1},
    {"thread_invitation": "false", "thread_capability": "x" * 43},
    {"thread_invitation": None},
])
def test_thread_invitation_flag_is_closed_and_requires_token(setup, values):
    transport, profile, smtp = setup
    with pytest.raises(mail.MailDenied):
        send(transport, profile, **values)
    assert not smtp.calls


def test_send_authority_is_fresh_after_tls_login_and_durable_reservation(setup):
    transport, profile, smtp = setup
    checked = []

    def verify(current, capability):
        assert current == profile and capability == mail.SEND
        assert smtp.calls[-1] == "login"
        with mail.sqlite3.connect(transport.outbox_path) as db:
            assert db.execute("SELECT status FROM outbox").fetchone() == ("uncertain",)
        checked.append("fresh-send-authority")
        smtp.calls.append("fresh-send-authority")
        return True

    transport.verify_profile = verify
    send(transport, profile)
    assert checked == ["fresh-send-authority"]
    assert isinstance(smtp.calls[6], tuple)


def test_revocation_during_smtp_login_denies_transmission_and_quarantines(setup):
    transport, profile, smtp = setup
    transport.verify_profile = lambda _profile, _capability: False
    with pytest.raises(mail.MailDenied):
        send(transport, profile)
    assert smtp.calls == ["connect", "ehlo", "starttls", "ehlo", "login", "close"]
    with mail.sqlite3.connect(transport.outbox_path) as db:
        assert db.execute("SELECT status FROM outbox").fetchone() == ("uncertain",)
    with pytest.raises(mail.MailUncertain):
        send(transport, profile)
    assert not any(isinstance(call, tuple) for call in smtp.calls)


@pytest.mark.parametrize("token", ["short", "x" * 44, "x" * 42 + "\n", "x" * 42 + ".", 12])
def test_thread_capability_never_allows_header_injection(setup, token):
    transport, profile, smtp = setup
    with pytest.raises(mail.MailDenied):
        send(transport, profile, thread_capability=token)
    assert not smtp.calls


@pytest.mark.parametrize("field", ["to", "cc", "bcc"])
@pytest.mark.parametrize("address", ["outsider@liquisto.com", "aernout@liquisto.com\r\nBcc:evil@example.com",
                                     "Aernout <aernout@liquisto.com>", "aernout@liquisto.com "])
def test_every_recipient_channel_fails_before_provider(setup, field, address):
    transport, profile, smtp = setup
    with pytest.raises(mail.MailDenied):
        send(transport, profile, **{field: (address,)})
    assert smtp.calls == []


@pytest.mark.parametrize("change", [
    {"tenant_id": "foreign"}, {"agent_id": "foreign"}, {"mailbox": "olivia@liquisto.com"},
    {"capabilities": frozenset({mail.INSPECT})}, {"policy_version": "unknown"},
    {"recipients": frozenset({"outsider@example.com"})}, {"capabilities": {mail.SEND}},
    {"source_grants": frozenset()}, {"capabilities": frozenset({mail.SEND, "mail.delete"})},
])
def test_host_profile_is_not_a_persona_grant(setup, change):
    transport, profile, smtp = setup
    with pytest.raises(mail.MailDenied):
        send(transport, replace(profile, **change))
    assert smtp.calls == []


def test_invalid_host_verifier_cannot_read_credentials(setup):
    transport, profile, smtp = setup
    transport.verify_profile = lambda p, c: False
    transport.credentials_path = Path("must-not-be-opened")
    with pytest.raises(mail.MailDenied):
        transport.inspect_imap(profile)
    assert smtp.calls == []


def test_profile_is_immutable(setup):
    _, profile, _ = setup
    with pytest.raises(FrozenInstanceError):
        profile.tenant_id = "foreign"


@pytest.mark.parametrize("change", [
    {"subject": "Injected\r\nBcc: evil@example.com"}, {"body": "x" * 64001},
    {"body": "\x00"}, {"to": ()}, {"idempotency_key": "short"},
    {"to": ["konstantin@liquisto.com"]},
])
def test_invalid_message_never_connects(setup, change):
    transport, profile, smtp = setup
    with pytest.raises(mail.MailDenied):
        send(transport, profile, **change)
    assert smtp.calls == []


def test_same_key_replay_survives_adapter_restart(setup):
    transport, profile, smtp = setup
    send(transport, profile)
    restarted = mail.OliviaMailTransport(transport.credentials_path, transport.outbox_path, transport.verify_profile)
    assert send(restarted, profile) == mail.MailResult("accepted", True)
    assert len([c for c in smtp.calls if isinstance(c, tuple)]) == 1
    assert transport.outbox_path.read_bytes().find(b"Synthetic test output") == -1


def test_key_cannot_be_reused_for_other_content(setup):
    transport, profile, smtp = setup
    send(transport, profile)
    with pytest.raises(mail.MailDenied):
        send(transport, profile, body="Different output")
    assert len([c for c in smtp.calls if isinstance(c, tuple)]) == 1


@pytest.mark.parametrize("partial", [True, False])
def test_uncertain_or_partial_send_never_retries(setup, partial):
    transport, profile, smtp = setup
    if partial:
        smtp.refused = {"konstantin@liquisto.com": (550, b"refused")}
    else:
        smtp.failure = OSError("provider text with sensitive fixture")
    with pytest.raises(mail.MailUncertain, match="operator reconciliation"):
        send(transport, profile)
    restarted = mail.OliviaMailTransport(transport.credentials_path, transport.outbox_path, transport.verify_profile)
    with pytest.raises(mail.MailUncertain, match="operator reconciliation"):
        send(restarted, profile)
    assert len([c for c in smtp.calls if isinstance(c, tuple)]) == 1


def test_credentials_wrong_account_is_rejected_without_provider(setup):
    transport, profile, smtp = setup
    transport.credentials_path.write_text('{"username":"other@example.com","password":"fixture"}')
    with pytest.raises(mail.MailUnavailable) as failure:
        send(transport, profile)
    assert "fixture" not in str(failure.value)
    assert smtp.calls == []


def test_smtp_inspection_has_no_send_command(setup):
    transport, profile, smtp = setup
    transport.inspect_smtp(profile)
    assert not any(isinstance(c, tuple) for c in smtp.calls)


def test_imap_inspection_is_readonly_and_has_no_fetch_or_store(setup, monkeypatch):
    transport, profile, _ = setup
    calls = []

    class FakeIMAP:
        def __init__(self, host, port, *, ssl_context, timeout):
            assert (host, port, timeout) == ("ssl0.ovh.net", 993, 20)
            assert ssl_context.check_hostname
            assert ssl_context.verify_mode == mail.ssl.CERT_REQUIRED

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def login(self, username, password):
            assert username == mail.MAILBOX

        def select(self, folder, *, readonly):
            calls.append((folder, readonly))
            return "OK", [b"12"]

        def status(self, folder, fields):
            calls.append((folder, fields))
            return "OK", [b'INBOX (MESSAGES 12 UNSEEN 3 UIDVALIDITY 99)']

    monkeypatch.setattr(mail.imaplib, "IMAP4_SSL", FakeIMAP)
    assert transport.inspect_imap(profile) == {"messages": 12, "unseen": 3, "uidvalidity": 99}
    assert calls == [("INBOX", True), ("INBOX", "(MESSAGES UNSEEN UIDVALIDITY)")]


def test_provider_exception_does_not_expose_details(setup, monkeypatch):
    transport, profile, _ = setup

    def fail(*args, **kwargs):
        raise RuntimeError("secret provider fixture")

    monkeypatch.setattr(mail.smtplib, "SMTP", fail)
    with pytest.raises(mail.MailUnavailable) as failure:
        transport.inspect_smtp(profile)
    assert "secret" not in str(failure.value)


def test_inspect_only_profile_can_authenticate_but_cannot_send(setup):
    transport, profile, smtp = setup
    inspected = replace(profile, capabilities=frozenset({mail.INSPECT}), source_grants=frozenset())
    transport.verify_profile = lambda p, c: p == inspected
    transport.inspect_smtp(inspected)
    with pytest.raises(mail.MailDenied):
        send(transport, inspected)
    assert not any(isinstance(c, tuple) for c in smtp.calls)


def test_restrictive_profile_cannot_add_approved_but_ungranted_recipient(setup):
    transport, profile, smtp = setup
    restricted = replace(profile, recipients=frozenset({"konstantin@liquisto.com"}))
    transport.verify_profile = lambda p, c: p == restricted
    with pytest.raises(mail.MailDenied):
        send(transport, restricted, cc=("aernout@liquisto.com",))
    assert smtp.calls == []


def test_operator_credential_path_is_required(setup):
    transport, profile, smtp = setup
    transport.credentials_path = Path("relative-credentials.json")
    with pytest.raises(mail.MailUnavailable):
        transport.inspect_smtp(profile)
    assert smtp.calls == []


def test_host_verifier_failure_fails_closed(setup):
    transport, profile, smtp = setup

    def unavailable(profile, capability):
        raise RuntimeError("host authorization unavailable")

    transport.verify_profile = unavailable
    with pytest.raises(mail.MailDenied):
        send(transport, profile)
    assert smtp.calls == ["connect", "ehlo", "starttls", "ehlo", "login", "close"]
    with mail.sqlite3.connect(transport.outbox_path) as db:
        assert db.execute("SELECT status FROM outbox").fetchone() == ("uncertain",)


def test_send_ledger_race_cannot_emit_duplicate(setup, monkeypatch):
    transport, profile, smtp = setup
    original = transport._smtp
    raced = False

    def concurrent_accept(credentials):
        nonlocal raced
        if not raced:
            raced = True
            transport._smtp = original
            send(transport, profile)
        return original(credentials)

    monkeypatch.setattr(transport, "_smtp", concurrent_accept)
    assert send(transport, profile) == mail.MailResult("accepted", True)
    assert len([c for c in smtp.calls if isinstance(c, tuple)]) == 1


@pytest.mark.parametrize("owner,mode,allowed", [
    (0, 0o600, True), (1001, 0o600, True), (1002, 0o600, False),
    (1001, 0o644, False), (1001, 0o660, False),
])
def test_linux_owner_and_permissions_fail_closed(monkeypatch, owner, mode, allowed):
    # Replace only this module's os reference; do not change Windows pathlib.
    monkeypatch.setattr(mail, "os", SimpleNamespace(name="posix", geteuid=lambda: 1001))
    info = SimpleNamespace(st_uid=owner, st_mode=mail.stat.S_IFREG | mode)
    if allowed:
        mail._protected_stat(info)
    else:
        with pytest.raises(mail.MailUnavailable, match="ownership and permissions"):
            mail._protected_stat(info)


def test_credentials_size_is_rejected_before_unbounded_read(setup, monkeypatch):
    transport, _, smtp = setup
    transport.credentials_path.write_bytes(b"x" * 8193)

    def forbidden_read(*args, **kwargs):
        raise AssertionError("unbounded path read must never be used")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    with pytest.raises(mail.MailUnavailable, match="credentials are unavailable"):
        transport._credentials()
    assert smtp.calls == []


def test_credentials_fd_read_is_bounded(setup, monkeypatch):
    transport, _, _ = setup
    original = mail.os.fdopen
    limits = []

    class BoundedReader:
        def __init__(self, reader):
            self.reader = reader

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.reader.close()

        def fileno(self):
            return self.reader.fileno()

        def read(self, limit):
            limits.append(limit)
            return self.reader.read(limit)

    monkeypatch.setattr(mail.os, "fdopen", lambda fd, mode: BoundedReader(original(fd, mode)))
    assert transport._credentials().password == "test-only-fixture"
    assert limits == [8193]


def test_credential_open_failure_is_sanitized(setup, monkeypatch):
    transport, _, _ = setup

    def denied(*args, **kwargs):
        raise PermissionError("private provider fixture")

    monkeypatch.setattr(mail.os, "open", denied)
    with pytest.raises(mail.MailUnavailable) as failure:
        transport._credentials()
    assert "private" not in str(failure.value)
