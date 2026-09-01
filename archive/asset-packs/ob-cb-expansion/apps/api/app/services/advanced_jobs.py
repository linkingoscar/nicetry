from __future__ import annotations

import shutil
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pydantic import TypeAdapter

from app.advanced_contracts import AdvancedAnalysisSpec
from app.services.advanced_runner import (
    AdvancedExecutionError,
    _canonical_advanced_hash,
    execute_cancellable_advanced_analysis,
)
from app.services.dataset_repository import DatasetRepository
from app.settings import Settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AdvancedQueueFullError(RuntimeError):
    pass


class AdvancedJobManager:
    def __init__(
        self,
        repository: DatasetRepository,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.executor = ThreadPoolExecutor(
            max_workers=settings.r_worker_count,
            thread_name_prefix="researchpath-advanced",
        )
        total_capacity = settings.r_worker_count + settings.analysis_queue_capacity
        self._submission_slots = threading.BoundedSemaphore(total_capacity)
        self.events: dict[str, threading.Event] = {}
        self.futures: dict[str, Future[Any]] = {}
        self.listeners: dict[str, list[tuple[Any, Any]]] = {}
        self.lock = threading.RLock()
        self._closed = False
        self._recover_interrupted_jobs()

    def register_listener(self, run_id: str, queue: Any, loop: Any) -> None:
        with self.lock:
            self.listeners.setdefault(run_id, []).append((queue, loop))

    def unregister_listener(self, run_id: str, queue: Any) -> None:
        with self.lock:
            if run_id not in self.listeners:
                return
            self.listeners[run_id] = [
                item for item in self.listeners[run_id] if item[0] is not queue
            ]
            if not self.listeners[run_id]:
                del self.listeners[run_id]

    def _recover_interrupted_jobs(self) -> None:
        import os
        import subprocess

        for state in self.repository.list_unfinished_advanced_jobs():
            pid = state.get("pid")
            if pid is not None:
                try:
                    if os.name == "nt":
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True
                        )
                    else:
                        import signal

                        os.killpg(os.getpgid(pid), signal.SIGKILL)
                except Exception:
                    pass
            state.update(
                status="failed",
                stage="failed",
                error="分析服务重启，原后台进程已中断；请重新运行。",
            )
            self._save(state)

    def _path(self, run_id: str) -> Path:
        return self.settings.state_root / "projects" / "default" / "runs" / run_id / "state.json"

    def _save(self, state: dict[str, Any]) -> None:
        state["updatedAt"] = _utc_now()
        self.repository.save_advanced_job(state, self._path(state["id"]))
        state_copy = dict(state)
        state_copy.pop("result", None)
        with self.lock:
            for queue, loop in self.listeners.get(state["id"], []):
                try:
                    loop.call_soon_threadsafe(queue.put_nowait, state_copy)
                except Exception:
                    pass

    def start(self, spec: AdvancedAnalysisSpec) -> dict[str, Any]:
        if self._closed:
            raise RuntimeError("高级分析任务管理器已经关闭")
        if not self._submission_slots.acquire(blocking=False):
            raise AdvancedQueueFullError(
                f"队列已满，最多允许 {self.settings.analysis_queue_capacity} 个等待任务"
            )
        run_id = f"advanced_{uuid.uuid4().hex}"
        now = _utc_now()
        spec_hash = _canonical_advanced_hash(spec)
        state = {
            "id": run_id,
            "analysisId": getattr(spec, "analysis_id", None),
            "family": spec.family,
            "specHash": spec_hash,
            "datasetVersionId": getattr(spec, "dataset_version_id", None),
            "status": "queued",
            "stage": "queued",
            "progress": 0.0,
            "cancelRequested": False,
            "createdAt": now,
            "updatedAt": now,
            "error": None,
            "result": None,
            "resultPath": None,
            "spec": spec.model_dump(mode="json", by_alias=True),
        }
        event = threading.Event()
        try:
            self._save(state)
            with self.lock:
                self.events[run_id] = event
                future = self.executor.submit(self._run_advanced, state, spec, event)
                self.futures[run_id] = future
                future.add_done_callback(lambda _completed: self._submission_slots.release())
        except Exception:
            self._submission_slots.release()
            raise
        return state

    def _progress_callback(self, run_id: str) -> Callable[[dict[str, Any]], None]:
        last_save_time = 0.0
        last_save_progress = -1.0
        last_save_stage = ""

        def progress(update: dict[str, Any]) -> None:
            nonlocal last_save_time, last_save_progress, last_save_stage
            with self.lock:
                current = self.get(run_id)
                if current["status"] not in {"queued", "running", "cancelling"}:
                    return
                stage = str(update.get("stage", current["stage"]))
                fraction = float(update.get("progress", current["progress"]))
                current.update(
                    stage=stage,
                    progress=fraction,
                )
                now = time.monotonic()
                if (
                    stage != last_save_stage
                    or abs(fraction - last_save_progress) >= 0.05
                    or now - last_save_time >= 2.0
                    or fraction >= 1.0
                ):
                    self._save(current)
                    last_save_time = now
                    last_save_progress = fraction
                    last_save_stage = stage

        return progress

    def _run_advanced(
        self,
        state: dict[str, Any],
        spec: AdvancedAnalysisSpec,
        event: threading.Event,
    ) -> None:
        run_id = state["id"]
        work_dir = self._path(run_id).parent / "work"
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            with self.lock:
                current = self.get(run_id)
                current.update(status="running", stage="preparing_data", progress=0.02)
                self._save(current)

            def _on_started(pid: int) -> None:
                with self.lock:
                    current = self.get(run_id)
                    current["pid"] = pid
                    self._save(current)

            result = execute_cancellable_advanced_analysis(
                spec,
                self.repository,
                run_id,
                work_dir,
                self.settings,
                event,
                self._progress_callback(run_id),
                on_started=_on_started,
            )
            result_path = self.repository.record_advanced_result(run_id, result)
            self._cleanup_work_directory(work_dir)
            with self.lock:
                current = self.get(run_id)
                current.update(
                    status="succeeded",
                    stage="succeeded",
                    progress=1.0,
                    result=None,
                    resultPath=result_path.relative_to(self.settings.state_root).as_posix(),
                )
                self._save(current)
        except AdvancedExecutionError as error:
            self._cleanup_work_directory(work_dir)
            if error.code == "ANALYSIS_CANCELLED":
                self._mark_cancelled(run_id)
            else:
                self._mark_failed(run_id, error)
        except Exception as error:
            self._cleanup_work_directory(work_dir)
            self._mark_failed(run_id, error)
        finally:
            self._finish_running_job(run_id, work_dir)

    def _mark_cancelled(self, run_id: str) -> None:
        with self.lock:
            current = self.get(run_id)
            current.update(
                status="cancelled",
                stage="cancelled",
                error="高级分析已由用户取消",
            )
            self._save(current)

    def _mark_failed(self, run_id: str, error: Exception) -> None:
        with self.lock:
            current = self.get(run_id)
            if isinstance(error, AdvancedExecutionError):
                current.update(
                    status="failed",
                    stage="failed",
                    error=error.message,
                    errorCode=error.code,
                    errorDetails=error.details,
                )
            else:
                current.update(status="failed", stage="failed", error=str(error))
            self._save(current)

    def _finish_running_job(self, run_id: str, work_dir: Path) -> None:
        with self.lock:
            self.events.pop(run_id, None)
            self.futures.pop(run_id, None)
        self._cleanup_work_directory(work_dir)

    @staticmethod
    def _cleanup_work_directory(work_dir: Path) -> None:
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)

    def get(self, run_id: str) -> dict[str, Any]:
        return self.repository.get_advanced_job(run_id)

    def get_result(self, run_id: str) -> dict[str, Any]:
        state = self.get(run_id)
        if state.get("status") != "succeeded" or not state.get("resultPath"):
            raise ValueError("高级分析尚未成功完成")
        return self.repository.get_advanced_result(run_id)

    def get_spec(self, run_id: str) -> AdvancedAnalysisSpec:
        state = self.get(run_id)
        payload = state.get("spec")
        if not isinstance(payload, dict):
            raise LookupError(f"AdvancedAnalysis 规格不存在: {run_id}")
        try:
            spec = TypeAdapter(AdvancedAnalysisSpec).validate_python(payload)
        except ValueError as error:
            raise LookupError(f"AdvancedAnalysis 规格损坏: {run_id}") from error
        if _canonical_advanced_hash(spec) != state.get("specHash"):
            raise LookupError(f"AdvancedAnalysis 规格身份不匹配: {run_id}")
        return spec

    def cancel(self, run_id: str) -> dict[str, Any]:
        with self.lock:
            state = self.get(run_id)
            if state["status"] not in {"queued", "running", "cancelling"}:
                return state
            state.update(cancelRequested=True, stage="cancelling")
            event = self.events.get(run_id)
            future = self.futures.get(run_id)
            cancelled_before_start = future.cancel() if future is not None else False
            if cancelled_before_start:
                self.events.pop(run_id, None)
                self.futures.pop(run_id, None)
                state.update(
                    status="cancelled",
                    stage="cancelled",
                    error="分析在排队阶段已由用户取消",
                )
            self._save(state)
            if event is not None:
                event.set()
            return state

    def close(self) -> None:
        with self.lock:
            if self._closed:
                return
            self._closed = True
            for event in self.events.values():
                event.set()
        self.executor.shutdown(wait=True, cancel_futures=True)
