from __future__ import annotations

import atexit
import json
import logging
import os
import queue
import subprocess
import threading
import time
import uuid
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from app.services.subprocess_runtime import (
    read_progress_if_changed,
    touch_cancel_marker,
)
from app.services.windows_process_job import WindowsProcessJob
from app.settings import Settings

logger = logging.getLogger("researchpath")


class RWorkerError(RuntimeError):
    pass


class RWorkerUnavailable(RWorkerError):
    pass


class RWorkerTaskError(RWorkerError):
    pass


class RWorkerCancelled(RWorkerError):
    pass


class _RWorkerProcess:
    def __init__(
        self,
        settings: Settings,
        ordinal: int,
        cancel_event: threading.Event | None = None,
    ) -> None:
        self.settings = settings
        self.ordinal = ordinal
        self.responses: queue.Queue[dict[str, Any]] = queue.Queue()
        self.ready = threading.Event()
        self.stderr_tail: deque[str] = deque(maxlen=40)
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        environment["LC_ALL"] = "English_United States.utf8"
        environment["RESEARCHPATH_PARALLEL_WORKERS"] = str(settings.r_parallel_workers)
        self.process_job: WindowsProcessJob | None = None
        creation_flags = (subprocess.CREATE_NO_WINDOW | 0x00000004) if os.name == "nt" else 0
        self.process = subprocess.Popen(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(settings.r_worker_path),
            ],
            cwd=settings.project_root,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creation_flags,
        )
        if os.name == "nt":
            try:
                self.process_job = WindowsProcessJob(self.process)
            except BaseException:
                self.process.kill()
                self.process.wait(timeout=2)
                raise
        self.reader = threading.Thread(
            target=self._read_stdout,
            name=f"researchpath-r-worker-{ordinal}-stdout",
            daemon=True,
        )
        self.stderr_reader = threading.Thread(
            target=self._read_stderr,
            name=f"researchpath-r-worker-{ordinal}-stderr",
            daemon=True,
        )
        self.reader.start()
        self.stderr_reader.start()
        ready_deadline = time.monotonic() + 30
        while not self.ready.is_set():
            if cancel_event is not None and cancel_event.is_set():
                self.terminate(grace_period=0.1)
                raise RWorkerCancelled("分析在启动 R worker 时被取消")
            remaining = ready_deadline - time.monotonic()
            if remaining <= 0:
                break
            self.ready.wait(timeout=min(0.1, remaining))
        if not self.ready.is_set():
            message = "".join(self.stderr_tail).strip()
            self.terminate()
            raise RWorkerUnavailable(
                f"R worker {ordinal} did not become ready: {message or 'no diagnostics'}"
            )

    @property
    def alive(self) -> bool:
        return self.process.poll() is None

    def _read_stdout(self) -> None:
        if self.process.stdout is None:
            return
        for line in self.process.stdout:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("R worker %d returned invalid JSON protocol message: %r", self.ordinal, line[:200])
                self.stderr_tail.append(f"protocol: {line}")
                continue
            if message.get("type") == "ready":
                self.ready.set()
            else:
                self.responses.put(message)

    def _read_stderr(self) -> None:
        if self.process.stderr is None:
            return
        for line in self.process.stderr:
            self.stderr_tail.append(line)

    def submit(self, request: dict[str, Any]) -> None:
        if not self.alive or self.process.stdin is None:
            raise RWorkerUnavailable("R worker exited before the request was submitted")
        try:
            self.process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as error:
            raise RWorkerUnavailable("R worker input pipe is unavailable") from error

    def terminate(self, *, grace_period: float = 2.0) -> None:
        if self.process_job is not None:
            self.process_job.close()
            self.process_job = None
        if not self.alive:
            return
        if self.alive:
            self.process.terminate()
            try:
                self.process.wait(timeout=grace_period)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=grace_period)

    def shutdown(self) -> None:
        if not self.alive:
            self.terminate()
            return
        try:
            self.submit({"type": "shutdown"})
            self.process.wait(timeout=5)
        except (RWorkerError, subprocess.TimeoutExpired):
            self.terminate()
        finally:
            if self.process_job is not None:
                self.process_job.close()
                self.process_job = None


class RWorkerPool:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._available: queue.Queue[_RWorkerProcess] = queue.Queue()
        self._workers: list[_RWorkerProcess] = []
        self._lock = threading.RLock()
        self._starting_ordinals: set[int] = set()
        self._started = False
        self._closed = False
        self._degraded_reason: str | None = None
        atexit.register(self.close)

    @contextmanager
    def _cancellable_lock(self, cancel_event: threading.Event | None) -> Iterator[None]:
        while not self._lock.acquire(timeout=0.05):
            if cancel_event is not None and cancel_event.is_set():
                raise RWorkerCancelled("分析在等待 R worker 启动锁时被取消")
        try:
            if cancel_event is not None and cancel_event.is_set():
                raise RWorkerCancelled("分析在等待 R worker 启动锁时被取消")
            yield
        finally:
            self._lock.release()

    def start(self, cancel_event: threading.Event | None = None) -> None:
        with self._cancellable_lock(cancel_event):
            if self._closed:
                raise RWorkerUnavailable("R worker pool is closed")
            if self._started:
                return
            if cancel_event is not None and cancel_event.is_set():
                raise RWorkerCancelled("分析在启动 R worker 前被取消")
            if not self.settings.rscript_path.exists():
                raise RWorkerUnavailable(f"Rscript 不存在: {self.settings.rscript_path}")
            if not self.settings.r_worker_path.exists():
                raise RWorkerUnavailable(f"R worker 脚本不存在: {self.settings.r_worker_path}")
            workers: list[_RWorkerProcess] = []
            try:
                for ordinal in range(1, self.settings.r_worker_count + 1):
                    workers.append(_RWorkerProcess(self.settings, ordinal, cancel_event))
            except Exception:
                termination_grace_period = (
                    0.1 if cancel_event is not None and cancel_event.is_set() else 2.0
                )
                for worker in workers:
                    worker.terminate(grace_period=termination_grace_period)
                raise
            self._workers = workers
            for worker in workers:
                self._available.put(worker)
            self._started = True
            self._degraded_reason = None

    def _repair_capacity(self, cancel_event: threading.Event | None = None) -> None:
        """Reserve slots under the lock, but never hold it while starting R.

        A different task must be able to cancel and remove its worker while a
        replacement is cold-starting. Reservations prevent duplicate capacity.
        """
        with self._cancellable_lock(cancel_event):
            if self._closed:
                return
            active_ordinals = {worker.ordinal for worker in self._workers}
            missing_ordinals = [
                ordinal for ordinal in range(1, self.settings.r_worker_count + 1)
                if ordinal not in active_ordinals and ordinal not in self._starting_ordinals
            ]
            self._starting_ordinals.update(missing_ordinals)
        try:
            for ordinal in missing_ordinals:
                try:
                    replacement = _RWorkerProcess(self.settings, ordinal, cancel_event)
                except RWorkerCancelled:
                    raise
                except Exception as error:
                    self._degraded_reason = str(error)
                    continue
                with self._lock:
                    closed = self._closed
                    if not closed:
                        self._workers.append(replacement)
                        self._available.put(replacement)
                        self._degraded_reason = None
                if closed:
                    replacement.terminate(grace_period=0.1)
        finally:
            with self._lock:
                self._starting_ordinals.difference_update(missing_ordinals)

    def _replace(
        self,
        worker: _RWorkerProcess,
        *,
        termination_grace_period: float = 2.0,
        repair_capacity: bool = True,
    ) -> None:
        worker.terminate(grace_period=termination_grace_period)
        with self._lock:
            try:
                self._workers.remove(worker)
            except ValueError:
                pass
        if repair_capacity:
            self._repair_capacity()

    def run(
        self,
        *,
        script_path: Path,
        input_path: Path,
        output_path: Path,
        log_path: Path,
        cancel_event: threading.Event | None = None,
        cancel_path: Path | None = None,
        progress_path: Path | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        timeout: float = 180,
        repair_capacity_on_cancel: bool = False,
    ) -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise RWorkerCancelled("分析在启动 R worker 前被取消")
        pool_was_started = self._started
        self.start(cancel_event=cancel_event)
        self._repair_capacity(cancel_event=cancel_event)
        started = time.monotonic()
        worker: _RWorkerProcess | None = None
        while worker is None:
            if cancel_event is not None and cancel_event.is_set():
                raise RWorkerCancelled("分析在等待 R worker 时被取消")
            if time.monotonic() - started >= timeout:
                detail = (
                    f"；最近的恢复错误：{self._degraded_reason}" if self._degraded_reason else ""
                )
                raise RWorkerUnavailable(f"等待 R worker 超时{detail}")
            try:
                worker = self._available.get(timeout=0.1)
            except queue.Empty:
                continue
        request_id = uuid.uuid4().hex
        request = {
            "type": "execute",
            "requestId": request_id,
            "scriptPath": str(script_path.resolve()),
            "inputPath": str(input_path.resolve()),
            "outputPath": str(output_path.resolve()),
            "logPath": str(log_path.resolve()),
            "cancelPath": str(cancel_path.resolve()) if cancel_path is not None else None,
            "progressPath": str(progress_path.resolve()) if progress_path is not None else None,
            "parallelWorkers": self.settings.r_parallel_workers,
        }
        last_progress = ""
        reusable = True
        termination_grace_period = 2.0
        # Eager startup can exceed the cancellation SLA. Cancellation defers
        # repair by default; ordinary sequential worker failures still repair
        # inline. The next request repairs a deferred slot before waiting.
        repair_capacity = pool_was_started and self.settings.r_parallel_workers <= 1
        try:
            worker.submit(request)
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    touch_cancel_marker(cancel_path)
                    if not repair_capacity_on_cancel:
                        repair_capacity = False
                    try:
                        response = worker.responses.get(timeout=0.05)
                        if response.get("requestId") == request_id:
                            raise RWorkerCancelled("分析已由用户取消")
                    except queue.Empty:
                        reusable = False
                        termination_grace_period = 0.1
                        raise RWorkerCancelled("分析已由用户取消") from None
                if time.monotonic() - started >= timeout:
                    reusable = False
                    raise RWorkerUnavailable("R worker 执行超时")
                last_progress, payload = read_progress_if_changed(
                    progress_path, last_progress, progress_callback
                )
                if payload is not None and progress_callback is not None:
                    progress_callback(payload)
                try:
                    response = worker.responses.get(timeout=0.1)
                except queue.Empty:
                    if not worker.alive:
                        reusable = False
                        raise RWorkerUnavailable(
                            "R worker unexpectedly exited: " + "".join(worker.stderr_tail).strip()
                        ) from None
                    continue
                if response.get("requestId") != request_id:
                    reusable = False
                    raise RWorkerUnavailable("R worker response did not match request")
                if not response.get("ok"):
                    message = str(response.get("error") or "R worker task failed")
                    if (
                        response.get("cancelled")
                        or (cancel_event is not None and cancel_event.is_set())
                        or (cancel_path is not None and cancel_path.exists())
                    ):
                        raise RWorkerCancelled("分析已由用户取消")
                    raise RWorkerTaskError(message)
                return
        finally:
            if reusable and worker.alive:
                self._available.put(worker)
            else:
                self._replace(
                    worker,
                    termination_grace_period=termination_grace_period,
                    repair_capacity=repair_capacity,
                )

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            workers = list(self._workers)
            self._workers.clear()
            for worker in workers:
                worker.shutdown()
