from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.repository_errors import MeasurementNotFoundError
from app.services.repository_io import (
    UnsafePathError,
    _read_json_safe,
    resolve_owned_path,
    safe_identifier,
)


class MeasurementRepositoryMixin:
    def _load_measurement_definition(
        self, dataset_id: str, version: int, value: object
    ) -> dict[str, Any]:
        safe_identifier(dataset_id, label="dataset id")
        try:
            path = resolve_owned_path(
                self.settings.state_root,
                value,
                label="measurement definition path",
                expected_parent=self.settings.state_root
                / "projects"
                / "default"
                / "datasets"
                / dataset_id
                / "measurement"
                / f"v{version}",
                expected_name="measurement.json",
            )
            measurement = _read_json_safe(path)
        except (UnsafePathError, OSError, json.JSONDecodeError) as error:
            raise MeasurementNotFoundError(
                f"测量版本文件引用不安全或损坏: {dataset_id} v{version}"
            ) from error
        derived = measurement.get("derivedDataset", {})
        if (
            measurement.get("datasetVersionId") != dataset_id
            or measurement.get("version") != version
            or derived.get("sourceDatasetVersionId") != dataset_id
            or derived.get("measurementVersion") != version
        ):
            raise MeasurementNotFoundError(f"测量版本文件身份不匹配: {dataset_id} v{version}")
        return measurement

    def next_measurement_version(self, dataset_id: str) -> int:
        self._dataset_row(dataset_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM measurement_versions WHERE dataset_id = ?",
                (dataset_id,),
            ).fetchone()
        return int(row["version"]) + 1

    def record_measurement(
        self,
        dataset_id: str,
        version: int,
        created_at: str,
        definition_path: Path,
        derived_path: Path,
        construct_count: int,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO measurement_versions (
                    dataset_id, version, created_at, definition_path,
                    derived_path, construct_count
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_id,
                    version,
                    created_at,
                    definition_path.relative_to(self.settings.state_root).as_posix(),
                    derived_path.relative_to(self.settings.state_root).as_posix(),
                    construct_count,
                ),
            )
        if hasattr(self, "_clear_caches"):
            self._clear_caches(dataset_id)

    def get_measurement(self, dataset_id: str, version: int | None = None) -> dict[str, Any]:
        cache_key = (dataset_id, version)
        if hasattr(self, "_measurement_cache") and cache_key in self._measurement_cache:
            return self._measurement_cache[cache_key]

        self._dataset_row(dataset_id)
        query = (
            "SELECT definition_path, version FROM measurement_versions "
            "WHERE dataset_id = ? AND version = ?"
            if version is not None
            else "SELECT definition_path, version FROM measurement_versions WHERE dataset_id = ? ORDER BY version DESC LIMIT 1"
        )
        parameters: tuple[Any, ...] = (
            (dataset_id, version) if version is not None else (dataset_id,)
        )
        with self._connect() as connection:
            row = connection.execute(query, parameters).fetchone()
        if row is None:
            requested = f" v{version}" if version is not None else ""
            raise MeasurementNotFoundError(f"数据集 {dataset_id} 尚无测量版本{requested}")
        resolved_version = int(row["version"])
        measurement = self._load_measurement_definition(
            dataset_id, resolved_version, row["definition_path"]
        )
        if hasattr(self, "_measurement_cache"):
            self._measurement_cache[cache_key] = measurement
        return measurement

    def get_measurement_for_derived(
        self, dataset_id: str, derived_dataset_id: str
    ) -> dict[str, Any]:
        cache_key = (dataset_id, derived_dataset_id)
        if (
            hasattr(self, "_derived_measurement_cache")
            and cache_key in self._derived_measurement_cache
        ):
            return self._derived_measurement_cache[cache_key]

        self._dataset_row(dataset_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT definition_path, version FROM measurement_versions WHERE dataset_id = ? ORDER BY version DESC",
                (dataset_id,),
            ).fetchall()
        for row in rows:
            measurement = self._load_measurement_definition(
                dataset_id, int(row["version"]), row["definition_path"]
            )
            if measurement["derivedDataset"]["id"] == derived_dataset_id:
                if hasattr(self, "_derived_measurement_cache"):
                    self._derived_measurement_cache[cache_key] = measurement
                return measurement
        raise MeasurementNotFoundError(f"派生数据版本不存在: {derived_dataset_id}")
