"""Dedicated Olivia mail transport; no conversational tool or implicit grant.

The host must verify a sealed SCAS profile before each operation. This module
does not compose profiles, authenticate employees, or select report data.
"""

from __future__ import annotations

import hashlib
import imaplib
import json
import os
import re
import smtplib
import sqlite3
import ssl
import stat
from collections.abc import Callable
from contextlib import closing, suppress
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import formatdate
from pathlib import Path

MAILBOX = "olivia@liquisto.cloud"
APPROVED_RECIPIENTS = frozenset(
    {
        "konstantin@liquisto.com",
        "konstantin.milonas@condata.io",
        "aernout@liquisto.com",
    }
)
POLICY_VERSION = "olivia-mail-v1"
INSPECT = "olivia.mail.inspect"
SEND = "olivia.mail.send"


class MailDenied(Exception):
    """The operation is outside the verified host authorization."""


class MailUnavailable(Exception):
    """Transport/configuration failed; contains no provider details or secrets."""


class MailUncertain(Exception):
    """Delivery must be reconciled by an operator; automatic retry is forbidden."""


@dataclass(frozen=True)
class ImmutableMailProfile:
    """Narrow host view of a sealed profile, verified externally on every call."""

    profile_id: str
    tenant_id: str
    agent_id: str
    mailbox: str
    capabilities: frozenset[str]
    recipients: frozenset[str]
    source_grants: frozenset[str]
    policy_version: str


@dataclass(frozen=True)
class MailResult:
    status: str
    replayed: bool


@dataclass(frozen=True)
class _Credentials:
    password: str = field(repr=False)


def _protected_path(path: Path) -> None:
    try:
        if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
            raise MailUnavailable("Protected absolute paths are required.")
        if path.exists() and os.name != "nt":
            _protected_stat(path.stat())
    except OSError:
        raise MailUnavailable("Protected file metadata is unavailable.") from None


def _protected_stat(info: os.stat_result) -> None:
    if os.name != "nt" and (
        info.st_uid not in {0, os.geteuid()} or stat.S_IMODE(info.st_mode) & 0o077
    ):
        raise MailUnavailable("Protected file ownership and permissions are required.")


def _load_credentials(path: Path) -> _Credentials:
    """Protected loader shared by runtime and explicitly privileged operators."""
    _protected_path(path)
    try:
        parent = path.parent.stat()
        if os.name != "nt" and (
            parent.st_uid not in {0, os.geteuid()} or stat.S_IMODE(parent.st_mode) & 0o022
        ):
            raise ValueError
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as credential_file:
            info = os.fstat(credential_file.fileno())
            _protected_stat(info)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 8192:
                raise ValueError
            raw = credential_file.read(8193)
            if len(raw) > 8192:
                raise ValueError
        record = json.loads(raw)
        if (
            set(record) != {"username", "password"}
            or record["username"] != MAILBOX
            or not isinstance(record["password"], str)
            or not record["password"]
            or "\x00" in record["password"]
        ):
            raise ValueError
        return _Credentials(record["password"])
    except Exception:
        raise MailUnavailable("Dedicated mailbox credentials are unavailable.") from None


class OliviaMailTransport:
    """Callable by a separately governed host mail workflow only.

    verify_profile must consult the host's authoritative sealed profile and
    current grants. A boolean supplied by a model/request is not a verifier.
    Payload provenance and employee data visibility belong to that host gate.
    """

    def __init__(
        self,
        credentials_path: Path,
        outbox_path: Path,
        verify_profile: Callable[[ImmutableMailProfile, str], bool],
    ) -> None:
        self.credentials_path = credentials_path
        self.outbox_path = outbox_path
        self.verify_profile = verify_profile

    @staticmethod
    def _validate_profile(profile: ImmutableMailProfile, capability: str) -> None:
        if (
            not isinstance(profile, ImmutableMailProfile)
            or not isinstance(profile.capabilities, frozenset)
            or not isinstance(profile.recipients, frozenset)
            or not isinstance(profile.source_grants, frozenset)
            or not isinstance(profile.profile_id, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", profile.profile_id)
            or profile.tenant_id != "liquisto"
            or profile.agent_id != "liquisto-assistant"
            or profile.mailbox != MAILBOX
            or profile.policy_version != POLICY_VERSION
            or capability not in profile.capabilities
            or not profile.capabilities <= {INSPECT, SEND}
            or not profile.recipients
            or not profile.recipients <= APPROVED_RECIPIENTS
            or (capability == SEND and not profile.source_grants)
        ):
            raise MailDenied("A matching sealed mail profile is required.")

    def _authorize(self, profile: ImmutableMailProfile, capability: str) -> None:
        self._validate_profile(profile, capability)
        try:
            accepted = self.verify_profile(profile, capability) is True
        except Exception:
            accepted = False
        if not accepted:
            raise MailDenied("Host profile verification failed.")

    def _credentials(self) -> _Credentials:
        return _load_credentials(self.credentials_path)

    def inspect_imap(self, profile: ImmutableMailProfile) -> dict[str, int]:
        """Login and inspect INBOX counts, without messages or flag changes."""
        self._authorize(profile, INSPECT)
        credentials = self._credentials()
        try:
            with imaplib.IMAP4_SSL(
                "ssl0.ovh.net", 993, ssl_context=ssl.create_default_context(), timeout=20
            ) as client:
                client.login(MAILBOX, credentials.password)
                status, _ = client.select("INBOX", readonly=True)
                if status != "OK":
                    raise ValueError
                status, result = client.status("INBOX", "(MESSAGES UNSEEN UIDVALIDITY)")
                if status != "OK" or len(result) != 1 or not isinstance(result[0], bytes):
                    raise ValueError
                fields = {}
                for name in ("MESSAGES", "UNSEEN", "UIDVALIDITY"):
                    found = re.search(rb"\b" + name.encode() + rb" ([0-9]+)\b", result[0])
                    if not found:
                        raise ValueError
                    fields[name.lower()] = int(found[1])
                if fields["uidvalidity"] < 1:
                    raise ValueError
                return fields
        except Exception:
            raise MailUnavailable("Mailbox metadata verification failed.") from None

    def inspect_smtp(self, profile: ImmutableMailProfile) -> None:
        """TLS/login check only. Does not issue MAIL FROM, RCPT TO, or DATA."""
        self._authorize(profile, INSPECT)
        credentials = self._credentials()
        client = None
        try:
            client = self._smtp(credentials)
        except Exception:
            raise MailUnavailable("Mail transport authentication failed.") from None
        finally:
            if client is not None:
                with suppress(Exception):
                    client.close()

    @staticmethod
    def _smtp(credentials: _Credentials) -> smtplib.SMTP:
        client = smtplib.SMTP("ssl0.ovh.net", 587, timeout=20)
        try:
            client.ehlo()
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
            client.login(MAILBOX, credentials.password)
            return client
        except Exception:
            client.close()
            raise

    def _ledger(self) -> sqlite3.Connection:
        _protected_path(self.outbox_path)
        _protected_path(self.outbox_path.parent)
        try:
            if not self.outbox_path.exists():
                fd = os.open(self.outbox_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(fd)
            db = sqlite3.connect(self.outbox_path, timeout=15)
            db.execute("PRAGMA synchronous=FULL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS outbox "
                "(key TEXT PRIMARY KEY, digest TEXT NOT NULL, status TEXT NOT NULL)"
            )
            return db
        except FileExistsError:
            return self._ledger()
        except Exception:
            raise MailUnavailable("Protected outbox is unavailable.") from None

    @staticmethod
    def _recipients(values: tuple[str, ...], profile: ImmutableMailProfile) -> tuple[str, ...]:
        if not isinstance(values, tuple):
            raise MailDenied("Recipients must be an explicit address tuple.")
        canonical = []
        for value in values:
            if (
                not isinstance(value, str)
                or value != value.strip()
                or any(c in value for c in "\r\n\x00")
            ):
                raise MailDenied("Invalid recipient.")
            address = value.lower()
            if address not in APPROVED_RECIPIENTS or address not in profile.recipients:
                raise MailDenied("Recipient is not approved.")
            canonical.append(address)
        return tuple(canonical)

    def send_text(
        self,
        profile: ImmutableMailProfile,
        *,
        to: tuple[str, ...],
        subject: str,
        body: str,
        idempotency_key: str,
        cc: tuple[str, ...] = (),
        bcc: tuple[str, ...] = (),
        thread_capability: str | None = None,
        thread_invitation: bool = False,
    ) -> MailResult:
        """Send a host-approved plain-text work output to exact approved employees.

        No caller-controlled headers, sender, SMTP host, attachments, or raw MIME.
        Uncertain delivery is durable and cannot be retried by this adapter.
        """
        self._validate_profile(profile, SEND)
        if type(thread_invitation) is not bool or (thread_invitation and thread_capability is None):
            raise MailDenied("A thread invitation requires an explicit host capability.")
        if thread_capability is not None and (
            not isinstance(thread_capability, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{43}", thread_capability)
        ):
            raise MailDenied("Invalid host reply-thread capability.")
        to, cc, bcc = (self._recipients(values, profile) for values in (to, cc, bcc))
        recipients = tuple(sorted(set(to + cc + bcc)))
        if not to or not recipients:
            raise MailDenied("At least one approved To recipient is required.")
        if (
            not isinstance(subject, str)
            or not subject.strip()
            or len(subject) > 200
            or any(ord(c) < 32 or ord(c) == 127 for c in subject)
            or not isinstance(body, str)
            or not body.strip()
            or "\x00" in body
            or len(body.encode("utf-8")) > 64000
            or not isinstance(idempotency_key, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", idempotency_key)
        ):
            raise MailDenied("Invalid plain-text work message.")
        key = hashlib.sha256((MAILBOX + ":" + idempotency_key).encode()).hexdigest()
        # Preserve existing accepted entries when no new thread was requested.
        content_binding = [MAILBOX, to, cc, bcc, subject, body]
        if thread_capability is not None:
            content_binding.extend((thread_capability, thread_invitation))
        digest = hashlib.sha256(
            json.dumps(content_binding, separators=(",", ":")).encode()
        ).hexdigest()
        with closing(self._ledger()) as db:
            prior = db.execute("SELECT digest,status FROM outbox WHERE key=?", (key,)).fetchone()
            if prior:
                return self._prior(prior, digest)
        credentials = self._credentials()
        client = None
        reserved = False
        try:
            client = self._smtp(credentials)
            message = EmailMessage(policy=SMTP)
            message["From"] = MAILBOX
            message["To"] = ", ".join(to)
            if cc:
                message["Cc"] = ", ".join(cc)
            message["Subject"] = subject
            message["Date"] = formatdate(localtime=False)
            anchor = f"<olivia-thread.{thread_capability}@liquisto.cloud>"
            message_id = f"olivia-thread.{thread_capability}" if thread_invitation else key
            message["Message-ID"] = f"<{message_id}@liquisto.cloud>"
            if thread_capability is not None and not thread_invitation:
                message["In-Reply-To"] = anchor
                message["References"] = anchor
            message.set_content(body)
            with closing(self._ledger()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                prior = db.execute(
                    "SELECT digest,status FROM outbox WHERE key=?", (key,)
                ).fetchone()
                if prior:
                    return self._prior(prior, digest)
                db.execute("INSERT INTO outbox VALUES (?, ?, 'uncertain')", (key, digest))
            reserved = True
            # Obtain one fresh single-use SEND receipt after TLS/login and
            # durable reservation, immediately before the SMTP transmission.
            # Revocation or authority failure leaves the reservation quarantined.
            self._authorize(profile, SEND)
            refused = client.sendmail(MAILBOX, recipients, message.as_bytes())
            if refused:
                raise MailUncertain("Delivery requires operator reconciliation.")
            with closing(self._ledger()) as db, db:
                db.execute("UPDATE outbox SET status='accepted' WHERE key=?", (key,))
            return MailResult("accepted", False)
        except (MailDenied, MailUncertain):
            raise
        except Exception:
            if reserved:
                raise MailUncertain("Delivery requires operator reconciliation.") from None
            raise MailUnavailable("Mail transport is unavailable.") from None
        finally:
            if client is not None:
                with suppress(Exception):
                    client.close()

    @staticmethod
    def _prior(prior: tuple[str, str], digest: str) -> MailResult:
        if prior[0] != digest:
            raise MailDenied("Idempotency key belongs to a different message.")
        if prior[1] != "accepted":
            raise MailUncertain("Delivery requires operator reconciliation.")
        return MailResult("accepted", True)
