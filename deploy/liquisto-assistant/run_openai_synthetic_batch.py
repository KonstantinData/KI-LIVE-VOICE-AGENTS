"""Separate test process; never imports app startup, binds a service, or sends mail."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import stat
import sys
from pathlib import Path

from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.api.services.liquisto_mail_openai import PRICE_SNAPSHOT  # noqa: E402
from src.api.services.liquisto_openai_budget import OpenAIHttpBudget  # noqa: E402
from src.api.services.liquisto_openai_synthetic_batch import (  # noqa: E402
    BATCH_ID, batch_request_bytes, run_batch,
)


def protected_key(path: Path) -> SecretStr:
    """Read only the separately approved key file; emit no value, prefix, or length."""
    if not path.is_absolute() or any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 16384:
            raise ValueError
        if os.name != "nt" and (info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600):
            raise ValueError
        lines = handle.read(16385).decode("utf-8", errors="strict").splitlines()
    entries = []
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"OLIVIA_OPENAI_API_KEY=(.+)", line)
        if not match:
            raise ValueError
        value = match[1]
        if value[:1] in {"'", '"'}:
            if len(value) < 3 or value[-1] != value[0]:
                raise ValueError
            value = value[1:-1]
        if not re.fullmatch(r"[^\s'\"\x00-\x1f]+", value):
            raise ValueError
        entries.append(value)
    if len(entries) != 1:
        raise ValueError
    return SecretStr(entries[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--ledger-file", type=Path)
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--approved-price-snapshot")
    parser.add_argument("--describe", action="store_true")
    args = parser.parse_args()
    if args.describe:
        import hashlib

        print(json.dumps({"batch_id": BATCH_ID, "payload_sha256": hashlib.sha256(batch_request_bytes()).hexdigest(),
                          "maximum_http_calls": 2, "maximum_input_tokens": 8192,
                          "maximum_output_tokens": 2560, "price_snapshot": PRICE_SNAPSHOT,
                          "maximum_standard_generation_cost_micro_usd": 3584}))
        return
    if (not args.key_file or not args.ledger_file or not args.output_file
            or args.approved_price_snapshot != PRICE_SNAPSHOT):
        raise SystemExit("synthetic_batch_explicit_configuration_required")
    result = {"batch_id": BATCH_ID, "status": "failed", "answers": {}, "usage": {}}
    budget = OpenAIHttpBudget(args.ledger_file)
    try:
        # Reserve a new protected result path before consuming any provider budget.
        from src.api.services.liquisto_mail import _protected_path

        _protected_path(args.output_file)
        _protected_path(args.output_file.parent)
        fd = os.open(args.output_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            try:
                result["answers"] = asyncio.run(run_batch(
                    protected_key(args.key_file), budget, usage_out=result["usage"],
                ))
                result["status"] = "completed"
            except Exception:
                result["reason"] = "synthetic_batch_failed_or_denied_no_retry"
            result["http_attempts"] = budget.attempts()
            json.dump(result, output, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        raise SystemExit("synthetic_batch_local_configuration_unavailable_no_retry") from None
    print(json.dumps({"batch_id": BATCH_ID, "status": result["status"], "http_attempts": result["http_attempts"]}))
    if result["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
