from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any, Callable

from app.services.process_ownership import kill_process_tree
from app.services.windows_process_job import WindowsProcessJob


class RuntimeCancelled(RuntimeError):
    pass


class RuntimeTimedOut(RuntimeError):
    pass


@dataclass(frozen=True)
class SubprocessResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class SubprocessRuntimeSpec:
    command: list[str]
    cwd: Path
    environment: dict[str, str]
    stdout_log: Path
    stderr_log: Path | None = None
    cancel_event: Event | None = None
    cancel_path: Path | None = None
    progress_path: Path | None = None
    progress_callback: Callable[..., None] | None = None
    timeout: float = 180.0
    poll_interval: float = 0.1
    cancel_grace: float = 1.0
    termination_grace: float = 1.0
    kill_grace: float = 1.0
    new_process_group: bool = False
    create_no_window: bool = False
    merge_stderr: bool = False
    on_started: Callable[[int], None] | None = None


def touch_cancel_marker(cancel_path: Path | None) -> None:
    if cancel_path is not None:
        cancel_path.touch(exist_ok=True)


def cancel_requested(
    cancel_event: Event | None, cancel_path: Path | None
) -> bool:
    return bool(
        (cancel_event is not None and cancel_event.is_set())
        or (cancel_path is not None and cancel_path.exists())
    )


def read_progress_if_changed(
    progress_path: Path | None,
    previous: str,
    progress_callback: Callable[..., None] | None,
) -> tuple[str, dict[str, object] | None]:
    """Return (previous_content, parsed_payload); unchanged files return None."""
    if progress_path is None or not progress_path.exists() or progress_callback is None:
        return previous, None
    try:
        rendered = progress_path.read_text(encoding="utf-8")
        if rendered == previous:
            return previous, None
        return rendered, json.loads(rendered)
    except (OSError, json.JSONDecodeError):
        return previous, None


def _stop_process_tree(
    process: subprocess.Popen[str],
    *,
    termination_grace: float,
    kill_grace: float,
) -> None:
    if termination_grace <= 0:
        kill_process_tree(process)
        try:
            process.wait(timeout=kill_grace)
        except subprocess.TimeoutExpired:
            pass
        return
    try:
        process.terminate()
    except OSError:
        pass
    try:
        process.wait(timeout=termination_grace)
        return
    except subprocess.TimeoutExpired:
        pass
    kill_process_tree(process)
    try:
        process.wait(timeout=kill_grace)
    except subprocess.TimeoutExpired:
        pass


def run_subprocess(spec: SubprocessRuntimeSpec) -> SubprocessResult:
    """Run one child process with unified cancel/timeout/progress/log handling."""
    creationflags = subprocess.CREATE_NO_WINDOW if spec.create_no_window else 0
    popen_options: dict[str, Any] = {
        "cwd": spec.cwd,
        "env": spec.environment,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if spec.merge_stderr:
        popen_options["stderr"] = subprocess.STDOUT
    else:
        popen_options["stderr"] = spec.stderr_log and spec.stderr_log.open("w", encoding="utf-8")
    if spec.new_process_group and os.name == "nt":
        popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    elif spec.new_process_group:
        popen_options["preexec_fn"] = os.setsid  # type: ignore[attr-defined]
    elif os.name == "nt":
        popen_options["creationflags"] = creationflags

    if os.name == "nt":
        popen_options["creationflags"] = int(popen_options.get("creationflags", 0)) | 0x00000004

    stderr_handle = popen_options.get("stderr")
    with spec.stdout_log.open("w", encoding="utf-8") as stdout_handle:
        popen_options["stdout"] = stdout_handle
        try:
            process = subprocess.Popen(spec.command, **popen_options)
        finally:
            if stderr_handle is not None and hasattr(stderr_handle, "close"):
                stderr_handle.close()

        process_job: WindowsProcessJob | None = None
        if os.name == "nt":
            try:
                process_job = WindowsProcessJob(process)
            except BaseException:
                process.kill()
                process.wait(timeout=2)
                raise

        if spec.on_started is not None:
            try:
                spec.on_started(process.pid)
            except Exception:
                pass

        started = time.monotonic()
        last_progress = ""
        try:
            while process.poll() is None:
                if cancel_requested(spec.cancel_event, spec.cancel_path):
                    touch_cancel_marker(spec.cancel_path)
                    if spec.cancel_grace <= 0:
                        _stop_process_tree(
                            process,
                            termination_grace=spec.termination_grace,
                            kill_grace=spec.kill_grace,
                        )
                    else:
                        try:
                            process.wait(timeout=spec.cancel_grace)
                        except subprocess.TimeoutExpired:
                            _stop_process_tree(
                                process,
                                termination_grace=spec.termination_grace,
                                kill_grace=spec.kill_grace,
                            )
                    raise RuntimeCancelled("子进程已取消")
                if time.monotonic() - started >= spec.timeout:
                    _stop_process_tree(
                        process,
                        termination_grace=spec.termination_grace,
                        kill_grace=spec.kill_grace,
                    )
                    raise RuntimeTimedOut("子进程超过运行时限")
                last_progress, payload = read_progress_if_changed(
                    spec.progress_path,
                    last_progress,
                    spec.progress_callback,
                )
                if payload is not None and spec.progress_callback is not None:
                    spec.progress_callback(payload)
                time.sleep(spec.poll_interval)
        except BaseException:
            if process.poll() is None:
                _stop_process_tree(
                    process,
                    termination_grace=spec.termination_grace,
                    kill_grace=spec.kill_grace,
                )
            raise
        finally:
            if process_job is not None:
                process_job.close()

    stdout = spec.stdout_log.read_text(encoding="utf-8", errors="replace")
    stderr = (
        ""
        if spec.merge_stderr or spec.stderr_log is None
        else spec.stderr_log.read_text(encoding="utf-8", errors="replace")
    )
    if cancel_requested(spec.cancel_event, spec.cancel_path):
        raise RuntimeCancelled("子进程已取消")
    return SubprocessResult(returncode=int(process.returncode or 0), stdout=stdout, stderr=stderr)
