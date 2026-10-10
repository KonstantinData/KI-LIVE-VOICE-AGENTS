"""Regular Olivia mail provider; existing replay store holds small cost counters."""
from __future__ import annotations

import asyncio
import os
import re
import sqlite3
import stat
import time
from contextlib import closing
from pathlib import Path

import httpx
from pydantic import SecretStr

from src.api.services.liquisto_mail import _protected_path, _protected_stat
from src.api.services.liquisto_mail_openai import (
    ENDPOINT, MAX_RESPONSE_BYTES, parse_json, request_bytes, response_text,
)

MONTHLY_MICRO_USD = 25_000_000
# 24,000 request bytes + conservative 16,384 framing tokens, 512 output tokens:
# USD .010404 at the reviewed standard ceilings; debit USD .02 without refunds.
RESERVATION_MICRO_USD = 20_000


class RegularMailProviderError(Exception):
    """Sanitized terminal failure, never an instruction to retry or switch keys."""


class RegularMailBudgetStop(RegularMailProviderError):
    """Local reservation exhausted or provider project spend limit reached."""


def protected_openai_key(path: Path) -> SecretStr:
    """Dedicated Olivia file only; no shared OPENAI_API_KEY/env fallback."""
    _protected_path(path)
    parent = path.parent.stat()
    if os.name != "nt" and (parent.st_uid not in {0, os.geteuid()}
                           or stat.S_IMODE(parent.st_mode) & 0o022):
        raise ValueError
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        _protected_stat(info)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 16384:
            raise ValueError
        entries = []
        for line in handle.read(16385).decode("utf-8", errors="strict").splitlines():
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


def month() -> str:
    return time.strftime("%Y-%m", time.gmtime())


def mail_budget(path: Path, *, block_month: str | None = None) -> str:
    """One small table in the EXISTING private receipt store; no pilot ledger.

    Reserve atomically before every HTTP attempt, including failures. Preserve
    state across service processes/restarts. Verify the provider's USD25 project
    hard limit separately before activation; local tests cannot verify it.
    """
    try:
        _protected_path(path)
        _protected_path(path.parent)
        if not path.exists():
            raise ValueError  # Only the authenticated receipt path creates state.
        _protected_stat(path.stat())
        if not stat.S_ISREG(path.stat().st_mode):
            raise ValueError
        with closing(sqlite3.connect(path, timeout=15)) as db, db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            current = month()  # After acquiring the lock, never a queued timestamp.
            db.execute("CREATE TABLE IF NOT EXISTS mail_openai_months "
                       "(month TEXT PRIMARY KEY, reserved INTEGER NOT NULL, blocked INTEGER NOT NULL)")
            latest = db.execute("SELECT MAX(month) FROM mail_openai_months").fetchone()[0]
            if latest is not None and current < latest:
                raise RegularMailBudgetStop("mail_openai_budget_stopped")
            db.execute("INSERT OR IGNORE INTO mail_openai_months VALUES (?,0,0)", (current,))
            if block_month is not None:
                if not re.fullmatch(r"\d{4}-\d{2}", block_month):
                    raise ValueError
                db.execute("UPDATE mail_openai_months SET blocked=1 WHERE month=?", (block_month,))
            else:
                reserved, stopped = db.execute("SELECT reserved,blocked FROM mail_openai_months "
                                                "WHERE month=?", (current,)).fetchone()
                if stopped or reserved + RESERVATION_MICRO_USD > MONTHLY_MICRO_USD:
                    raise RegularMailBudgetStop("mail_openai_budget_stopped")
                db.execute("UPDATE mail_openai_months SET reserved=reserved+? WHERE month=?",
                           (RESERVATION_MICRO_USD, current))
            return current
    except RegularMailBudgetStop:
        raise
    except Exception:
        raise RegularMailProviderError("mail_openai_state_unavailable") from None


async def regular_openai_answer(messages: list[dict[str, str]], *, key_file: Path,
                                replay_file: Path) -> str:
    """Called only after the regular route's unchanged signed receipt validation."""
    try:
        encoded = request_bytes(messages)
        charged_month = mail_budget(replay_file)
        key = protected_openai_key(key_file)
        async with asyncio.timeout(20), httpx.AsyncClient(
            timeout=httpx.Timeout(20), follow_redirects=False, trust_env=False,
        ) as client:
            async with client.stream("POST", ENDPOINT, content=encoded, headers={
                "Authorization": "Bearer " + key.get_secret_value(),
                "Content-Type": "application/json",
            }) as response:
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise ValueError
                if response.status_code == 429:
                    try:
                        spend = parse_json(bytes(raw)).get("error", {}).get("code") in {
                            "project_spend_limit_exceeded", "organization_spend_limit_exceeded",
                        }
                    except Exception:
                        spend = False
                    if spend:
                        mail_budget(replay_file, block_month=charged_month)
                        raise RegularMailBudgetStop("mail_openai_budget_stopped")
                    raise RegularMailProviderError("mail_openai_rate_limited")
                if response.status_code != 200:
                    raise ValueError
        count = parse_json(bytes(raw))["usage"]["input_tokens"]
        if type(count) is not int or not 0 < count <= len(encoded) + 16384:
            raise ValueError
        return response_text(bytes(raw), expected_input_tokens=count, max_output_tokens=512)
    except RegularMailProviderError:
        raise
    except Exception:
        raise RegularMailProviderError("mail_openai_generation_unavailable") from None
