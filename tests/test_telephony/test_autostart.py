"""Supervisor contracts without starting processes or modifying the registry."""

from contextlib import nullcontext
import subprocess
import sys
from types import SimpleNamespace

import pytest

from src.telephony import autostart


class MemoryPath:
    def __init__(self, name="state", entries=None):
        self.name = name
        self.entries = entries if entries is not None else set()

    def __truediv__(self, suffix):
        return MemoryPath(f"{self.name}/{suffix}", self.entries)

    def __str__(self):
        return self.name

    def exists(self):
        return self.name in self.entries

    def unlink(self, missing_ok=False):
        self.entries.discard(self.name)

    def touch(self):
        self.entries.add(self.name)

    def mkdir(self, **kwargs):
        pass


class Child:
    def __init__(self, code=None):
        self.returncode = code
        self.terminated = False
        self.waits = []

    def poll(self):
        return self.returncode

    def wait(self, timeout):
        self.waits.append(timeout)
        self.returncode = 0

    def terminate(self):
        self.terminated = True


@pytest.fixture
def worker(monkeypatch):
    directory = MemoryPath()
    states, launches = [], []
    child = Child(2)
    monkeypatch.setattr(autostart, "state_directory", lambda: directory)
    monkeypatch.setattr(autostart, "instance_lock", lambda: nullcontext(True))
    monkeypatch.setattr(autostart, "load_credentials", lambda *args: {"configured": True})
    monkeypatch.setattr(autostart, "write_status", lambda path, state: states.append(state))
    monkeypatch.setattr(autostart, "microsip_running", lambda: False)
    monkeypatch.setattr(autostart.time, "sleep", lambda seconds: None)

    def launch(*args, **kwargs):
        launches.append((args, kwargs))
        return child

    monkeypatch.setattr(autostart.subprocess, "Popen", launch)
    return SimpleNamespace(directory=directory, states=states, launches=launches, child=child)


def test_duplicate_supervisor_does_not_start_child(worker, monkeypatch):
    monkeypatch.setattr(autostart, "instance_lock", lambda: nullcontext(False))
    assert autostart.supervise() == 0
    assert worker.launches == []


def test_stop_requested_before_worker_runs_is_preserved(worker):
    (worker.directory / "stop").touch()
    assert autostart.supervise() == 0
    assert worker.launches == []
    assert worker.states[-1] == "stopped"


def test_every_child_is_bound_to_supervisor_lifetime(worker):
    autostart.supervise()
    args, _ = worker.launches[0]
    assert "--parent-pid" in args[0]


def test_malformed_status_types_are_not_displayed(monkeypatch):
    from src.telephony.runtime_status import read_status

    path = SimpleNamespace(read_text=lambda **kw: '{"state":[],"pid":1,"updated_at":"now"}')
    assert read_status(path) == {"state": "unknown"}


def test_missing_credentials_require_setup_without_child(worker, monkeypatch):
    monkeypatch.setattr(autostart, "load_credentials", lambda *args: None)
    assert autostart.supervise() == 2
    assert worker.states == ["setup_required"]
    assert worker.launches == []


def test_permanent_child_failure_does_not_retry(worker):
    assert autostart.supervise() == 2
    assert len(worker.launches) == 1
    args, kwargs = worker.launches[0]
    assert "--non-interactive" in args[0]
    assert "--status-file" in args[0] and "--stop-file" in args[0]
    assert kwargs["stdin"] == subprocess.DEVNULL


def test_transient_child_failure_retries_then_stop(worker, monkeypatch):
    worker.child.returncode = 1
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        if len(worker.launches) == 2:
            (worker.directory / "stop").touch()

    monkeypatch.setattr(autostart.time, "sleep", sleep)
    assert autostart.supervise() == 0
    assert len(worker.launches) == 2
    assert "retrying" in worker.states
    assert worker.states[-1] == "stopped"


def test_running_child_gets_graceful_stop(worker, monkeypatch):
    worker.child.returncode = None
    monkeypatch.setattr(autostart.time, "sleep", lambda seconds: (worker.directory / "stop").touch())
    assert autostart.supervise() == 0
    assert worker.child.waits == [15]
    assert not worker.child.terminated
    assert worker.states[-1] == "stopped"


def test_microsip_blocks_launch_without_terminating_it(worker, monkeypatch):
    monkeypatch.setattr(autostart, "microsip_running", lambda: True)
    monkeypatch.setattr(autostart.time, "sleep", lambda seconds: (worker.directory / "stop").touch())
    assert autostart.supervise() == 0
    assert worker.launches == []
    assert worker.states == ["microsip_running", "stopped"]


def test_registry_install_and_remove_are_current_user_and_named(monkeypatch):
    writes, deletes = [], []
    fake = SimpleNamespace(
        HKEY_CURRENT_USER="current-user", REG_SZ=1, KEY_SET_VALUE=2,
        CreateKey=lambda hive, path: nullcontext((hive, path)),
        OpenKey=lambda hive, path, *args: nullcontext((hive, path)),
        SetValueEx=lambda *args: writes.append(args),
        DeleteValue=lambda *args: deletes.append(args),
    )
    monkeypatch.setitem(sys.modules, "winreg", fake)
    command = [r"C:\Program Files\repo\pythonw.exe", "background.py", "--worker"]
    monkeypatch.setattr(autostart, "startup_command", lambda: command)
    autostart.install_autostart()
    assert writes == [(("current-user", autostart.RUN_KEY), autostart.RUN_NAME,
                       0, 1, subprocess.list2cmdline(command))]
    autostart.remove_autostart()
    assert deletes == [(("current-user", autostart.RUN_KEY), autostart.RUN_NAME)]


def test_declined_setup_does_not_store_or_install(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "nein")

    def forbidden(*args):
        pytest.fail("Declined setup must not write credentials or autostart")

    monkeypatch.setattr(autostart, "save_credentials", forbidden)
    monkeypatch.setattr(autostart, "install_autostart", forbidden)
    assert autostart.configure() == 1
