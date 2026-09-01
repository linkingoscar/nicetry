from __future__ import annotations

import shutil
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from app.services.analysis_context import AnalysisContextResolutionError, AnalysisContextService
from app.services.analysis_job_progress import create_progress_callback
from app.services.analysis_job_results import AnalysisResultReader
from app.services.analysis_jobs_recovery import recover_interrupted_jobs
from app.services.capability_applicability import applicable_capability_registry
from app.services.dataset_repository import DatasetRepository, _write_json_atomic
from app.services.empirical_analysis import run_empirical_analysis
from app.services.empirical_context_gate import require_empirical_capability
from app.services.empirical_export import empirical_report_path
from app.services.model_service import validate_model_context
from app.services.r_engine import AnalysisCancelled, execute_cancellable_analysis
from app.services.r_workers import RWorkerPool
from app.services.repository_io import remove_path_tree
from app.services.repository_io import utc_now as _utc_now
from app.services.status_model import apply_status_model
from app.services.study_plans import StudyPlanService
from app.settings import Settings


class AnalysisQueueFullError(RuntimeError):
    pass


class AnalysisJobManager:
    def __init__(
        self, repository: DatasetRepository, settings: Settings, r_worker_pool: RWorkerPool,
        context_service: AnalysisContextService | None = None,
        study_plan_service: StudyPlanService | None = None,
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.r_worker_pool = r_worker_pool
        self.context_service = context_service or AnalysisContextService(repository)
        self.study_plan_service = study_plan_service or StudyPlanService(
            repository, applicable_capability_registry
        )
        self.result_reader = AnalysisResultReader(repository, self.study_plan_service)
        self.applicability_registry = applicable_capability_registry
        self.executor = ThreadPoolExecutor(
            max_workers=settings.r_worker_count,
            thread_name_prefix="researchpath-analysis",
        )
        total_capacity = settings.r_worker_count + settings.analysis_queue_capacity
        self._submission_slots = threading.BoundedSemaphore(total_capacity)
        self.events: dict[str, threading.Event] = {}
        self.futures: dict[str, Future[Any]] = {}
        self.listeners: dict[str, list[tuple[Any, Any]]] = {}
        self.lock = threading.RLock()
        self._closed = False
        self._recover_interrupted_jobs()

    def register_listener(self, run_id: str, queue: Any, loop: Any) -> bool:
        """Register one SSE listener; returns False when the budget is exhausted.

        Bounded per-run and global listener counts keep anonymous local
        connections from exhausting memory (each listener owns an unbounded
        asyncio queue fed on every progress save).
        """
        with self.lock:
            per_run = len(self.listeners.get(run_id, []))
            total = sum(len(items) for items in self.listeners.values())
            if per_run >= 2 or total >= 50:
                return False
            self.listeners.setdefault(run_id, []).append((queue, loop))
            return True

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
        recover_interrupted_jobs(self)

    def _path(self, run_id: str) -> Path:
        return self.settings.state_root / "projects" / "default" / "runs" / run_id / "state.json"

    def _save(self, state: dict[str, Any]) -> None:
        state["updatedAt"] = _utc_now()
        self.repository.save_analysis_job(state, self._path(state["id"]))
        state_copy = dict(state)
        state_copy.pop("result", None)
        with self.lock:
            for queue, loop in self.listeners.get(state["id"], []):
                try:
                    loop.call_soon_threadsafe(queue.put_nowait, state_copy)
                except Exception:
                    pass

    def _enqueue(self, state: dict[str, Any], target: Callable[..., None], *target_args: Any) -> dict[str, Any]:
        if self._closed:
            raise RuntimeError("分析任务管理器已经关闭")
        if not self._submission_slots.acquire(blocking=False):
            raise AnalysisQueueFullError(
                f"分析队列已满，最多允许 {self.settings.analysis_queue_capacity} 个等待任务"
            )
        event = threading.Event()
        try:
            self._save(state)
            with self.lock:
                self.events[state["id"]] = event
                future = self.executor.submit(target, state, *target_args, event)
                self.futures[state["id"]] = future
                future.add_done_callback(lambda _completed: self._submission_slots.release())
        except Exception:
            self._submission_slots.release()
            raise
        return state

    def start(
        self,
        dataset_id: str,
        model_id: str,
        version: int,
        study_plan_binding: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        frozen = self.repository.get_model_version(model_id, version)
        if frozen["datasetId"] != dataset_id:
            raise ValueError("ModelVersion 不属于该数据集")
        if not frozen.get("validation", {}).get("executionAvailable", False):
            reason = frozen.get("validation", {}).get("unsupportedReason")
            raise ValueError(reason or "该模型结构当前仅支持识别与保存，尚未开放估计")
        context_lineage = validate_model_context(
            dataset_id,
            frozen["modelSpec"],
            self.context_service,
        )
        run_id = f"run_{uuid.uuid4().hex}"
        now = _utc_now()
        state = {
            "id": run_id,
            "jobKind": "model",
            "datasetId": dataset_id,
            "modelId": model_id,
            "modelVersion": version,
            "modelVersionId": frozen["id"],
            "status": "queued",
            "stage": "queued",
            "progress": 0.0,
            "completedReplicates": 0,
            "totalReplicates": 0,
            "cancelRequested": False,
            "createdAt": now,
            "updatedAt": now,
            "error": None,
            "result": None,
            "resultPath": None,
        }
        if context_lineage is not None:
            state["contextLineage"] = context_lineage
            state["contextHash"] = context_lineage.get("contextHash")
            state["metadata"] = context_lineage
        if study_plan_binding is not None:
            state["studyPlanBinding"] = self.study_plan_service.bind_for_execution(dataset_id, study_plan_binding, execution_spec=frozen["modelSpec"], identity=context_lineage, spec_hash=frozen["modelHash"])
        return self._enqueue(state, self._run_model, frozen)
    def start_empirical(
        self,
        dataset_id: str,
        measurement_version: int | None,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        measurement = self.repository.get_measurement(dataset_id, measurement_version) if measurement_version is not None else None
        if measurement is None and self.repository.get_dataset(dataset_id).get("dictionary", {}).get("status") != "confirmed":
            raise ValueError("请先确认变量字典，再运行原始变量分析。")
        if measurement is None and options.get("procedure") not in {
            "descriptives", "frequencies", "missing", "correlation", "groups",
            "regression", "relative_importance", "response_surface",
        }:
            raise ValueError("此方法需要已确认的测量版本；基础原始变量分析可直接运行。")
        sample_version_id = options.get("sampleVersionId") or options.get("sample_version_id")
        context = self.context_service.resolve(
            dataset_id,
            measurement_version=measurement_version,
            include_measurement=measurement is not None,
            sample_version_id=str(sample_version_id) if sample_version_id else None,
        )
        requested_context_hash = options.get("contextHash") or options.get("context_hash")
        if requested_context_hash and requested_context_hash != context["contextHash"]:
            raise AnalysisContextResolutionError(
                "ANALYSIS_CONTEXT_CHANGED",
                "当前数据、样本、测量或结构版本已变化；请回到分析中心重新确认上下文。",
            )
        applicable_slices = require_empirical_capability(context, options, self.applicability_registry)
        panel = options.get("longitudinalPanel")
        diary = options.get("diaryMultilevel")
        if panel or diary:
            structure = context.get("structure")
            if context.get("validity") != "ready" or not isinstance(structure, dict):
                raise AnalysisContextResolutionError(
                    "ANALYSIS_CONTEXT_INCOMPLETE",
                    "面板与 ESM 分析必须先完成研究上下文和数据结构角色绑定。",
                )
            roles = structure.get("roles", {})
            if not isinstance(roles, dict):
                roles = {}
            if panel and panel.get("subjectVariableId") != roles.get("subjectId"):
                raise AnalysisContextResolutionError(
                    "CONTEXT_ROLE_MISMATCH",
                    "纵向面板的 subject 变量必须使用当前结构版本绑定的 subjectId。",
                )
            if diary and (
                diary.get("subjectVariableId") != roles.get("subjectId")
                or diary.get("timeVariableId") != roles.get("timeId")
            ):
                raise AnalysisContextResolutionError(
                    "CONTEXT_ROLE_MISMATCH",
                    "ESM 的 subject/time 变量必须使用当前结构版本绑定的角色。",
                )
        bound_options = dict(options)
        bound_options["contextHash"] = context["contextHash"]
        study_context = context.get("studyContext")
        study_value = study_context.get("value", {}) if isinstance(study_context, dict) else {}
        bound_options["contextTimeStructure"] = study_value.get("timeStructure")
        bound_options["contextDependenceStructure"] = study_value.get("dependenceStructure")
        bound_options["contextDesign"] = study_value.get("design")
        bound_options["applicableCapabilitySlices"] = list(applicable_slices)
        study_plan_binding = options.get("studyPlanBinding")
        if study_plan_binding is not None:
            if not isinstance(study_plan_binding, dict):
                raise ValueError("STUDY_PLAN_BINDING_INVALID: StudyPlan 绑定必须是对象")
            study_plan_binding = self.study_plan_service.bind_for_execution(dataset_id, study_plan_binding, execution_spec=bound_options, identity=context)
            bound_options["studyPlanBinding"] = study_plan_binding
            bound_options["studyPlanMultiplicity"] = self.study_plan_service.binding.multiplicity_context(
                self.study_plan_service, study_plan_binding
            )
        report_id = f"empirical_{uuid.uuid4().hex[:16]}"
        run_id = f"run_{uuid.uuid4().hex}"
        now = _utc_now()
        state = {
            "id": run_id,
            "jobKind": "empirical",
            "datasetId": dataset_id,
            "measurementVersion": measurement_version,
            "measurementVersionId": measurement["id"] if measurement else None,
            "modelId": "__empirical__",
            "modelVersion": measurement_version or 0,
            "modelVersionId": measurement["id"] if measurement else dataset_id,
            "reportId": report_id,
            "status": "queued",
            "stage": "queued",
            "progress": 0.0,
            "completedReplicates": 0,
            "totalReplicates": int(options.get("parallelIterations", 0)),
            "cancelRequested": False,
            "createdAt": now,
            "updatedAt": now,
            "error": None,
            "result": None,
            "resultPath": None,
            "warnings": [],
            "options": bound_options,
            "contextLineage": {
                "contextHash": context["contextHash"],
                "dataset": context["dataset"],
                "studyContext": context.get("studyContext"),
                "structure": context.get("structure"),
                "measurement": context.get("measurement"),
                "sample": context.get("sample"),
                "imputation": context.get("imputation"),
                "validity": context.get("validity"),
            },
            "metadata": None,
        }
        if study_plan_binding is not None:
            state["studyPlanBinding"] = study_plan_binding
        return self._enqueue(state, self._run_empirical, bound_options)
    def _progress_callback(self, run_id: str) -> Callable[[dict[str, Any]], None]:
        return create_progress_callback(run_id, self.lock, self.get, self._save)
    def _run_model(
        self,
        state: dict[str, Any],
        frozen: dict[str, Any],
        event: threading.Event,
    ) -> None:
        run_id = state["id"]
        work_dir = self._path(run_id).parent / "work"
        try:
            with self.lock:
                current = self.get(run_id)
                current.update(status="running", stage="preparing_data", progress=0.02)
                self._save(current)
            dataset = self.repository.get_dataset(state["datasetId"])
            measurement = self.repository.get_measurement_for_derived(
                state["datasetId"], frozen["modelSpec"]["datasetVersionId"]
            )
            result = execute_cancellable_analysis(
                frozen["modelSpec"],
                dataset,
                measurement,
                frozen["id"],
                run_id,
                work_dir,
                self.settings,
                event,
                self._progress_callback(run_id),
                self.r_worker_pool,
            )
            if event.is_set():
                raise AnalysisCancelled("分析已由用户取消")
            context_lineage = state.get("contextLineage")
            if isinstance(context_lineage, dict):
                provenance = result.get("provenance")
                if not isinstance(provenance, dict):
                    provenance = {}
                provenance.update(context_lineage)
                result["provenance"] = provenance
            study_plan_binding = state.get("studyPlanBinding")
            if isinstance(study_plan_binding, dict):
                self.study_plan_service.binding.attach_result_binding(result, study_plan_binding)
                apply_status_model(result)
            work_csv = work_dir / "analysis-data.csv"
            if work_csv.exists():
                shutil.copy2(work_csv, work_dir.parent / "analysis-data.csv")
            result_path = self.repository.record_analysis_result(
                state["datasetId"], state["modelId"], state["modelVersion"], result
            )
            replicates = (
                int(
                    frozen["modelSpec"]
                    .get("estimation", {})
                    .get("bootstrap", {})
                    .get("replicates", 0)
                )
                if frozen["modelSpec"].get("estimation", {}).get("bootstrap", {}).get("enabled")
                else 0
            )
            self._cleanup_work_directory(work_dir)
            with self.lock:
                current = self.get(run_id)
                current.update(
                    status="succeeded",
                    stage="succeeded",
                    progress=1.0,
                    completedReplicates=replicates,
                    totalReplicates=replicates,
                    result=None,
                    resultPath=result_path.relative_to(self.settings.state_root).as_posix(),
                )
                self._save(current)
        except AnalysisCancelled:
            self._cleanup_work_directory(work_dir)
            self._mark_cancelled(run_id)
        except Exception as error:
            self._cleanup_work_directory(work_dir)
            self._mark_failed(run_id, error)
        finally:
            self._finish_running_job(run_id, work_dir)

    def _run_empirical(
        self,
        state: dict[str, Any],
        options: dict[str, Any],
        event: threading.Event,
    ) -> None:
        run_id = state["id"]
        work_dir = self._path(run_id).parent / "work"
        report_path = empirical_report_path(state["datasetId"], state["measurementVersion"], state["reportId"], self.settings)
        try:
            with self.lock:
                current = self.get(run_id)
                current.update(status="running", stage="preparing_data", progress=0.02)
                self._save(current)
            report = run_empirical_analysis(
                state["datasetId"],
                state["measurementVersion"],
                options,
                self.repository,
                self.settings,
                self.r_worker_pool,
                cancel_event=event,
                progress_callback=self._progress_callback(run_id),
                work_dir=work_dir,
                report_id=state["reportId"],
                context_lineage=state.get("contextLineage"),
            )
            if event.is_set():
                raise AnalysisCancelled("分析已由用户取消")
            study_plan_binding = state.get("studyPlanBinding")
            if isinstance(study_plan_binding, dict):
                self.study_plan_service.binding.attach_result_binding(report, study_plan_binding)
                apply_status_model(report)
            _write_json_atomic(report_path, report)
            self._cleanup_work_directory(work_dir)
            with self.lock:
                current = self.get(run_id)
                current.update(
                    status="succeeded",
                    stage="succeeded",
                    progress=1.0,
                    reportId=report["reportId"],
                    resultPath=report_path.relative_to(self.settings.state_root).as_posix(),
                    warnings=report.get("warnings", []),
                    options=report.get("options"),
                    metadata=report.get("provenance"),
                )
                self._save(current)
        except AnalysisCancelled:
            self._cleanup_work_directory(work_dir)
            remove_path_tree(report_path.parent)
            self._mark_cancelled(run_id)
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
                error="分析已由用户取消",
            )
            self._save(current)

    def _mark_failed(self, run_id: str, error: Exception) -> None:
        with self.lock:
            current = self.get(run_id)
            current.update(status="failed", stage="failed", error=str(error), errorDetails=getattr(error, "diagnostic", None))
            self._save(current)

    def _finish_running_job(self, run_id: str, work_dir: Path) -> None:
        with self.lock:
            self.events.pop(run_id, None)
            self.futures.pop(run_id, None)
        self._cleanup_work_directory(work_dir)

    @staticmethod
    def _cleanup_work_directory(work_dir: Path) -> None:
        remove_path_tree(work_dir, retries=30, delay=0.05)

    def get(self, run_id: str) -> dict[str, Any]:
        return self.repository.get_analysis_job(run_id)

    def get_result(self, run_id: str) -> dict[str, Any]:
        return self.result_reader.get_result(run_id, self.get(run_id))
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

    def cleanup_runs(
        self,
        keep_count: int | None = None,
        older_than_days: float | None = None,
    ) -> int:
        run_ids = self.repository.list_terminal_analysis_run_ids(
            keep_count=keep_count,
            older_than_days=older_than_days,
        )
        for run_id in run_ids:
            self.repository.delete_analysis_job_and_run(run_id)
        return len(run_ids)

    def close(self) -> None:
        with self.lock:
            if self._closed:
                return
            self._closed = True
            for event in self.events.values():
                event.set()
        self.executor.shutdown(wait=True, cancel_futures=True)
