"""Credential Manager contract tests with a fake native API; no real writes."""

import ctypes

import pytest

from src.telephony import credentials as store


TENANT = "mein-kuechenexperte"
AGENT = "anna-phone-assistant"
DATA = {"username": "test-user", "password": "test-password", "api_key": "test-key"}


class Native:
    def __init__(self):
        self.blobs = {}
        self.freed = 0
        self.last_error = 0
        self.references = []

    def CredWriteW(self, pointer, flags):
        credential = ctypes.cast(pointer, ctypes.POINTER(store._Credential)).contents
        assert flags == 0 and credential.Type == 1 and credential.Persist == 2
        self.blobs[credential.TargetName] = ctypes.string_at(
            credential.CredentialBlob, credential.CredentialBlobSize,
        )
        return True

    def CredReadW(self, target, kind, flags, result):
        assert kind == 1 and flags == 0
        if target not in self.blobs:
            self.last_error = 1168
            return False
        blob = self.blobs[target]
        buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        credential = store._Credential()
        credential.CredentialBlobSize = len(blob)
        credential.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(store.wintypes.BYTE))
        self.references.extend([buffer, credential])
        ctypes.cast(result, ctypes.POINTER(ctypes.POINTER(store._Credential)))[0] = ctypes.pointer(credential)
        return True

    def CredFree(self, pointer):
        self.freed += 1

    def CredDeleteW(self, target, kind, flags):
        assert kind == 1 and flags == 0
        if target not in self.blobs:
            self.last_error = 1168
            return False
        del self.blobs[target]
        return True


@pytest.fixture
def native(monkeypatch):
    fake = Native()
    monkeypatch.setattr(store, "_api", lambda: fake)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: fake.last_error, raising=False)
    return fake


def test_roundtrip_and_delete_are_tenant_scoped(native):
    store.save_credentials(TENANT, AGENT, DATA)
    assert list(native.blobs) == ["KI-LIVE-VOICE-AGENTS/phone/mein-kuechenexperte/anna-phone-assistant"]
    assert store.load_credentials(TENANT, AGENT) == DATA
    assert native.freed == 1
    assert store.load_credentials("other-tenant", AGENT) is None
    store.delete_credentials(TENANT, AGENT)
    assert store.load_credentials(TENANT, AGENT) is None
    store.delete_credentials(TENANT, AGENT)


def test_unicode_credentials_roundtrip(native):
    data = dict(DATA, password="test-äöü-密碼")
    store.save_credentials(TENANT, AGENT, data)
    assert store.load_credentials(TENANT, AGENT) == data


@pytest.mark.parametrize("identifier", ["../other", "UPPER", "", "anna/other", "a" * 97])
def test_invalid_identifiers_never_touch_store(native, identifier):
    with pytest.raises(store.CredentialStoreError):
        store.save_credentials(TENANT, identifier, DATA)
    assert not native.blobs


@pytest.mark.parametrize("data", [{}, dict(DATA, password=""), dict(DATA, extra="secret"),
                                   dict(DATA, password="a" * 3000)])
def test_invalid_or_oversized_credentials_are_rejected(native, data):
    with pytest.raises(store.CredentialStoreError):
        store.save_credentials(TENANT, AGENT, data)
    assert not native.blobs


def test_malformed_stored_data_is_freed_without_leaking(native):
    native.blobs[store._target(TENANT, AGENT)] = b"private invalid json"
    with pytest.raises(store.CredentialStoreError) as error:
        store.load_credentials(TENANT, AGENT)
    assert "private" not in str(error.value)
    assert native.freed == 1


def test_native_failures_are_sanitized(native, monkeypatch):
    def fail(*args):
        raise RuntimeError("private native payload")

    monkeypatch.setattr(native, "CredWriteW", fail)
    with pytest.raises(store.CredentialStoreError) as error:
        store.save_credentials(TENANT, AGENT, DATA)
    assert "private" not in str(error.value)


def test_access_denied_is_not_treated_as_missing(native, monkeypatch):
    native.last_error = 5
    monkeypatch.setattr(native, "CredReadW", lambda *args: False)
    with pytest.raises(store.CredentialStoreError, match="could not be read"):
        store.load_credentials(TENANT, AGENT)
    monkeypatch.setattr(native, "CredDeleteW", lambda *args: False)
    with pytest.raises(store.CredentialStoreError, match="could not be removed"):
        store.delete_credentials(TENANT, AGENT)
