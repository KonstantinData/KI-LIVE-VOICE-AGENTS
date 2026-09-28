"""Make an unattended phone child exit if its Windows supervisor disappears."""

import ctypes
from ctypes import wintypes
import os
import sys
from threading import Thread


def watch_parent(parent_pid: int) -> None:
    """Hold a process handle so PID reuse cannot keep an orphan alive."""
    if sys.platform != "win32" or parent_pid <= 0:
        raise ValueError("A Windows supervisor process is required")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x00100000, False, parent_pid)  # SYNCHRONIZE
    if not handle:
        raise RuntimeError("Supervisor process is unavailable")

    def wait() -> None:
        kernel.WaitForSingleObject(handle, 0xFFFFFFFF)
        kernel.CloseHandle(handle)
        # The supervisor is gone; close all SIP/RTP sockets with the process.
        # No stack traces or sensitive provider state can escape on this path.
        os._exit(1)

    Thread(target=wait, name="Anna supervisor watcher", daemon=True).start()
