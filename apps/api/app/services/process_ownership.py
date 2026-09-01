from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from app.settings import Settings


def get_process_commandline(pid: int) -> str | None:
    """Best-effort command line of a process, or None when it cannot be read."""
    if os.name == "nt":
        query = (
            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}').CommandLine"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", query],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            return None
        value = result.stdout.strip()
        return value or None
    try:
        result = subprocess.run(
            ["ps", "-o", "command=", "-p", str(int(pid))],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    value = result.stdout.strip()
    return value or None


def is_process_owned_by_runtime(
    pid: int,
    settings: Settings,
    *,
    commandline_reader: Callable[[int], str | None] = get_process_commandline,
) -> bool:
    """Whether the PID belongs to this project's R runtime before killing it.

    Restart recovery must not blindly taskkill a persisted PID: Windows can
    reuse PIDs, and a tampered state file could name an unrelated process.
    """
    commandline = commandline_reader(pid)
    if not commandline:
        return False
    return str(settings.rscript_path).casefold() in commandline.casefold()


def kill_process_tree(target: object) -> None:
    """Kill a process and its child processes cleanly across platforms."""
    if isinstance(target, int):
        pid = target
        killable = False
    else:
        pid = cast(int, target.pid)  # type: ignore[attr-defined]
        killable = True
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True
            )
        else:
            import signal

            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception:
        if killable and hasattr(target, "kill"):
            try:
                cast(Any, target).kill()
            except Exception:
                pass
