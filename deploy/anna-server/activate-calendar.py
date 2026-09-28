"""Prepare approved production calendar settings on the existing Linux host.

This does not restart services. Run only after source/image rollback is retained.
OAuth secrets stay in the sidecar; the phone worker receives only its API token.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agents.anna.calendar.config import CalendarConfig  # noqa: E402


def env_values(path):
    if not path.exists():
        return {}
    return dict(line.split("=", 1) for line in path.read_text().splitlines()
                if "=" in line and not line.lstrip().startswith("#"))


def updated_env(path, updates):
    """Keep unrelated dotenv text byte-for-byte apart from line endings."""
    original = path.read_text().splitlines() if path.exists() else []
    remaining = dict(updates)
    lines = []
    for line in original:
        key = line.partition("=")[0]
        if key in updates:
            if key in remaining:
                lines.append(key + "=" + remaining.pop(key))
        else:
            lines.append(line)
    lines.extend(key + "=" + value for key, value in remaining.items())
    return "\n".join(lines) + "\n"


def compose_files(path, defaults, required):
    existing = env_values(path).get("COMPOSE_FILE", "").strip("\"'")
    paths = existing.split(":") if existing else list(defaults)
    for item in required:
        if item not in paths:
            paths.append(item)
    return ":".join(paths)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        raise SystemExit("Run as root on the existing Anna server.")
    policy = json.loads(args.policy.read_text())
    if policy.get("timezone") != "Europe/Berlin":
        raise SystemExit("Unsupported timezone; configuration unchanged.")
    config = CalendarConfig(
        mode="production", weekly_hours=json.dumps(policy["weekly_hours"]),
        duration_minutes=str(policy["duration_minutes"]),
        buffer_minutes=str(policy["buffer_minutes"]),
        minimum_notice_hours=str(policy.get("minimum_notice_hours", 24)),
    )
    config.validate_policy()
    calendar_env = Path("/etc/anna/calendar.env")
    client_env = Path("/etc/anna/calendar-client.env")
    phone_env = Path("/opt/anna/deploy/anna-server/.env")
    project_env = Path("/opt/anna-calendar/.env")
    values = env_values(calendar_env)
    token = values.get("ANNA_CALENDAR_API_TOKEN", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token):
        raise SystemExit("Unsupported API token encoding; configuration unchanged.")
    if values.get("MS_CALENDAR_USER") != "kontakt@konstantinmilonas.de":
        raise SystemExit("Unexpected master calendar; configuration unchanged.")
    updates = {
        calendar_env: updated_env(calendar_env, {
            "ANNA_CALENDAR_MODE": "production",
            "ANNA_CALENDAR_WEEKLY_HOURS": json.dumps(policy["weekly_hours"], separators=(",", ":")),
            "ANNA_CALENDAR_DURATION_MINUTES": str(policy["duration_minutes"]),
            "ANNA_CALENDAR_BUFFER_MINUTES": str(policy["buffer_minutes"]),
            "ANNA_CALENDAR_MINIMUM_NOTICE_HOURS": str(policy.get("minimum_notice_hours", 24)),
        }),
        client_env: "\n".join([
            "ANNA_CALENDAR_API_TOKEN=" + token,
            "ANNA_CALENDAR_SERVICE_URL=http://anna-calendar:8735",
            "ANNA_CALENDAR_TOOLS_ENABLED=true", "",
        ]),
        phone_env: updated_env(phone_env, {"COMPOSE_FILE": compose_files(
            phone_env, ["compose.yaml", "compose.override.yaml"], ["compose.calendar-client.yaml"],
        )}),
        project_env: updated_env(project_env, {"COMPOSE_FILE": compose_files(
            project_env, ["deploy/anna-server/compose.calendar.yaml"],
            ["deploy/anna-server/compose.calendar-network.yaml"],
        )}),
    }
    os.umask(0o077)
    backup = Path("/opt/anna-backups") / datetime.now(timezone.utc).strftime("calendar-config-%Y%m%dT%H%M%SZ")
    backup.mkdir(mode=0o700)
    manifest = []
    for index, (path, content) in enumerate(updates.items()):
        if path.is_symlink():
            raise SystemExit("Refused symlink configuration path.")
        saved = backup / str(index)
        if path.exists():
            saved.write_bytes(path.read_bytes())
        manifest.append({"path": str(path), "backup": str(saved) if saved.exists() else None})
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2))
    for path, content in updates.items():
        temporary = path.with_name(path.name + ".activation-tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            output.write(content)
        temporary.replace(path)
    print("Protected settings prepared. Backup:", backup)
    print("Restart the calendar service, verify it, then restart Anna only while idle.")


if __name__ == "__main__":
    main()
