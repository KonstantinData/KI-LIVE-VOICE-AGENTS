"""Scoped Windows timer resolution and drift-resistant telephone frame timing."""

from __future__ import annotations

import asyncio
import ctypes
import math
import sys
import time
from typing import Awaitable, Callable


class WindowsAudioTimer:
    """Balance a successful one-millisecond timer request once per instance.

    Timer resolution is a best-effort latency improvement, not an audio clock
    guarantee. Unsupported platforms and unavailable native APIs remain usable.
    """

    def __init__(self) -> None:
        self._api = None
        self._acquired = False

    def acquire(self) -> None:
        if self._acquired or sys.platform != "win32":
            return
        try:
            api = ctypes.WinDLL("winmm", use_last_error=True)
            for name in ("timeBeginPeriod", "timeEndPeriod"):
                function = getattr(api, name)
                function.argtypes = [ctypes.c_uint]
                function.restype = ctypes.c_uint
            if api.timeBeginPeriod(1) == 0:
                self._api = api
                self._acquired = True
        except (AttributeError, OSError):
            pass

    def release(self) -> None:
        if not self._acquired:
            return
        api = self._api
        self._acquired = False
        self._api = None
        try:
            api.timeEndPeriod(1)
        except (AttributeError, OSError):
            pass


class FrameClock:
    """Wait between frames using absolute monotonic deadlines.

    Construct immediately before the first frame, then await ``wait`` after
    processing each frame. Small work costs do not accumulate. If processing
    misses a whole period, skip expired deadlines rather than replaying a burst
    of historical frames. Clock and sleep injection are for deterministic tests.
    """

    def __init__(
        self,
        period: float = 0.02,
        *,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        if not math.isfinite(period) or period <= 0:
            raise ValueError("Frame period must be finite and positive.")
        self._clock = clock if clock is not None else time.perf_counter
        self._sleep = sleep if sleep is not None else asyncio.sleep
        self._period = period
        self._deadline = self._clock() + period

    async def wait(self) -> None:
        now = self._clock()
        if now >= self._deadline + self._period:
            missed = math.floor((now - self._deadline) / self._period)
            self._deadline += missed * self._period
        if now >= self._deadline:
            await self._sleep(0)
        else:
            # Windows event-loop timers may wake before a high-resolution
            # deadline. Recheck without busy-spinning or accumulating drift.
            while now < self._deadline:
                await self._sleep(max(0.001, self._deadline - now))
                now = self._clock()
        self._deadline += self._period
