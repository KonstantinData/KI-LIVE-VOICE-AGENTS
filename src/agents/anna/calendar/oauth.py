"""Authorization code + PKCE with encrypted, transactional token rotation."""

import asyncio
import base64
import hashlib
import json
import logging
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken

from .config import MASTER_CALENDAR, CalendarConfig, CalendarError

SCOPES = "offline_access User.Read Calendars.ReadWrite"
LOGGER = logging.getLogger("anna.calendar")


class OAuthManager:
    def __init__(self, config: CalendarConfig, http: httpx.AsyncClient | None = None):
        self.config = config
        self.http = http

    def _cipher(self) -> Fernet:
        self.config.validate()
        try:
            return Fernet(self.config.encryption_key.encode())
        except (ValueError, TypeError):
            raise CalendarError("calendar_invalid_encryption_key") from None

    def _connection(self):
        self._cipher()
        self.config.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.config.data_dir, 0o700)
        path = self.config.data_dir / "oauth.sqlite3"
        conn = sqlite3.connect(path, timeout=0, isolation_level=None)
        os.chmod(path, 0o600)
        conn.execute("CREATE TABLE IF NOT EXISTS vault (key TEXT PRIMARY KEY, value BLOB NOT NULL)")
        return conn

    @asynccontextmanager
    async def _transaction(self):
        # A database write transaction coordinates all workers, not just this loop.
        deadline = time.monotonic() + 45
        conn = None
        while True:
            try:
                conn = self._connection()
                conn.execute("BEGIN IMMEDIATE")
                break
            except sqlite3.OperationalError:
                if conn:
                    conn.close()
                if time.monotonic() >= deadline:
                    raise CalendarError("oauth_busy") from None
                await asyncio.sleep(0.05)
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _read(self, conn, key):
        row = conn.execute("SELECT value FROM vault WHERE key=?", (key,)).fetchone()
        if not row:
            return None
        try:
            return json.loads(self._cipher().decrypt(row[0]))
        except (InvalidToken, ValueError, TypeError):
            raise CalendarError("oauth_storage_invalid") from None

    def _write(self, conn, key, value):
        encrypted = self._cipher().encrypt(json.dumps(value).encode())
        conn.execute("INSERT OR REPLACE INTO vault VALUES (?,?)", (key, encrypted))

    def _binding(self) -> dict:
        # Only tokens issued through this explicit business tenant may be reused.
        return {
            "authority_tenant": (self.config.authority_tenant or self.config.tenant_id).casefold(),
            "client_id": self.config.client_id,
            "calendar_user": self.config.calendar_user.casefold(),
        }

    def _bound(self, value) -> bool:
        return isinstance(value, dict) and value.get("binding") == self._binding()

    async def _request(self, method, url, **kwargs):
        try:
            if self.http is not None:
                response = await self.http.request(method, url, follow_redirects=False, **kwargs)
            else:
                async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
                    response = await client.request(method, url, **kwargs)
            if not 200 <= response.status_code < 300:
                provider_error = "unknown"
                try:
                    provider_error = str(response.json().get("error", "unknown"))[:80]
                except (ValueError, AttributeError):
                    pass
                LOGGER.warning("oauth_provider_rejected status=%s error=%s", response.status_code, provider_error)
                raise CalendarError("oauth_provider_rejected")
            data = response.json()
            if not isinstance(data, dict):
                raise CalendarError("oauth_response_invalid")
            return data
        except (httpx.HTTPError, ValueError):
            raise CalendarError("oauth_provider_unavailable") from None

    async def start(self, browser_nonce: str) -> str:
        self._cipher()
        if not browser_nonce or len(browser_nonce) < 32:
            raise CalendarError("oauth_browser_binding_required")
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        async with self._transaction() as conn:
            # Single pending authorization keeps stale states and storage bounded.
            self._write(conn, "pending", {
                "state": state, "verifier": verifier, "nonce": browser_nonce,
                "expires_at": time.time() + 600,
                "binding": self._binding(),
            })
        return self._endpoint("authorize") + "?" + urlencode({
            "client_id": self.config.client_id, "response_type": "code",
            "redirect_uri": self.config.redirect_uri, "response_mode": "query",
            "scope": SCOPES, "state": state, "code_challenge": challenge,
            "code_challenge_method": "S256", "login_hint": MASTER_CALENDAR,
            "prompt": "select_account",
        })

    def _endpoint(self, kind):
        authority_tenant = self.config.authority_tenant or self.config.tenant_id
        return f"https://login.microsoftonline.com/{authority_tenant}/oauth2/v2.0/{kind}"

    async def _token(self, **grant):
        result = await self._request("POST", self._endpoint("token"), data={
            "client_id": self.config.client_id, "client_secret": self.config.client_secret,
            "scope": SCOPES, **grant,
        })
        if not isinstance(result.get("access_token"), str) or not result["access_token"]:
            raise CalendarError("oauth_response_invalid")
        granted = set(str(result.get("scope", "")).lower().split())
        if not {"calendars.readwrite", "user.read"}.issubset(granted):
            raise CalendarError("oauth_scope_missing")
        try:
            lifetime = int(result["expires_in"])
            if lifetime <= 60:
                raise ValueError
        except (KeyError, ValueError, TypeError):
            raise CalendarError("oauth_response_invalid") from None
        return {"access_token": result["access_token"],
                "refresh_token": result.get("refresh_token"),
                "expires_at": time.time() + lifetime}

    async def _verify_identity(self, token):
        identity = await self._request("GET", "https://graph.microsoft.com/v1.0/me",
            params={"$select": "id,mail,userPrincipalName"},
            headers={"Authorization": f"Bearer {token}"})
        # A guest can have the same mail address but a different tenant principal.
        principal = str(identity.get("userPrincipalName") or "").casefold()
        if principal != self.config.calendar_user.casefold() or not identity.get("id"):
            raise CalendarError("oauth_wrong_calendar_account")
        return identity["id"]

    async def finish(self, code: str, state: str, browser_nonce: str) -> None:
        # Consume before redemption, even when the provider fails; never replay a code.
        async with self._transaction() as conn:
            pending = self._read(conn, "pending")
            if (not self._bound(pending) or pending["expires_at"] < time.time()
                or not secrets.compare_digest(pending["state"].encode(), state.encode())
                or not secrets.compare_digest(pending["nonce"].encode(), browser_nonce.encode())):
                raise CalendarError("oauth_state_invalid")
            conn.execute("DELETE FROM vault WHERE key='pending'")
        async with self._transaction() as conn:
            tokens = await self._token(grant_type="authorization_code", code=code,
                redirect_uri=self.config.redirect_uri, code_verifier=pending["verifier"])
            if not tokens.get("refresh_token"):
                raise CalendarError("oauth_refresh_token_missing")
            tokens["account_id"] = await self._verify_identity(tokens["access_token"])
            tokens["binding"] = self._binding()
            self._write(conn, "tokens", tokens)

    async def access_token(self) -> str:
        async with self._transaction() as conn:
            tokens = self._read(conn, "tokens")
            if not self._bound(tokens) or not tokens.get("account_id"):
                raise CalendarError("oauth_login_required")
            if tokens["expires_at"] <= time.time() + 120:
                updated = await self._token(grant_type="refresh_token",
                                            refresh_token=tokens["refresh_token"])
                account_id = await self._verify_identity(updated["access_token"])
                if account_id != tokens["account_id"]:
                    raise CalendarError("oauth_wrong_calendar_account")
                updated["account_id"] = account_id
                updated["binding"] = tokens["binding"]
                updated["refresh_token"] = updated.get("refresh_token") or tokens["refresh_token"]
                self._write(conn, "tokens", updated)
                tokens = updated
            return tokens["access_token"]

    def status(self) -> dict:
        try:
            self._cipher()
            path = self.config.data_dir / "oauth.sqlite3"
            if not path.exists():
                return {"connected": False, "mode": self.config.mode}
            conn = sqlite3.connect(path, timeout=0)
            try:
                tokens = self._read(conn, "tokens")
                connected = self._bound(tokens) and bool(tokens.get("account_id"))
            finally:
                conn.close()
            return {"connected": connected, "mode": self.config.mode}
        except (CalendarError, sqlite3.Error, OSError):
            return {"connected": False, "mode": self.config.mode}
