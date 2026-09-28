"""Run interactively as root on the ANNA host; never paste secrets into chat."""

import getpass
import os
from pathlib import Path


def main():
    path = Path("/etc/anna/calendar.env")
    if os.geteuid() != 0 or not path.exists():
        raise SystemExit("Run as root after the disabled sidecar has been installed.")
    values = dict(line.split("=", 1) for line in path.read_text().splitlines() if "=" in line)
    for key, label in (("MS_TENANT_ID", "Directory (tenant) ID"), ("MS_CLIENT_ID", "Application (client) ID"), ("MS_CLIENT_SECRET", "Client secret VALUE")):
        value = getpass.getpass(label + ": ").strip()
        # Entra client-secret values can legitimately contain shell metacharacters.
        # They are written directly to a root-only file, never evaluated by a shell.
        if not value or any(c in value for c in "\r\n\x00"):
            raise SystemExit("Invalid value; configuration unchanged.")
        values[key] = value
    values["MS_AUTHORITY_TENANT"] = values["MS_TENANT_ID"]
    values["ANNA_CALENDAR_MODE"] = "test"
    temporary = path.with_suffix(".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        output.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    temporary.replace(path)
    print("Saved protected test configuration. Restart only the calendar sidecar.")
    print("Web redirect URI: " + values["MS_REDIRECT_URI"])
    print("The setup token remains in /etc/anna/calendar.env. View it only in your private SSH terminal.")


if __name__ == "__main__":
    main()
