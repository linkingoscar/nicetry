from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from app.contracts import file_sha256
from app.services.dataset_repository import DatasetRepository
from app.services.export_bundle import create_export_bundle
from app.services.owned_resources import (
    resolve_derived_dataset_path,
    resolve_normalized_dataset_path,
)
from app.services.repository_errors import (
    DatasetNotFoundError,
    MeasurementNotFoundError,
    ModelDraftNotFoundError,
    ModelVersionNotFoundError,
)
from app.services.repository_io import UnsafePathError
from app.settings import get_settings


def _repository(tmp_path: Path) -> DatasetRepository:
    return DatasetRepository(replace(get_settings(), state_root=tmp_path / "state"))


def _insert_dataset(
    repository: DatasetRepository,
    dataset_id: str,
    manifest_path: str,
    *,
    dictionary_version: int = 0,
) -> None:
    with repository._connect() as connection:
        connection.execute(
            """
            INSERT INTO dataset_versions (
                id, project_id, created_at, original_name, file_format,
                sha256, manifest_path, row_count, column_count,
                current_dictionary_version
            ) VALUES (?, 'default', '2026-07-15', 'input.csv', 'csv', ?, ?, 1, 1, ?)
            """,
            (dataset_id, "0" * 64, manifest_path, dictionary_version),
        )


def _insert_job(
    repository: DatasetRepository,
    state: dict[str, object],
    state_path: str,
) -> None:
    with sqlite3.connect(repository.database_path) as connection:
        connection.execute(
            """
            INSERT INTO analysis_jobs (
                id, dataset_id, model_id, model_version, status, stage,
                progress, created_at, updated_at, state_path, job_kind,
                cancel_requested, result_path
            ) VALUES (?, ?, ?, ?, ?, ?, 0.5, '2026-07-15', '2026-07-15', ?, ?, 0, ?)
            """,
            (
                state["id"],
                state["datasetId"],
                state["modelId"],
                state["modelVersion"],
                state["status"],
                state["stage"],
                state_path,
                state.get("jobKind", "model"),
                state.get("resultPath"),
            ),
        )


def _insert_advanced_job(
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1.0, 0, '2026-07-15',
                      '2026-07-15', ?, ?)
            """,
            (
                state["id"],
                state["analysisId"],
                state["family"],
                state["specHash"],
                state.get("datasetVersionId"),
                state["status"],
                state["stage"],
                state_path,
                state.get("resultPath"),
            ),
        )


def test_dataset_manifest_cannot_escape_or_impersonate_dataset(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"id": "dataset_a", "variables": []}), encoding="utf-8")
    _insert_dataset(repository, "dataset_a", "../outside.json")

    with pytest.raises(DatasetNotFoundError, match="不安全或损坏"):
        repository.get_dataset("dataset_a")

    with repository._connect() as connection:
        connection.execute("DELETE FROM dataset_versions WHERE id = 'dataset_a'")
    manifest = repository.settings.state_root / "projects/default/datasets/dataset_a/manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"id": "dataset_b", "variables": []}), encoding="utf-8")
    _insert_dataset(
        repository,
        "dataset_a",
        "projects/default/datasets/dataset_a/manifest.json",
    )
    with pytest.raises(DatasetNotFoundError, match="身份不匹配"):
        repository.get_dataset("dataset_a")


def test_dictionary_path_is_bound_to_dataset_version(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    manifest = repository.settings.state_root / "projects/default/datasets/dataset_a/manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"id": "dataset_a", "variables": []}), encoding="utf-8")
    _insert_dataset(
        repository,
        "dataset_a",
        "projects/default/datasets/dataset_a/manifest.json",
        dictionary_version=1,
    )
    victim = (
        repository.settings.state_root / "projects/default/datasets/dataset_b/dictionary/v1.json"
    )
    victim.parent.mkdir(parents=True)
    victim.write_text(
        json.dumps(
            {
                "datasetVersionId": "dataset_a",
                "version": 1,
                "confirmedTypes": {},
            }
        ),
        encoding="utf-8",
    )
    with repository._connect() as connection:
        connection.execute(
            """
            INSERT INTO dictionary_versions
                (dataset_id, version, created_at, path, confirmed_count)
            VALUES ('dataset_a', 1, '2026-07-15',
                    'projects/default/datasets/dataset_b/dictionary/v1.json', 0)
            """
        )

    with pytest.raises(DatasetNotFoundError, match="不安全或损坏"):
        repository.get_dataset("dataset_a")


def test_analysis_result_path_and_payload_are_bound_to_run(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    result = repository.settings.state_root / "projects/default/runs/run_a/result.json"
    result.parent.mkdir(parents=True)
    result.write_text(json.dumps({"run": {"id": "run_b"}}), encoding="utf-8")
    with sqlite3.connect(repository.database_path) as connection:
        connection.execute(
            """
            INSERT INTO analysis_runs
                (id, dataset_id, model_id, model_version, created_at, status, result_path)
            VALUES ('run_a', 'dataset_a', 'model_a', 1, '2026-07-15', 'succeeded',
                    'projects/default/runs/run_a/result.json')
            """
        )

    with pytest.raises(LookupError, match="身份不匹配"):
        repository.get_analysis_result("run_a")

    with sqlite3.connect(repository.database_path) as connection:
        connection.execute(
            "UPDATE analysis_runs SET result_path = '../outside.json' WHERE id = 'run_a'"
        )
    with pytest.raises(UnsafePathError):
        repository.get_analysis_result("run_a")


def test_job_state_and_recovery_are_bound_to_database_identity(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    state = {
        "id": "run_a",
        "datasetId": "dataset_a",
        "modelId": "model_a",
        "modelVersion": 1,
        "jobKind": "model",
        "status": "running",
        "stage": "running",
        "resultPath": None,
    }
    path = repository.settings.state_root / "projects/default/runs/run_a/state.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({**state, "datasetId": "dataset_b"}), encoding="utf-8")
    _insert_job(repository, state, "projects/default/runs/run_a/state.json")

    with pytest.raises(LookupError, match="身份不匹配"):
        repository.get_analysis_job("run_a")
    assert repository.list_unfinished_analysis_jobs() == []

    with sqlite3.connect(repository.database_path) as connection:
        connection.execute(
            "UPDATE analysis_jobs SET state_path = '../outside.json' WHERE id = 'run_a'"
        )
    with pytest.raises(UnsafePathError):
        repository.get_analysis_job("run_a")
    assert repository.list_unfinished_analysis_jobs() == []


def test_empirical_cleanup_rejects_cross_dataset_report_path_before_deletion(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    victim = (
        repository.settings.state_root
        / "projects/default/datasets/dataset_b/measurement/v1/empirical/empirical_victim/report.json"
    )
    victim.parent.mkdir(parents=True)
    victim.write_text("{}", encoding="utf-8")
    state = {
        "id": "run_a",
        "datasetId": "dataset_a",
        "modelId": "__empirical__",
        "modelVersion": 1,
        "jobKind": "empirical",
        "measurementVersion": 1,
        "measurementVersionId": "measurement_a_v1",
        "reportId": "empirical_victim",
        "status": "succeeded",
        "stage": "succeeded",
        "resultPath": "projects/default/datasets/dataset_b/measurement/v1/empirical/empirical_victim/report.json",
    }
    state_path = repository.settings.state_root / "projects/default/runs/run_a/state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    _insert_job(repository, state, "projects/default/runs/run_a/state.json")

    with pytest.raises(UnsafePathError):
        repository.delete_analysis_job_and_run("run_a")

    assert victim.is_file()
    with repository._connect() as connection:
        assert connection.execute("SELECT 1 FROM analysis_jobs WHERE id = 'run_a'").fetchone()


def test_export_rejects_result_path_and_run_identity_before_writing(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    unsafe_state = {
        "id": "run_a",
        "status": "succeeded",
        "result": None,
        "resultPath": "../outside.json",
    }
    with pytest.raises(ValueError, match="引用不安全"):
        create_export_bundle(
            "run_a", unsafe_state, repository, repository.settings, include_data=False
        )

    mismatched = {
        "id": "run_a",
        "status": "succeeded",
        "result": {"run": {"id": "run_b"}},
        "resultPath": None,
    }
    with pytest.raises(ValueError, match="结果身份"):
        create_export_bundle(
            "run_a", mismatched, repository, repository.settings, include_data=False
        )
    assert not (repository.settings.state_root / "projects/default/runs/run_a/exports").exists()


def test_export_rejects_unsafe_run_id_before_writing(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    with pytest.raises(ValueError, match="标识不安全"):
        create_export_bundle(
            "../run_a",
            {"id": "../run_a", "status": "succeeded", "result": {}},
            repository,
            repository.settings,
            include_data=False,
        )

    assert not (repository.settings.state_root / "projects/default/runs").exists()


def test_job_result_path_allows_atomic_transition_but_stays_owned(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    state = {
        "id": "run_a",
        "datasetId": "dataset_a",
        "modelId": "model_a",
        "modelVersion": 1,
        "jobKind": "model",
        "status": "running",
        "stage": "persisting",
        "resultPath": "projects/default/runs/run_a/result.json",
    }
    state_path = repository.settings.state_root / "projects/default/runs/run_a/state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    database_state = {**state, "resultPath": None}
    _insert_job(repository, database_state, "projects/default/runs/run_a/state.json")

    assert repository.get_analysis_job("run_a")["resultPath"] == state["resultPath"]

    state_path.write_text(
        json.dumps({**state, "resultPath": "projects/default/runs/run_b/result.json"}),
        encoding="utf-8",
    )
    with pytest.raises(UnsafePathError):
        repository.get_analysis_job("run_a")


def test_advanced_result_is_readable_during_state_database_commit_transition(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    run_id = "advanced_a"
    result_path = f"projects/default/runs/{run_id}/result.json"
    state = {
        "id": run_id,
        "analysisId": "advanced_analysis_a",
        "family": "power_analysis",
        "specHash": "advanced_hash_a",
        "datasetVersionId": None,
        "status": "succeeded",
        "stage": "succeeded",
        "resultPath": result_path,
    }
    state_path = repository.settings.state_root / f"projects/default/runs/{run_id}/state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (state_path.parent / "result.json").write_text(
        json.dumps({"run": {"id": run_id}}), encoding="utf-8"
    )
    # This is the legitimate interval after the state file has been atomically
    # published and before its SQLite result_path update is committed.
    _insert_advanced_job(
        repository,
        {**state, "resultPath": None},
        f"projects/default/runs/{run_id}/state.json",
    )

    assert repository.get_advanced_job(run_id)["status"] == "succeeded"
    assert repository.get_advanced_result(run_id) == {"run": {"id": run_id}}


def test_model_files_are_bound_to_database_path_and_identity(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _insert_dataset(repository, "dataset_a", "projects/default/datasets/dataset_a/manifest.json")
    model_dir = repository.settings.state_root / "projects/default/models/model_a"
    model_dir.mkdir(parents=True)
    draft = {
        "datasetId": "dataset_a",
        "modelId": "model_a",
        "modelHash": "hash_a",
        "modelSpec": {"modelId": "model_a"},
    }
    (model_dir / "draft.json").write_text(json.dumps(draft), encoding="utf-8")
    frozen = {**draft, "version": 1}
    (model_dir / "v1.json").write_text(json.dumps(frozen), encoding="utf-8")
    with repository._connect() as connection:
        connection.execute(
            "INSERT INTO model_drafts VALUES (?, ?, ?, ?, ?)",
            (
                "model_a",
                "dataset_a",
                "2026-07-15",
                "projects/default/models/model_a/draft.json",
                "hash_a",
            ),
        )
        connection.execute(
            "INSERT INTO model_versions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "model_a",
                1,
                "dataset_a",
                "2026-07-15",
                "projects/default/models/model_a/v1.json",
                "hash_a",
                None,
            ),
        )

    assert repository.get_model_draft("dataset_a", "model_a")["modelHash"] == "hash_a"
    assert repository.get_model_version("model_a", 1)["version"] == 1

    with repository._connect() as connection:
        connection.execute("UPDATE model_drafts SET path = '../draft.json'")
        connection.execute("UPDATE model_versions SET model_hash = 'other'")
    with pytest.raises(ModelDraftNotFoundError, match="不安全或损坏"):
        repository.get_model_draft("dataset_a", "model_a")
    with pytest.raises(ModelVersionNotFoundError, match="身份不匹配"):
        repository.get_model_version("model_a", 1)


def test_measurement_and_dataset_storage_are_owned_and_digest_bound(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    dataset_dir = repository.settings.state_root / "projects/default/datasets/dataset_a"
    dataset_dir.mkdir(parents=True)
    manifest_path = dataset_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"id": "dataset_a", "variables": []}), encoding="utf-8")
    _insert_dataset(repository, "dataset_a", "projects/default/datasets/dataset_a/manifest.json")
    normalized = dataset_dir / "normalized/data.parquet"
    normalized.parent.mkdir()
    normalized.write_bytes(b"normalized")
    measurement_dir = dataset_dir / "measurement/v1"
    measurement_dir.mkdir(parents=True)
    derived = measurement_dir / "derived.parquet"
    derived.write_bytes(b"derived")
    measurement = {
        "datasetVersionId": "dataset_a",
        "version": 1,
        "derivedDataset": {
            "id": "derived_a",
            "sourceDatasetVersionId": "dataset_a",
            "measurementVersion": 1,
            "storage": "projects/default/datasets/dataset_a/measurement/v1/derived.parquet",
            "sha256": file_sha256(derived),
        },
    }
    definition = measurement_dir / "measurement.json"
    definition.write_text(json.dumps(measurement), encoding="utf-8")
    with repository._connect() as connection:
        connection.execute(
            "INSERT INTO measurement_versions VALUES (?, ?, ?, ?, ?, ?)",
            (
                "dataset_a",
                1,
                "2026-07-15",
                "projects/default/datasets/dataset_a/measurement/v1/measurement.json",
                "projects/default/datasets/dataset_a/measurement/v1/derived.parquet",
                0,
            ),
        )

    loaded = repository.get_measurement("dataset_a", 1)
    assert (
        resolve_normalized_dataset_path(
            repository.settings.state_root,
            {
                "id": "dataset_a",
                "storage": {
                    "normalized": "projects/default/datasets/dataset_a/normalized/data.parquet"
                },
            },
        )
        == normalized
    )
    assert resolve_derived_dataset_path(repository.settings.state_root, loaded) == derived

    derived.write_bytes(b"tampered")
    with pytest.raises(UnsafePathError, match="digest"):
        resolve_derived_dataset_path(repository.settings.state_root, loaded)
    with repository._connect() as connection:
        connection.execute(
            "UPDATE measurement_versions SET definition_path = '../measurement.json'"
        )
    repository._clear_caches("dataset_a")
    with pytest.raises(MeasurementNotFoundError, match="不安全或损坏"):
        repository.get_measurement("dataset_a", 1)
