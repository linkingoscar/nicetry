from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Callable, cast

from pydantic import TypeAdapter

from app.advanced_contracts import AdvancedAnalysisSpec
from app.services.advanced_analysis import advanced_analysis_registry
from app.services.advanced_runner import (
    AdvancedExecutionError,
    _canonical_advanced_hash,
    execute_cancellable_advanced_analysis,
)
from app.services.analysis_context import AnalysisContextResolutionError, AnalysisContextService
from app.services.capability_applicability import (
    CapabilityApplicabilityRegistry,
    applicable_capability_registry,
)
from app.services.dataset_repository import DatasetRepository
from app.services.process_ownership import (
    get_process_commandline,
    is_process_owned_by_runtime,
    kill_process_tree,
)
from app.services.repository_io import JsonObject, remove_path_tree
from app.services.repository_io import utc_now as _utc_now
from app.settings import Settings

_process_commandline = get_process_commandline
_kill_process_tree = kill_process_tree


def _process_owned_by_runtime(pid: int, settings: Settings) -> bool:
    return is_process_owned_by_runtime(
        pid,
        settings,
        commandline_reader=_process_commandline,
    )


class AdvancedQueueFullError(RuntimeError):
    pass


class AdvancedJobManager:
    def __init__(
        self,
        repository: DatasetRepository,
        settings: Settings,
        context_service: AnalysisContextService | None = None,
        applicability_registry: CapabilityApplicabilityRegistry | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.context_service = context_service or AnalysisContextService(repository)
        self.applicability_registry = applicability_registry or applicable_capability_registry
        self.executor = ThreadPoolExecutor(
            max_workers=settings.r_worker_count,
            thread_name_prefix="researchpath-advanced",
        )
        total_capacity = settings.r_worker_count + settings.analysis_queue_capacity
        self._submission_slots = threading.BoundedSemaphore(total_capacity)
        self.events: dict[str, threading.Event] = {}
        self.futures: dict[str, Future[None]] = {}
        self.lock = threading.RLock()
        self._closed = False
        self._recover_interrupted_jobs()

    def _recover_interrupted_jobs(self) -> None:
        for state in self.repository.list_unfinished_advanced_jobs():
            pid = state.get("pid")
            if pid is not None and _process_owned_by_runtime(int(pid), self.settings):
                _kill_process_tree(int(pid))
            state.update(
                status="failed",
                stage="failed",
                error="分析服务重启，原后台进程已中断；请重新运行。",
            )
            self._save(state)

    def _path(self, run_id: str) -> Path:
        return self.settings.state_root / "projects" / "default" / "runs" / run_id / "state.json"

    def _save(self, state: JsonObject) -> None:
        state["updatedAt"] = _utc_now()
        self.repository.save_advanced_job(state, self._path(state["id"]))

    def _resolve_context_lineage(
        self, spec: AdvancedAnalysisSpec, dataset_id: str | None
    ) -> JsonObject | None:
        if spec.context_hash is None:
            if dataset_id is not None:
                raise AnalysisContextResolutionError(
                    "ANALYSIS_CONTEXT_REQUIRED",
                    "绑定数据版本的高级分析必须引用当前 resolved-analysis-context 和 analysis draft。",
                )
            return None
        bound_dataset_id = dataset_id or spec.dataset_version_id
        if not bound_dataset_id:
            raise AnalysisContextResolutionError(
                "ANALYSIS_CONTEXT_DATASET_REQUIRED",
                "上下文绑定的 advanced 分析必须指定 datasetVersionId。",
            )
        sample_id = spec.sample_version_id
        if sample_id and sample_id.startswith("sample_all_"):
            sample_id = None
        context = self.context_service.resolve(
            bound_dataset_id,
            sample_version_id=sample_id,
        )
        if spec.context_hash != context.get("contextHash"):
            raise AnalysisContextResolutionError(
                "ANALYSIS_CONTEXT_CHANGED",
                "上下文引用 contextHash 与当前服务端版本不一致，请重新创建分析草稿。",
            )
        if context.get("validity") != "ready":
            raise AnalysisContextResolutionError(
                "ANALYSIS_CONTEXT_INCOMPLETE",
                "上下文绑定的 advanced 分析必须先完成 study context 与结构角色确认。",
            )
        capability_slice = advanced_analysis_registry.slice_for_spec(spec)
        if capability_slice is None:
            raise AnalysisContextResolutionError(
                "CAPABILITY_SLICE_REQUIRED",
                "当前高级分析规格没有对应的已登记 capability slice。",
            )
        applicability = self.applicability_registry.evaluate_slice(
            capability_slice.id,
            context,
        )
        if not applicability.get("executionAvailable") or not applicability.get("applicable"):
            raise AnalysisContextResolutionError(
                "METHOD_NOT_APPLICABLE_TO_CONTEXT",
                str(applicability.get("blockedReason") or "当前研究上下文不满足该方法的适用性要求。"),
                {
                    "sliceId": capability_slice.id,
                    "missingRequirements": applicability.get("missingRequirements", []),
                    "blockedReason": applicability.get("blockedReason"),
                },
            )
        expected_refs = {
            "contextHash": spec.context_hash,
            "datasetSha256": spec.dataset_sha256,
            "sampleVersionId": spec.sample_version_id,
            "sampleHash": spec.sample_hash,
            "structureVersionId": spec.structure_version_id,
            "structureHash": spec.structure_hash,
            "measurementVersionId": spec.measurement_version_id,
            "measurementHash": spec.measurement_hash,
        }
        dataset_ref = cast(dict[str, object], context.get("dataset") or {})
        sample_ref = cast(dict[str, object], context.get("sample") or {})
        structure_ref = cast(dict[str, object], context.get("structure") or {})
        measurement_ref = cast(dict[str, object], context.get("measurement") or {})
        actual_refs = {
            "contextHash": context.get("contextHash"),
            "datasetSha256": dataset_ref.get("sha256"),
            "sampleVersionId": sample_ref.get("id"),
            "sampleHash": sample_ref.get("hash"),
            "structureVersionId": structure_ref.get("id"),
            "structureHash": structure_ref.get("hash"),
            "measurementVersionId": measurement_ref.get("id"),
            "measurementHash": measurement_ref.get("hash"),
        }
        for key, expected in expected_refs.items():
            if expected is not None and expected != actual_refs[key]:
                raise AnalysisContextResolutionError(
                    "ANALYSIS_CONTEXT_CHANGED",
                    f"上下文引用 {key} 与当前服务端版本不一致，请重新创建分析草稿。",
                )
        return {
            key: actual_refs[key]
            for key in actual_refs
            if actual_refs[key] is not None
        }

    def start(
        self,
        spec: AdvancedAnalysisSpec,
        metadata: JsonObject | None = None,
        dataset_id: str | None = None,
    ) -> JsonObject:
        if self._closed:
            raise RuntimeError("高级分析任务管理器已经关闭")
        bound_dataset_id = dataset_id or spec.dataset_version_id
        context_lineage = self._resolve_context_lineage(spec, bound_dataset_id)
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
            "datasetVersionId": getattr(spec, "dataset_version_id", None) or bound_dataset_id,
            "status": "queued",
            "stage": "queued",
            "progress": 0.0,
            "cancelRequested": False,
            "createdAt": now,
            "updatedAt": now,
            "error": None,
            "errorCode": None,
            "errorDetails": None,
            "remediation": None,
            "result": None,
            "resultPath": None,
            "spec": spec.model_dump(mode="json", by_alias=True),
        }
        if context_lineage is not None:
            state["contextLineage"] = context_lineage
            state["contextHash"] = context_lineage.get("contextHash")
        if metadata:
            state["metadata"] = dict(metadata)
        if context_lineage is not None:
            state["metadata"] = {
                **(state.get("metadata") or {}),
                **context_lineage,
            }
        for key in ("planVersionId", "imputationPlanVersionId", "contextHash"):
            if isinstance(metadata, dict) and metadata.get(key) is not None:
                state[key] = metadata[key]
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

    def _progress_callback(self, run_id: str) -> Callable[[JsonObject], None]:
        last_save_time = 0.0
        last_save_progress = -1.0
        last_save_stage = ""

        def progress(update: JsonObject) -> None:
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
        state: JsonObject,
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
            if event.is_set():
                raise AdvancedExecutionError("ANALYSIS_CANCELLED", "高级分析已由用户取消")
            context_lineage = state.get("contextLineage")
            if isinstance(context_lineage, dict):
                provenance = result.get("provenance")
                if not isinstance(provenance, dict):
                    provenance = {}
                provenance.update(context_lineage)
                result["provenance"] = provenance
            metadata = state.get("metadata")
            if isinstance(metadata, dict) and (
                metadata.get("imputationPlanVersionId") or metadata.get("planVersionId")
            ):
                plan_version_id = metadata.get("imputationPlanVersionId") or metadata.get("planVersionId")
                imputation_dataset_id = self.repository.save_imputation_dataset_version(
                    str(plan_version_id),
                    run_id,
                    result,
                )
                provenance = result.get("provenance")
                if not isinstance(provenance, dict):
                    provenance = {}
                provenance["imputationDatasetVersionId"] = imputation_dataset_id
                provenance["imputationPlanVersionId"] = plan_version_id
                result["provenance"] = provenance
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
                    remediation=error.remediation,
                )
            else:
                diagnostic = getattr(error, "diagnostic", None)
                current.update(
                    status="failed",
                    stage="failed",
                    error=str(error),
                    errorDetails=diagnostic,
                )
            self._save(current)

    def _finish_running_job(self, run_id: str, work_dir: Path) -> None:
        with self.lock:
            self.events.pop(run_id, None)
            self.futures.pop(run_id, None)
        self._cleanup_work_directory(work_dir)

    @staticmethod
    def _cleanup_work_directory(work_dir: Path) -> None:
        remove_path_tree(work_dir)

    def get(self, run_id: str) -> JsonObject:
        return self.repository.get_advanced_job(run_id)

    def get_result(self, run_id: str) -> JsonObject:
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

    def cancel(self, run_id: str) -> JsonObject:
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
