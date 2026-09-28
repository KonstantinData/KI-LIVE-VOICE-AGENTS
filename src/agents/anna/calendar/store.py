"""Encrypted durable ANNA operations and cross-process calendar serialization."""

import asyncio
import json
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from cryptography.fernet import Fernet


class CalendarStore:
    def __init__(self, directory: Path, key: str):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "anna-calendar.sqlite3"
        self.lock_path = directory / "anna-calendar.lock"
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, value BLOB, PRIMARY KEY(kind,id))")
        if os.name != "nt":
            os.chmod(self.path, 0o600)

    def _put(self, kind, key, value):
        encrypted = self.cipher.encrypt(json.dumps(value).encode())
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO records VALUES (?,?,?)", (kind, key, encrypted))

    async def put(self, kind, key, value):
        await asyncio.to_thread(self._put, kind, key, value)

    def _read(self, kind, key):
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT id,value FROM records WHERE kind=?" + (" AND id=?" if key is not None else ""), (kind, key) if key is not None else (kind,)).fetchall()
        values = [(row[0], json.loads(self.cipher.decrypt(row[1]))) for row in rows]
        return values if key is None else (values[0][1] if values else None)

    async def get(self, kind, key):
        return await asyncio.to_thread(self._read, kind, key)

    async def all(self, kind):
        return await asyncio.to_thread(self._read, kind, None)

    def _acquire(self):
        handle = open(self.lock_path, "a+b")
        handle.seek(0)
        handle.write(b"0")
        handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        return handle

    @asynccontextmanager
    async def locked(self):
        # The worker, never the event loop, waits for the process-wide lock.
        task = asyncio.create_task(asyncio.to_thread(self._acquire))
        try:
            handle = await asyncio.shield(task)
        except asyncio.CancelledError:
            handle = await task
            handle.close()
            raise
        try:
            yield
        finally:
            handle.close()
