"""Synthetic clock/native API tests; no real timer resolution changes."""

from types import SimpleNamespace

import pytest

from src.telephony import timing


class Time:
    def __init__(self):
        self.now = 0.0
        self.delays = []

    def clock(self):
        return self.now

    async def sleep(self, delay):
        self.delays.append(delay)
        self.now += delay


@pytest.mark.asyncio
async def test_frame_clock_subtracts_work_without_cumulative_drift():
    time = Time()
    clock = timing.FrameClock(clock=time.clock, sleep=time.sleep)
    for _ in range(100):
        time.now += 0.003
        await clock.wait()
    assert time.now == pytest.approx(2.0)
    assert time.delays == pytest.approx([0.017] * 100)


@pytest.mark.asyncio
async def test_frame_clock_skips_long_stall_without_catchup_burst():
    time = Time()
    clock = timing.FrameClock(clock=time.clock, sleep=time.sleep)
    time.now = 3.005
    await clock.wait()
    await clock.wait()
    await clock.wait()
    assert time.delays[0] == 0
    assert time.delays[1] == pytest.approx(0.015)
    assert time.delays[2] == pytest.approx(0.02)


@pytest.mark.asyncio
async def test_frame_clock_compensates_small_scheduler_overshoot():
    time = Time()
    clock = timing.FrameClock(clock=time.clock, sleep=time.sleep)
    await clock.wait()
    time.now += 0.006
    await clock.wait()
    assert time.now == pytest.approx(0.04)


@pytest.mark.asyncio
async def test_frame_clock_rechecks_early_timer_wakeup():
    time = Time()

    async def early_sleep(delay):
        time.delays.append(delay)
        time.now += delay / 2 if len(time.delays) == 1 else delay

    clock = timing.FrameClock(clock=time.clock, sleep=early_sleep)
    await clock.wait()
    assert time.now == pytest.approx(0.02)
    assert time.delays == pytest.approx([0.02, 0.01])


@pytest.mark.parametrize("period", [0, -1, float("inf"), float("nan")])
def test_invalid_period_rejected(period):
    with pytest.raises(ValueError):
        timing.FrameClock(period, clock=lambda: 0)


class NativeFunction:
    def __init__(self, result=0):
        self.calls = []
        self.result = result

    def __call__(self, value):
        self.calls.append(value)
        return self.result


@pytest.fixture
def native(monkeypatch):
    api = SimpleNamespace(timeBeginPeriod=NativeFunction(), timeEndPeriod=NativeFunction())
    monkeypatch.setattr(timing.sys, "platform", "win32")
    monkeypatch.setattr(timing.ctypes, "WinDLL", lambda *args, **kwargs: api, raising=False)
    return api


def test_timer_balances_success_and_is_idempotent(native):
    timer = timing.WindowsAudioTimer()
    timer.acquire()
    timer.acquire()
    timer.release()
    timer.release()
    assert native.timeBeginPeriod.calls == [1]
    assert native.timeEndPeriod.calls == [1]


def test_failed_timer_request_is_not_released(native):
    native.timeBeginPeriod.result = 1
    timer = timing.WindowsAudioTimer()
    timer.acquire()
    timer.release()
    assert native.timeBeginPeriod.calls == [1]
    assert native.timeEndPeriod.calls == []


def test_timer_noop_on_other_platform(native, monkeypatch):
    monkeypatch.setattr(timing.sys, "platform", "linux")
    timer = timing.WindowsAudioTimer()
    timer.acquire()
    timer.release()
    assert native.timeBeginPeriod.calls == []
    assert native.timeEndPeriod.calls == []


def test_timer_native_load_unavailable_is_nonfatal(native, monkeypatch):
    def missing(*args, **kwargs):
        raise OSError("API unavailable")

    monkeypatch.setattr(timing.ctypes, "WinDLL", missing)
    timer = timing.WindowsAudioTimer()
    timer.acquire()
    timer.release()
