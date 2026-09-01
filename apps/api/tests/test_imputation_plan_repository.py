from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

from app.services.dataset_repository import DatasetRepository
from app.settings import get_settings


def _repository(tmp_path: Path) -> DatasetRepository:
    return DatasetRepository(replace(get_settings(), state_root=tmp_path / "state"))


def _insert_dataset_row(repository: DatasetRepository, dataset_id: str) -> None:
    with sqlite3.connect(repository.database_path) as connection:
        connection.execute(
            """
            INSERT INTO dataset_versions (
                id, project_id, created_at, original_name, file_format,
                sha256, manifest_path, row_count, column_count,
                current_dictionary_version
            ) VALUES (?, 'default', '2026-08-16', 'input.csv', 'csv', ?, ?, 2, 2, 0)
            """,
            (dataset_id, "a" * 64, f"projects/default/datasets/{dataset_id}/manifest.json"),
        )


def _insert_advanced_job_row(repository: DatasetRepository, job_id: str) -> None:
    with sqlite3.connect(repository.database_path) as connection:
        connection.execute(
            """
            INSERT INTO advanced_analysis_jobs (
                id, analysis_id, family, spec_hash, dataset_version_id,
                status, stage, progress, cancel_requested, created_at,
                updated_at, state_path, result_path
            ) VALUES (?, 'analysis_a', 'power_analysis', 'hash_a', NULL,
                      'succeeded', 'succeeded', 1.0, 0, '2026-08-16',
                      '2026-08-16', ?, NULL)
            """,
            (job_id, f"projects/default/runs/{job_id}/state.json"),
        )


def _payload() -> dict[str, object]:
    return {
        "schemaVersion": "1.0.0",
        "datasetVersionId": "dataset_a",
        "datasetSha256": "a" * 64,
        "contextHash": "b" * 64,
        "sampleVersionId": "sample_v1",
        "sampleHash": "c" * 64,
        "measurementVersionId": "measurement_v1",
        "measurementHash": "d" * 64,
        "structureVersionId": "structure_v1",
        "structureHash": "e" * 64,
        "substantiveModel": {"modelId": "model_a"},
        "variables": [{"variableId": "var_1"}],
        "passiveRules": [],
        "imputations": 5,
        "iterations": 10,
        "seed": 20260714,
        "diagnostics": [],
        "predictorMatrixHash": "f" * 64,
        "substantiveModelHash": "g" * 64,
    }


def test_save_list_and_idempotent_imputation_plan(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _insert_dataset_row(repository, "dataset_a")
    plan_hash = "h" * 64
    first = repository.save_imputation_plan(
        "dataset_a",
        None,
        "b" * 64,
        "c" * 64,
        "g" * 64,
        plan_hash,
        _payload(),
    )
    first_id = str(first["id"])
    assert first_id == "imputation_plan_" + plan_hash[:32]
    assert first["sampleVersionId"] == "sample_v1"
    assert first["imputations"] == 5

    second = repository.save_imputation_plan(
        "dataset_a",
        None,
        "b" * 64,
        "c" * 64,
        "g" * 64,
        plan_hash,
        _payload(),
    )
    assert str(second["id"]) == first_id
    assert repository.get_imputation_plan(first_id) == first
    assert [plan["id"] for plan in repository.list_imputation_plans("dataset_a")] == [
        first_id
    ]
    assert repository.get_imputation_plan("missing_plan") is None


def test_imputation_dataset_version_round_trip(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _insert_dataset_row(repository, "dataset_a")
    _insert_advanced_job_row(repository, "job_a")
    plan = repository.save_imputation_plan(
        "dataset_a",
        None,
        "b" * 64,
        "c" * 64,
        "g" * 64,
        "h" * 64,
        _payload(),
    )
    plan_id = str(plan["id"])
    result: dict[str, object] = {"familyResult": {"artifacts": [{"imputation": 1}]}}
    version_id = repository.save_imputation_dataset_version(plan_id, "job_a", result)
    assert version_id == repository.imputation_dataset_id(plan_id, "job_a")

    stored = repository.get_imputation_dataset_version(version_id)
    assert stored is not None
    assert stored["imputationPlanVersionId"] == plan_id
    assert stored["jobId"] == "job_a"
    assert stored["status"] == "ready"
    assert repository.get_imputation_dataset_plan_id(version_id) == plan_id
    assert repository.get_imputation_dataset_version("missing") is None
    assert repository.get_imputation_dataset_plan_id("missing") is None


def test_save_imputation_dataset_version_tolerates_missing_artifacts(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    _insert_dataset_row(repository, "dataset_a")
    _insert_advanced_job_row(repository, "job_b")
    plan = repository.save_imputation_plan(
        "dataset_a",
        None,
        "b" * 64,
        "c" * 64,
        "g" * 64,
        "h" * 64,
        _payload(),
    )
    plan_id = str(plan["id"])
    version_id = repository.save_imputation_dataset_version(plan_id, "job_b", {})
    stored = repository.get_imputation_dataset_version(version_id)
    assert stored is not None
    assert stored["artifactManifestPath"] == (
        "projects/default/runs/job_b/imputation-manifest.json"
    )
