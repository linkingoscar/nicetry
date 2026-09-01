from __future__ import annotations

from pathlib import Path
from typing import Any

from app.contracts import file_sha256
from app.services.repository_io import (
    UnsafePathError,
    resolve_owned_path,
    safe_identifier,
)


def resolve_normalized_dataset_path(state_root: Path, dataset: dict[str, Any]) -> Path:
    dataset_id = safe_identifier(dataset.get("id"), label="dataset id")
    storage = dataset.get("storage")
    if not isinstance(storage, dict):
        raise UnsafePathError("dataset storage is invalid")
    path = resolve_owned_path(
        state_root,
        storage.get("normalized"),
        label="normalized dataset path",
        expected_parent=state_root
        / "projects"
        / "default"
        / "datasets"
        / dataset_id
        / "normalized",
        expected_name="data.parquet",
    )
    if not path.is_file():
        raise UnsafePathError("normalized dataset file is missing")
    return path


def resolve_derived_dataset_path(
    state_root: Path, measurement: dict[str, Any], *, verify_digest: bool = True
) -> Path:
    dataset_id = safe_identifier(measurement.get("datasetVersionId"), label="dataset id")
    version = measurement.get("version")
    derived = measurement.get("derivedDataset")
    if not isinstance(version, int) or version < 1 or not isinstance(derived, dict):
        raise UnsafePathError("measurement identity is invalid")
    if (
        derived.get("sourceDatasetVersionId") != dataset_id
        or derived.get("measurementVersion") != version
    ):
        raise UnsafePathError("derived dataset identity does not match its measurement")
    path = resolve_owned_path(
        state_root,
        derived.get("storage"),
        label="derived dataset path",
        expected_parent=state_root
        / "projects"
        / "default"
        / "datasets"
        / dataset_id
        / "measurement"
        / f"v{version}",
        expected_name="derived.parquet",
    )
    if not path.is_file():
        raise UnsafePathError("derived dataset file is missing")
    expected_sha256 = derived.get("sha256")
    if verify_digest and (
        not isinstance(expected_sha256, str) or file_sha256(path) != expected_sha256
    ):
        raise UnsafePathError("derived dataset digest does not match its measurement")
    return path
