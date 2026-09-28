"""Small status snapshots without caller data, transcripts or credentials."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import Lock

_write_lock = Lock()


def write_status(path: Path | None, state: str) -> None:
    """Atomically replace a non-sensitive local status snapshot."""
    if path is None:
        return
    with _write_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f".{os.getpid()}.tmp")
        temporary.write_text(json.dumps({
            "state": state, "pid": os.getpid(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }), encoding="utf-8")
        temporary.replace(path)


def read_status(path: Path) -> dict:
    """Ignore incomplete or absent status files; never treat them as liveness."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not (
            isinstance(value, dict)
            and isinstance(value.get("state"), str)
            and type(value.get("pid")) is int
            and isinstance(value.get("updated_at"), str)
        ):
            return {"state": "unknown"}
        return {key: value[key] for key in ("state", "pid", "updated_at")}
    except (OSError, ValueError, KeyError, TypeError):
        return {"state": "unknown"}
