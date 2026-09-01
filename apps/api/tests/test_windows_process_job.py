from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

import pytest

from app.services.windows_process_job import WindowsProcessJob

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows Job Object lifecycle")


def test_owned_job_stops_children_without_touching_other_processes(tmp_path):
    child_pid_path = tmp_path / "child.pid"
    child_code = "import time; time.sleep(30)"
    parent_code = (
        "import subprocess,sys,time,pathlib; "
        f"p=subprocess.Popen([sys.executable,'-c',{child_code!r}]); "
        f"pathlib.Path({str(child_pid_path)!r}).write_text(str(p.pid)); "
        "time.sleep(30)"
    )
    unrelated = subprocess.Popen([sys.executable, "-c", child_code], creationflags=subprocess.CREATE_NO_WINDOW)
    parent = subprocess.Popen([sys.executable, "-c", parent_code], text=True, creationflags=subprocess.CREATE_NO_WINDOW | 0x00000004)
    job = WindowsProcessJob(parent)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    child_handle = None
    try:
        deadline = time.monotonic() + 5
        while not child_pid_path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        child_handle = kernel.OpenProcess(0x00100000, False, int(child_pid_path.read_text()))
        assert child_handle
        assert kernel.WaitForSingleObject(child_handle, 0) == 0x102
        started = time.monotonic()
        job.close()
        parent.wait(timeout=1)
        assert kernel.WaitForSingleObject(child_handle, 1000) == 0
        assert time.monotonic() - started < 2.5
        assert unrelated.poll() is None
        job.close()  # idempotent, no reused-PID fallback
    finally:
        job.close()
        if parent.poll() is None:
            parent.kill()
        parent.wait(timeout=2)
        unrelated.kill()
        unrelated.wait(timeout=2)
        if child_handle:
            kernel.CloseHandle(child_handle)
