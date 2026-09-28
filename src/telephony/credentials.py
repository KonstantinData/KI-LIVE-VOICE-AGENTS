"""Per-user Windows Credential Manager storage for optional telephone access.

Generic credentials persist on this machine for the current Windows user.
No credential material is written to repository files or application logs.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
import re


class CredentialStoreError(RuntimeError):
    """Sanitized credential storage error safe to display to the operator."""


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(wintypes.BYTE)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


_MAX_BLOB_BYTES = 5 * 512
_MISSING = 1168
_REQUIRED_KEYS = {"username", "password", "api_key"}
_OPTIONAL_KEYS = {"crm_handoff_secret"}


def _target(tenant_id: str, agent_id: str) -> str:
    if any(not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,95}", value)
           for value in (tenant_id, agent_id)):
        raise CredentialStoreError("Telephone credential identifiers are invalid.")
    return f"KI-LIVE-VOICE-AGENTS/phone/{tenant_id}/{agent_id}"


def _api():
    if os.name != "nt":
        raise CredentialStoreError("Telephone credential storage requires Windows.")
    api = ctypes.WinDLL("advapi32", use_last_error=True)
    api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                             ctypes.POINTER(ctypes.POINTER(_Credential))]
    api.CredReadW.restype = wintypes.BOOL
    api.CredWriteW.argtypes = [ctypes.POINTER(_Credential), wintypes.DWORD]
    api.CredWriteW.restype = wintypes.BOOL
    api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    api.CredDeleteW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    api.CredFree.restype = None
    return api


def _validate(credentials: dict) -> None:
    keys = set(credentials) if isinstance(credentials, dict) else set()
    if (not isinstance(credentials, dict)
            or not _REQUIRED_KEYS.issubset(keys)
            or not keys.issubset(_REQUIRED_KEYS | _OPTIONAL_KEYS)
            or any(not isinstance(credentials[key], str) or not credentials[key]
                   or "\x00" in credentials[key] for key in _REQUIRED_KEYS)
            or any(not isinstance(credentials[key], str) or "\x00" in credentials[key]
                   for key in keys & _OPTIONAL_KEYS)):
        raise CredentialStoreError("Telephone credentials are incomplete or invalid.")


def load_credentials(tenant_id: str, agent_id: str) -> dict[str, str] | None:
    """Read this tenant/agent's current-user credential, or None if absent."""
    try:
        target = _target(tenant_id, agent_id)
        api = _api()
        pointer = ctypes.POINTER(_Credential)()
        if not api.CredReadW(target, 1, 0, ctypes.byref(pointer)):
            if ctypes.get_last_error() == _MISSING:
                return None
            raise CredentialStoreError("Telephone credentials could not be read.")
        try:
            credential = pointer.contents
            if not 0 < credential.CredentialBlobSize <= _MAX_BLOB_BYTES:
                raise CredentialStoreError("Stored telephone credentials are invalid.")
            blob = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
            result = json.loads(blob.decode("utf-8"))
            _validate(result)
            return result
        finally:
            api.CredFree(pointer)
    except CredentialStoreError:
        raise
    except Exception:
        raise CredentialStoreError("Telephone credentials could not be read.") from None


def save_credentials(tenant_id: str, agent_id: str, credentials: dict[str, str]) -> None:
    """Save credentials after the operator explicitly confirms local storage."""
    try:
        target = _target(tenant_id, agent_id)
        _validate(credentials)
        blob = json.dumps(credentials, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(blob) > _MAX_BLOB_BYTES:
            raise CredentialStoreError("Telephone credentials exceed the Windows storage limit.")
        api = _api()
        buffer = (wintypes.BYTE * len(blob)).from_buffer_copy(blob)
        credential = _Credential()
        credential.Type = 1  # CRED_TYPE_GENERIC
        credential.TargetName = target
        credential.UserName = credentials["username"]
        credential.CredentialBlobSize = len(blob)
        credential.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(wintypes.BYTE))
        credential.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE, scoped to current user
        try:
            if not api.CredWriteW(ctypes.byref(credential), 0):
                raise CredentialStoreError("Telephone credentials could not be saved.")
        finally:
            ctypes.memset(buffer, 0, len(blob))
    except CredentialStoreError:
        raise
    except Exception:
        raise CredentialStoreError("Telephone credentials could not be saved.") from None


def delete_credentials(tenant_id: str, agent_id: str) -> None:
    """Delete only the named credential; an absent credential is already removed."""
    try:
        target = _target(tenant_id, agent_id)
        api = _api()
        if not api.CredDeleteW(target, 1, 0) and ctypes.get_last_error() != _MISSING:
            raise CredentialStoreError("Telephone credentials could not be removed.")
    except CredentialStoreError:
        raise
    except Exception:
        raise CredentialStoreError("Telephone credentials could not be removed.") from None
