"""Local setup checks never register a phone or disclose credentials."""

import pytest

from src.telephony import __main__ as cli


def test_check_prints_only_credential_presence(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(cli, "load_credentials", lambda *a: None)
    monkeypatch.setattr(cli, "local_addresses", lambda *a: ("192.168.1.1", "192.168.1.2"))
    monkeypatch.setattr(cli.importlib.util, "find_spec", lambda _: True)
    for name in ("OPENAI_API_KEY", "FRITZBOX_SIP_PASSWORD", "FRITZBOX_SIP_USERNAME"):
        monkeypatch.setenv(name, "must-never-be-printed")
    assert cli.main(["--check", "--tenant", "mein-kuechenexperte",
                     "--agent", "anna-phone-assistant"]) == 0
    output = capsys.readouterr().out
    assert "must-never-be-printed" not in output
    assert "Keine SIP-Anmeldung" in output


def test_managed_start_never_prompts_for_missing_credentials(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(cli, "load_credentials", lambda *a: None)
    monkeypatch.setattr(cli, "local_addresses", lambda *a: ("192.168.1.1", "192.168.1.2"))
    monkeypatch.setattr(cli.importlib.util, "find_spec", lambda _: True)
    for name in ("OPENAI_API_KEY", "FRITZBOX_SIP_PASSWORD", "FRITZBOX_SIP_USERNAME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("builtins.input", lambda *a: pytest.fail("Must not prompt"))
    assert cli.main(["--run", "--non-interactive", "--tenant", "mein-kuechenexperte",
                     "--agent", "anna-phone-assistant"]) == 2
    assert "Anna-Einrichten.cmd" in capsys.readouterr().out


@pytest.mark.parametrize("ip", ["0.0.0.0", "127.0.0.1", "8.8.8.8"])
def test_non_lan_registrars_rejected(monkeypatch, ip):
    monkeypatch.setattr(cli.socket, "gethostbyname", lambda _: ip)
    with pytest.raises(ValueError):
        cli.local_addresses("router", "192.168.1.2")
