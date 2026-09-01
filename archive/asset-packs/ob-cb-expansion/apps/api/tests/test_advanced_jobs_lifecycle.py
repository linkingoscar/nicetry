from __future__ import annotations

import copy
import threading
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest

from app.advanced_contracts import EffectSize, PowerAnalysisSpec
from app.services import advanced_jobs
from app.services.advanced_jobs import AdvancedJobManager, AdvancedQueueFullError
from app.services.advanced_runner import AdvancedExecutionError
from app.services.dataset_repository import DatasetRepository
from app.services.repository_io import JsonObject
from app.settings import Settings, get_settings


class _Repository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.states: dict[str, JsonObject] = {}
        self.results: dict[str, JsonObject] = {}

    def list_unfinished_advanced_jobs(self) -> list[JsonObject]:
        return []

    def save_advanced_job(self, state: JsonObject, _path: Path) -> None:
        self.states[state["id"]] = copy.deepcopy(state)

    def get_advanced_job(self, run_id: str) -> JsonObject:
        return copy.deepcopy(self.states[run_id])

    def record_advanced_result(self, run_id: str, result: JsonObject) -> Path:
        self.results[run_id] = copy.deepcopy(result)
        path = self.settings.state_root / "projects" / "default" / "runs" / run_id / "result.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        return path

    def get_advanced_result(self, run_id: str) -> JsonObject:
        return copy.deepcopy(self.results[run_id])


class _PendingFuture:
    def __init__(self) -> None:
        self.callback: Callable[[object], None] | None = None

    def add_done_callback(self, callback: Callable[[object], None]) -> None:
        self.callback = callback


def _settings(tmp_path: Path, *, queue_capacity: int = 1) -> Settings:
    return replace(
        get_settings(),
        state_root=tmp_path / "workspace",
        r_worker_count=1,
        analysis_queue_capacity=queue_capacity,
    )


def _power_spec() -> PowerAnalysisSpec:
    return PowerAnalysisSpec(
        analysis_id="advanced_job_lifecycle",
        name="Advanced job lifecycle",
        family="power_analysis",
        design_family="regression",
        method="analytic",
        solve_for="sample_size",
        effect_size=EffectSize(metric="cohens_f2", value=0.15),
        predictors=3,
    )


def _queued_state(run_id: str) -> JsonObject:
    return {
        "id": run_id,
        "analysisId": "advanced_job_lifecycle",
        "family": "power_analysis",
        "status": "queued",
        "stage": "queued",
        "progress": 0.0,
        "cancelRequested": False,
        "result": None,
        "resultPath": None,
    }


def test_job_lifecycle_persists_progress_result_and_cleans_work_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    repository = _Repository(settings)
    manager = AdvancedJobManager(cast(DatasetRepository, repository), settings)

    def execute(
        _spec: PowerAnalysisSpec,
        _repository: _Repository,
        _run_id: str,
        work_dir: Path,
        _settings: Settings,
        _event: threading.Event,
        progress: Callable[[JsonObject], None],
        on_started: Callable[[int], None],
    ) -> JsonObject:
        assert work_dir.is_dir()
        on_started(731)
        progress({"stage": "estimating", "progress": 0.5})
        return {"familyResult": {"solvedValue": 77}}

    monkeypatch.setattr(advanced_jobs, "execute_cancellable_advanced_analysis", execute)
    try:
        state = manager.start(_power_spec())
        deadline = time.monotonic() + 3
        while repository.get_advanced_job(state["id"])["status"] != "succeeded":
            if time.monotonic() >= deadline:
                raise TimeoutError("advanced job did not complete")
            time.sleep(0.01)

        completed = manager.get(state["id"])
        assert completed["status"] == "succeeded"
        assert completed["stage"] == "succeeded"
        assert completed["progress"] == 1.0
        assert completed["resultPath"].endswith("result.json")
        assert manager.get_result(state["id"]) == {"familyResult": {"solvedValue": 77}}
        assert not (
            settings.state_root / "projects" / "default" / "runs" / state["id"] / "work"
        ).exists()
    finally:
        manager.close()


def test_job_failure_and_queued_cancellation_are_terminal_and_observable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    repository = _Repository(settings)
    manager = AdvancedJobManager(cast(DatasetRepository, repository), settings)
    failed_id = "advanced_failed_unit"
    repository.save_advanced_job(_queued_state(failed_id), Path("unused"))
    monkeypatch.setattr(
        advanced_jobs,
        "execute_cancellable_advanced_analysis",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AdvancedExecutionError("ENGINE_FAILURE", "engine failed", "diagnostic")
        ),
    )
    try:
        manager._run_advanced(
            repository.get_advanced_job(failed_id), _power_spec(), threading.Event()
        )
        failed = manager.get(failed_id)
        assert failed["status"] == "failed"
        assert failed["errorCode"] == "ENGINE_FAILURE"
        assert failed["errorDetails"] == "diagnostic"

        queued_id = "advanced_cancelled_unit"
        repository.save_advanced_job(_queued_state(queued_id), Path("unused"))
        event = threading.Event()
        future = MagicMock()
        future.cancel.return_value = True
        manager.events[queued_id] = event
        manager.futures[queued_id] = future

        cancelled = manager.cancel(queued_id)
        assert cancelled["status"] == "cancelled"
        assert cancelled["cancelRequested"] is True
        assert event.is_set()
        with pytest.raises(ValueError, match="尚未成功完成"):
            manager.get_result(queued_id)
    finally:
        manager.close()


def test_queue_capacity_and_progress_persistence_are_enforced(tmp_path: Path) -> None:
    settings = _settings(tmp_path, queue_capacity=0)
    repository = _Repository(settings)
    manager = AdvancedJobManager(cast(DatasetRepository, repository), settings)
    manager.executor.shutdown(wait=True, cancel_futures=True)
    pending = _PendingFuture()
    manager.executor = MagicMock()
    manager.executor.submit.return_value = pending
    try:
        state = manager.start(_power_spec())
        with pytest.raises(AdvancedQueueFullError, match="队列已满"):
            manager.start(_power_spec())

        repository.save_advanced_job(
            {**repository.get_advanced_job(state["id"]), "status": "running"}, Path("unused")
        )
        progress = manager._progress_callback(state["id"])
        progress({"stage": "estimating", "progress": 0.4})
        observed = manager.get(state["id"])
        assert observed["stage"] == "estimating"
        assert observed["progress"] == 0.4

        manager._closed = True
        with pytest.raises(RuntimeError, match="已经关闭"):
            manager.start(_power_spec())
    finally:
        manager.close()
