"""A managed telephone worker cannot survive its supervisor process handle."""

from types import SimpleNamespace

import pytest

from src.telephony import parent_watch


class Function:
    def __init__(self, action):
        self.action = action

    def __call__(self, *args):
        return self.action(*args)


def test_parent_exit_closes_handle_and_terminates_child(monkeypatch):
    events, targets = [], []
    api = SimpleNamespace(
        OpenProcess=Function(lambda access, inherit, pid: 42),
        WaitForSingleObject=Function(lambda handle, timeout: events.append("parent-exited")),
        CloseHandle=Function(lambda handle: events.append(("closed", handle))),
    )
    monkeypatch.setattr(parent_watch.sys, "platform", "win32")
    monkeypatch.setattr(parent_watch.ctypes, "WinDLL", lambda *a, **kw: api, raising=False)
    monkeypatch.setattr(parent_watch, "Thread", lambda **kw: SimpleNamespace(
        start=lambda: targets.append(kw["target"])))
    monkeypatch.setattr(parent_watch.os, "_exit", lambda code: events.append(("exit", code)))
    parent_watch.watch_parent(100)
    assert events == []
    targets[0]()
    assert events == ["parent-exited", ("closed", 42), ("exit", 1)]


def test_missing_parent_refuses_managed_start(monkeypatch):
    api = SimpleNamespace(OpenProcess=Function(lambda *a: None),
                          WaitForSingleObject=Function(lambda *a: None),
                          CloseHandle=Function(lambda *a: None))
    monkeypatch.setattr(parent_watch.sys, "platform", "win32")
    monkeypatch.setattr(parent_watch.ctypes, "WinDLL", lambda *a, **kw: api, raising=False)
    with pytest.raises(RuntimeError):
        parent_watch.watch_parent(100)
