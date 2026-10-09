"""Receive credentials over SSH stdin; never print, overwrite or log secrets."""

import json
import os
import socket
import stat
import sys
from pathlib import Path

DESTINATION = Path("/etc/liquisto-assistant/olivia-mail-credentials.json")


def main():
    if socket.gethostname() != "scas-runtime-prod" or os.geteuid() != 0:
        raise ValueError("wrong-provisioning-host-or-user")
    parent = DESTINATION.parent
    metadata = parent.lstat()
    if (not stat.S_ISDIR(metadata.st_mode) or parent.resolve() != parent
            or metadata.st_uid != 0 or metadata.st_mode & 0o022):
        raise ValueError("protected-directory-required")
    data = sys.stdin.buffer.read(8193)
    if len(data) > 8192:
        raise ValueError("credential-input-budget")
    credentials = json.loads(data)
    if (set(credentials) != {"username", "password"}
            or credentials["username"] != "olivia@liquisto.cloud"
            or not isinstance(credentials["password"], str)
            or not 1 <= len(credentials["password"]) <= 2048
            or any(char in credentials["password"] for char in ("\0", "\r", "\n"))):
        raise ValueError("invalid-credential-input")
    descriptor = os.open(DESTINATION, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(credentials, stream)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"credentials_provisioned": True, "mail_activated": False}))


try:
    main()
except Exception:
    print(json.dumps({"credentials_provisioned": False,
                      "operator_review_required": True}))
    raise SystemExit(1) from None
