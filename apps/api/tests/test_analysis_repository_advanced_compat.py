from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from app.services.dataset_repository import DatasetRepository
from app.services.repository_io import UnsafePathError
from app.settings import get_settings


def _repository(tmp_path: Path) -> DatasetRepository:
    return DatasetRepository(replace(get_settings(), state_root=tmp_path / "state"))


def _advanced_state(
    run_id: str,
    *,
    status: str = "queued",
    result_path: str | None = None,
) -> dict[str, object]:
    return {
        "id": run_id,
        "analysisId": "analysis_a",
        "family": "power_analysis",
        "specHash": "hash_a",
        "datasetVersionId": None,
        "status": status,
        "stage": "queued",
        "progress": 0.0,
        "cancelRequested": False,
        "createdAt": "2026-08-16T00:00:00Z",
        "updatedAt": "2026-08-16T00:00:00Z",
        "resultPath": result_path,
    }


def _insert_row(
    repository: DatasetRepository,
    state: dict[str, object],
    state_path: str,
) -> None:
    with sqlite3.connect(repository.database_path) as connection:
        connection.execute(
            """
            INSERT INTO advanced_analysis_jobs (
                id, analysis_id, family, spec_hash, dataset_version_id,
                status, stage, progress, cancel_requested, created_at,
                updated_at, state_path, result_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state["id"],
                state["analysisId"],
                state["family"],
                state["specHash"],
                state.get("datasetVersionId"),
                state["status"],
                state["stage"],
                state["progress"],
                int(bool(state.get("cancelRequested"))),
                state["createdAt"],
                state["updatedAt"],
                state_path,
                state.get("resultPath"),
            ),
        )


def _state_path(repository: DatasetRepository, run_id: str) -> Path:
    return (
        repository.settings.state_root
        / "projects"
        / "default"
        / "runs"
        / run_id
        / "state.json"
    )


def test_save_advanced_job_persists_state_without_inline_result(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run_id = "adv_save"
    path = _state_path(repository, run_id)
    repository.save_advanced_job({**_advanced_state(run_id), "result": {"keep": "no"}}, path)

    assert path.exists()
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["id"] == run_id
    assert stored["result"] is None
    with repository._connect() as connection:
        row = connection.execute(
            "SELECT state_path FROM advanced_analysis_jobs WHERE id = ?", (run_id,)
        ).fetchone()
    assert row is not None
    assert row["state_path"] == path.relative_to(repository.settings.state_root).as_posix()


def test_save_and_get_advanced_job_round_trip(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run_id = "adv_get"
    repository.save_advanced_job(_advanced_state(run_id), _state_path(repository, run_id))
    state = repository.get_advanced_job(run_id)
    assert state["id"] == run_id
    assert state["family"] == "power_analysis"


def test_get_advanced_job_rejects_identity_mismatch(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run_id = "adv_mismatch"
    path = _state_path(repository, run_id)
    state = _advanced_state(run_id)
    state["analysisId"] = "expected_analysis"
    repository.save_advanced_job(state, path)
    stored = {**state, "analysisId": "other_analysis"}
    path.write_text(json.dumps(stored), encoding="utf-8")

    with pytest.raises(LookupError, match="身份不匹配"):
        repository.get_advanced_job(run_id)


def test_get_advanced_job_rejects_unescaped_state_path(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run_id = "adv_escape"
    _insert_row(
        repository,
        _advanced_state(run_id),
        "../outside/state.json",
    )
    with pytest.raises(UnsafePathError):
        repository.get_advanced_job(run_id)


def test_list_unfinished_advanced_jobs_returns_valid_and_skips_corrupt(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    good_id = "adv_good"
    repository.save_advanced_job(_advanced_state(good_id), _state_path(repository, good_id))
    repository.save_advanced_job(_advanced_state("adv_succeeded", status="succeeded"), _state_path(repository, "adv_succeeded"))
    corrupt_id = "adv_corrupt"
    _insert_row(
        repository,
        _advanced_state(corrupt_id),
        "projects/default/runs/adv_corrupt/state.json",
    )

    states = repository.list_unfinished_advanced_jobs()
    assert [state["id"] for state in states] == [good_id]


def test_delete_advanced_job_removes_row_and_run_directory(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run_id = "adv_delete"
    state_path = _state_path(repository, run_id)
    repository.save_advanced_job(_advanced_state(run_id), state_path)

    repository.delete_advanced_job(run_id)
    assert not state_path.exists()
    assert not state_path.parent.exists()
    with repository._connect() as connection:
        row = connection.execute(
            "SELECT id FROM advanced_analysis_jobs WHERE id = ?", (run_id,)
        ).fetchone()
    assert row is None


def test_delete_advanced_job_without_row_is_noop(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    repository.delete_advanced_job("adv_missing")


def test_record_and_get_advanced_result(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run_id = "adv_result"
    result = {"run": {"id": run_id}}
    path = repository.record_advanced_result(run_id, result)
    assert path.name == "result.json"
    assert json.loads(path.read_text(encoding="utf-8")) == result
    _insert_row(
        repository,
        _advanced_state(run_id, status="succeeded", result_path=path.relative_to(
            repository.settings.state_root
        ).as_posix()),
        _state_path(repository, run_id).relative_to(
            repository.settings.state_root
        ).as_posix(),
    )
    assert repository.get_advanced_result(run_id) == result


def test_get_advanced_result_rejects_wrong_identity(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    run_id = "adv_result_mismatch"
    result_path = repository.record_advanced_result(run_id, {"run": {"id": "other"}})
    _insert_row(
        repository,
        _advanced_state(run_id, status="succeeded", result_path=result_path.relative_to(
            repository.settings.state_root
        ).as_posix()),
        _state_path(repository, run_id).relative_to(
            repository.settings.state_root
        ).as_posix(),
    )
    with pytest.raises(LookupError, match="身份不匹配"):
        repository.get_advanced_result(run_id)
