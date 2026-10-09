"""Privileged check is independent of runtime grants and never sends/fetches."""
import importlib.util
import json
from pathlib import Path

import pytest

from src.api.services import liquisto_mail as mail


@pytest.fixture
def operator(monkeypatch):
    script = Path(__file__).resolve().parents[2] / "deploy/liquisto-assistant/verify_olivia_mail_login.py"
    spec = importlib.util.spec_from_file_location("olivia_operator_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(module.socket, "gethostname", lambda: "scas-runtime-prod")
    monkeypatch.setattr(mail, "_load_credentials", lambda path: mail._Credentials("test-only-fixture"))
    calls = []

    class IMAP:
        def __init__(self, host, port, *, ssl_context, timeout):
            assert (host, port, timeout) == ("ssl0.ovh.net", 993, 20)
            assert ssl_context.check_hostname
            assert ssl_context.verify_mode == module.ssl.CERT_REQUIRED

        def __enter__(self):
            return self

        def __exit__(self, *args):
            calls.append("imap-logout")

        def login(self, username, password):
            assert (username, password) == ("olivia@liquisto.cloud", "test-only-fixture")
            calls.append("imap-login")

        def select(self, folder, *, readonly):
            assert (folder, readonly) == ("INBOX", True)
            calls.append("imap-readonly")
            return "OK", [b"99"]

        def status(self, folder, fields):
            assert (folder, fields) == ("INBOX", "(MESSAGES UNSEEN UIDVALIDITY)")
            calls.append("imap-metadata")
            return "OK", [b"INBOX (MESSAGES 99 UNSEEN 2 UIDVALIDITY 5)"]

    class SMTP:
        def __init__(self, host, port, *, timeout):
            assert (host, port, timeout) == ("ssl0.ovh.net", 587, 20)

        def ehlo(self):
            calls.append("smtp-ehlo")

        def starttls(self, *, context):
            assert context.check_hostname
            assert context.verify_mode == module.ssl.CERT_REQUIRED
            calls.append("smtp-starttls")

        def login(self, username, password):
            assert (username, password) == ("olivia@liquisto.cloud", "test-only-fixture")
            calls.append("smtp-login")

        def quit(self):
            calls.append("smtp-quit")

    monkeypatch.setattr(module.imaplib, "IMAP4_SSL", IMAP)
    monkeypatch.setattr(module.smtplib, "SMTP", SMTP)
    return module, calls


def test_operator_checks_metadata_and_auth_without_runtime_profile(operator):
    module, calls = operator
    result = module.verify_login()
    assert result["imap_metadata_verified"] and result["smtp_tls_authenticated"]
    assert all(type(value) is bool for value in result.values())
    assert not result["mail_sent"] and not result["message_bodies_read"]
    assert calls == ["imap-login", "imap-readonly", "imap-metadata", "imap-logout",
                     "smtp-ehlo", "smtp-starttls", "smtp-ehlo", "smtp-login", "smtp-quit"]


@pytest.mark.parametrize("uid,host", [(1001, "scas-runtime-prod"), (0, "other-host")])
def test_nonprivileged_or_foreign_host_cannot_open_credentials(operator, monkeypatch, uid, host):
    module, calls = operator
    monkeypatch.setattr(module.os, "geteuid", lambda: uid)
    monkeypatch.setattr(module.socket, "gethostname", lambda: host)
    credential_reads = []
    monkeypatch.setattr(mail, "_load_credentials", lambda path: credential_reads.append(path))
    assert not module.verify_login()["operator_preconditions"]
    assert credential_reads == [] and calls == []


def test_missing_credentials_never_contact_provider(operator, monkeypatch):
    module, calls = operator

    def fail(path):
        assert path == module.CREDENTIALS_PATH
        raise RuntimeError("secret fixture unavailable")

    monkeypatch.setattr(mail, "_load_credentials", fail)
    result = module.verify_login()
    assert result["operator_preconditions"] and not result["credentials_available"]
    assert calls == []
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize("transport", ["imap", "smtp"])
def test_provider_failure_has_only_boolean_results(operator, monkeypatch, transport):
    module, _ = operator

    def fail(*args, **kwargs):
        raise RuntimeError("private provider fixture")

    if transport == "imap":
        monkeypatch.setattr(module.imaplib, "IMAP4_SSL", fail)
    else:
        monkeypatch.setattr(module.smtplib, "SMTP", fail)
    result = module.verify_login()
    assert all(type(value) is bool for value in result.values())
    assert "private" not in json.dumps(result)
    assert not result["mail_sent"] and not result["message_bodies_read"]


def test_operator_main_emits_only_boolean_json(operator, capsys):
    module, _ = operator
    assert module.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert all(type(value) is bool for value in output.values())
