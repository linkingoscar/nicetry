from __future__ import annotations

import threading
from dataclasses import replace
from pathlib import Path
from typing import cast

from conftest import _original_get_settings

from app.api.routes.analyses import _progress_event
from app.services.analysis_jobs import AnalysisJobManager
from app.services.dataset_repository import DatasetRepository
from app.services.r_workers import RWorkerPool
from app.settings import Settings, get_settings


class _Repository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def list_unfinished_analysis_jobs(self):
        return []

    def save_analysis_job(self, state, _path: Path):
        return None

    def get_analysis_job(self, run_id: str):
        raise LookupError(f"AnalysisRun 不存在: {run_id}")


def _settings(tmp_path: Path) -> Settings:
    return replace(
        get_settings(),
        state_root=tmp_path / "workspace",
        r_worker_count=1,
        analysis_queue_capacity=1,
    )


def test_progress_event_exposes_only_whitelisted_fields() -> None:
    state = {
        "id": "run_abc",
        "status": "running",
        "stage": "fitting_equations",
        "progress": 0.5,
        "completedReplicates": 10,
        "totalReplicates": 100,
        "error": "C:\\absolute\\internal\\path\\detail",
        "options": {"predictorVariableIds": ["x"]},
        "contextLineage": {"dataset": {"id": "dataset_x"}},
        "resultPath": "projects/default/runs/run_abc/result.json",
        "metadata": {"contextHash": "abc123", "internal": "secret"},
    }
    event = _progress_event(state)
    assert event["id"] == "run_abc"
    assert event["status"] == "running"
    assert event["progress"] == 0.5
    assert event["completedReplicates"] == 10
    assert event["metadata"] == {"contextHash": "abc123"}
    for leaked in ("error", "options", "contextLineage", "resultPath"):
        assert leaked not in event


def test_listener_budget_limits_per_run_and_global(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    repository = _Repository(settings)
    worker_pool = RWorkerPool(settings)
    manager = AnalysisJobManager(
        cast(DatasetRepository, repository), settings, worker_pool, context_service=None
    )
    try:
        first = manager.register_listener("run_a", threading.Event(), None)
        second = manager.register_listener("run_a", threading.Event(), None)
        third = manager.register_listener("run_a", threading.Event(), None)
        assert first is True
        assert second is True
        assert third is False

        manager.unregister_listener("run_a", None)
        assert manager.register_listener("run_b", threading.Event(), None) is True
    finally:
        manager.close()


def test_session_token_env_override(monkeypatch) -> None:
    monkeypatch.setenv("RESEARCHPATH_SESSION_TOKEN", "fixed-session-token")
    assert _original_get_settings().session_token == "fixed-session-token"
    monkeypatch.delenv("RESEARCHPATH_SESSION_TOKEN")
    assert _original_get_settings().session_token != "fixed-session-token"


def test_invalid_environment_integer_falls_back_without_crashing(monkeypatch) -> None:
    monkeypatch.setenv("RESEARCHPATH_R_WORKERS", "not-an-int")
    assert _original_get_settings().r_worker_count == 1
