"""Shared lifetime HTTP quota for manual Olivia synthetic acceptance and mail pilot."""
from __future__ import annotations

import os
import sqlite3
import stat
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from src.api.services.liquisto_mail import _protected_path, _protected_stat

MAX_HTTP_ATTEMPTS = 5
BUDGET_MICRO_USD = 100_000
RESERVATION_MICRO_USD = 10_000


class OpenAIBudgetError(Exception):
    """Fixed, non-sensitive reason for denied or unavailable budget authority."""


@dataclass(frozen=True)
class OpenAIHttpBudget:
    path: Path

    def _connect(self):
        _protected_path(self.path)
        _protected_path(self.path.parent)
        if not self.path.exists():
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(fd)
            except FileExistsError:
                pass
        info = self.path.stat()
        _protected_stat(info)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("regular ledger required")
        db = sqlite3.connect(self.path, timeout=15)
        db.execute("PRAGMA synchronous=FULL")
        return db

    def reserve(self, purpose: str):
        """Consume BEFORE every HTTP attempt, including token count and all failures."""
        try:
            if purpose not in {"count", "generate"}:
                raise ValueError
            with closing(self._connect()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("CREATE TABLE IF NOT EXISTS openai_http_attempts "
                           "(id INTEGER PRIMARY KEY, purpose TEXT NOT NULL, reservation_micro_usd INTEGER NOT NULL)")
                count, total = db.execute("SELECT COUNT(*),COALESCE(SUM(reservation_micro_usd),0) "
                                         "FROM openai_http_attempts").fetchone()
                if count >= MAX_HTTP_ATTEMPTS or total + RESERVATION_MICRO_USD > BUDGET_MICRO_USD:
                    raise ValueError
                db.execute("INSERT INTO openai_http_attempts(purpose,reservation_micro_usd) VALUES (?,?)",
                           (purpose, RESERVATION_MICRO_USD))
        except Exception:
            raise OpenAIBudgetError("olivia_openai_budget_denied") from None

    def claim_batch(self, batch_id: str, payload_sha256: str):
        """No resume/regeneration of an uncertain batch, even after process restart."""
        try:
            with closing(self._connect()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("CREATE TABLE IF NOT EXISTS openai_synthetic_batches "
                           "(batch_id TEXT PRIMARY KEY, payload_sha256 TEXT NOT NULL)")
                db.execute("INSERT INTO openai_synthetic_batches VALUES (?,?)", (batch_id, payload_sha256))
        except Exception:
            raise OpenAIBudgetError("olivia_openai_batch_already_claimed_or_unavailable") from None

    def attempts(self) -> int:
        try:
            with closing(self._connect()) as db:
                exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                    "AND name='openai_http_attempts'").fetchone()
                return db.execute("SELECT COUNT(*) FROM openai_http_attempts").fetchone()[0] if exists else 0
        except Exception:
            raise OpenAIBudgetError("olivia_openai_budget_unavailable") from None
