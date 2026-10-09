#!/usr/bin/env python3
"""Privileged login-only acceptance on the fixed production host.

This operator script neither authorizes a runtime mail profile nor reads/sends
messages. It cannot be called as a conversational tool.
"""
from __future__ import annotations

import imaplib
import json
import os
import re
import smtplib
import socket
import ssl
import sys
from pathlib import Path

CREDENTIALS_PATH = Path("/etc/liquisto-assistant/olivia-mail-credentials.json")
MAILBOX = "olivia@liquisto.cloud"


def verify_login() -> dict[str, bool]:
    result = {
        "operator_preconditions": False,
        "credentials_available": False,
        "imap_authenticated": False,
        "imap_metadata_verified": False,
        "smtp_tls_authenticated": False,
        "mail_sent": False,
        "message_bodies_read": False,
    }
    if (
        not hasattr(os, "geteuid") or os.geteuid() != 0
        or socket.gethostname() != "scas-runtime-prod"
    ):
        return result
    result["operator_preconditions"] = True
    try:
        # Keep the entrypoint usable in a reviewed release directory alongside
        # its src/ tree. It intentionally creates no runtime authorization.
        repository_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repository_root))
        from src.api.services.liquisto_mail import _load_credentials

        credentials = _load_credentials(CREDENTIALS_PATH)
        result["credentials_available"] = True
    except Exception:
        return result
    try:
        with imaplib.IMAP4_SSL(
            "ssl0.ovh.net", 993, ssl_context=ssl.create_default_context(), timeout=20
        ) as client:
            client.login(MAILBOX, credentials.password)
            result["imap_authenticated"] = True
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                raise ValueError
            status, data = client.status("INBOX", "(MESSAGES UNSEEN UIDVALIDITY)")
            if status != "OK" or len(data) != 1 or not isinstance(data[0], bytes):
                raise ValueError
            fields = {}
            for field in ("MESSAGES", "UNSEEN", "UIDVALIDITY"):
                value = re.search(rb"\b" + field.encode() + rb" ([0-9]+)\b", data[0])
                if not value:
                    raise ValueError
                fields[field] = int(value[1])
            result["imap_metadata_verified"] = fields["UIDVALIDITY"] > 0
    except Exception:
        pass
    smtp = None
    try:
        smtp = smtplib.SMTP("ssl0.ovh.net", 587, timeout=20)
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(MAILBOX, credentials.password)
        result["smtp_tls_authenticated"] = True
    except Exception:
        pass
    finally:
        if smtp is not None:
            try:
                smtp.quit()
            except Exception:
                try:
                    smtp.close()
                except Exception:
                    pass
    return result


def main() -> int:
    result = verify_login()
    print(json.dumps(result, sort_keys=True))
    return 0 if all(result[key] for key in (
        "operator_preconditions", "credentials_available", "imap_authenticated",
        "imap_metadata_verified", "smtp_tls_authenticated",
    )) else 1


if __name__ == "__main__":
    raise SystemExit(main())
