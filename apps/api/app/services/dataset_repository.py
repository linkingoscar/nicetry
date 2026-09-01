from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from app.services.analysis_context_repository import AnalysisContextRepositoryMixin
from app.services.analysis_draft_repository import AnalysisDraftRepositoryMixin
from app.services.analysis_repository import AnalysisRepositoryMixin
from app.services.data_quality_repository import DataQualityRepositoryMixin
from app.services.database_migrations import initialize_database
from app.services.imputation_plan_repository import ImputationPlanRepositoryMixin
from app.services.measurement_repository import MeasurementRepositoryMixin
from app.services.model_repository import ModelRepositoryMixin
from app.services.repository_errors import (
    DatasetNotFoundError,
    DictionaryUpdateError,
    MeasurementNotFoundError,
    ModelDraftNotFoundError,
    ModelVersionNotFoundError,
)
from app.services.repository_io import (
    UnsafePathError,
    _utc_now,
    _write_json_atomic,
    resolve_owned_path,
)
from app.services.study_context_repository import StudyContextRepositoryMixin
from app.services.study_plan_repository import StudyPlanRepositoryMixin
from app.settings import Settings

__all__ = [
    "DatasetRepository",
    "DatasetNotFoundError",
    "DictionaryUpdateError",
    "MeasurementNotFoundError",
    "ModelDraftNotFoundError",
    "ModelVersionNotFoundError",
    "_write_json_atomic",
]


class DatasetRepository(
    MeasurementRepositoryMixin,
    ModelRepositoryMixin,
    AnalysisRepositoryMixin,
    DataQualityRepositoryMixin,
    AnalysisContextRepositoryMixin,
    AnalysisDraftRepositoryMixin,
    ImputationPlanRepositoryMixin,
    StudyPlanRepositoryMixin,
    StudyContextRepositoryMixin,
):
    _precheck_cache: dict[tuple[str, int, str], dict[str, Any]] = {}
    _model_variables_cache: dict[tuple[str, int, str, int], dict[str, dict[str, Any]]] = {}

    @classmethod
    def get_precheck_cache_item(cls, key: tuple[str, int, str]) -> dict[str, Any] | None:
        return cls._precheck_cache.get(key)

    @classmethod
    def set_precheck_cache_item(cls, key: tuple[str, int, str], value: dict[str, Any]) -> None:
        cls._precheck_cache[key] = value

    @classmethod
    def clear_precheck_cache(cls) -> None:
        cls._precheck_cache.clear()

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database_path = settings.state_root / "metadata.sqlite3"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._dataset_cache: dict[str, dict[str, Any]] = {}
        self._measurement_cache: dict[tuple[str, int | None], dict[str, Any]] = {}
        self._derived_measurement_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self._variable_map_cache: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
        self._initialize()

    def _clear_caches(self, dataset_id: str | None = None) -> None:
        DatasetRepository.clear_precheck_cache()
        DatasetRepository._model_variables_cache.clear()
        if dataset_id is None:
            self._dataset_cache.clear()
            self._measurement_cache.clear()
            self._derived_measurement_cache.clear()
            self._variable_map_cache.clear()
        else:
            self._dataset_cache.pop(dataset_id, None)

            m_keys = [k for k in self._measurement_cache if k[0] == dataset_id]
            for k in m_keys:
                self._measurement_cache.pop(k, None)

            dm_keys = [k for k in self._derived_measurement_cache if k[0] == dataset_id]
            for k in dm_keys:
                self._derived_measurement_cache.pop(k, None)

            v_keys = [k for k in self._variable_map_cache if k[0] == dataset_id]
            for k in v_keys:
                self._variable_map_cache.pop(k, None)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            initialize_database(connection)

    def record_dataset(self, manifest: dict[str, Any], manifest_path: Path) -> None:
        relative_manifest = manifest_path.relative_to(self.settings.state_root).as_posix()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO dataset_versions (
                    id, project_id, created_at, original_name, file_format,
                    sha256, manifest_path, row_count, column_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    manifest["id"],
                    manifest["projectId"],
                    manifest["createdAt"],
                    manifest["originalFile"]["name"],
                    manifest["originalFile"]["format"],
                    manifest["originalFile"]["sha256"],
                    relative_manifest,
                    manifest["rowCount"],
                    manifest["columnCount"],
                ),
            )
        self._clear_caches(manifest["id"])

    def _dataset_row(self, dataset_id: str) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM dataset_versions WHERE id = ?", (dataset_id,)
            ).fetchone()
        if row is None:
            raise DatasetNotFoundError(f"DatasetVersion 不存在: {dataset_id}")
        return row

    def get_dataset(self, dataset_id: str) -> dict[str, Any]:
        if dataset_id in self._dataset_cache:
            return self._dataset_cache[dataset_id]

        row = self._dataset_row(dataset_id)
        try:
            dataset_root = (
                self.settings.state_root / "projects" / "default" / "datasets" / dataset_id
            )
            manifest_path = resolve_owned_path(
                self.settings.state_root,
                row["manifest_path"],
                label="dataset manifest path",
                expected_parent=dataset_root,
                expected_name="manifest.json",
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (UnsafePathError, OSError, json.JSONDecodeError) as error:
            raise DatasetNotFoundError(
                f"DatasetVersion 文件引用不安全或损坏: {dataset_id}"
            ) from error
        if manifest.get("id") != dataset_id:
            raise DatasetNotFoundError(f"DatasetVersion 文件身份不匹配: {dataset_id}")

        confirmed: dict[str, str] = {}
        dictionary_version = int(row["current_dictionary_version"])
        if dictionary_version > 0:
            with self._connect() as connection:
                dictionary_row = connection.execute(
                    "SELECT path FROM dictionary_versions WHERE dataset_id = ? AND version = ?",
                    (dataset_id, dictionary_version),
                ).fetchone()
            if dictionary_row is not None:
                try:
                    dictionary_path = resolve_owned_path(
                        self.settings.state_root,
                        dictionary_row["path"],
                        label="dictionary path",
                        expected_parent=dataset_root / "dictionary",
                        expected_name=f"v{dictionary_version}.json",
                    )
                    dictionary = json.loads(dictionary_path.read_text(encoding="utf-8"))
                except (UnsafePathError, OSError, json.JSONDecodeError) as error:
                    raise DatasetNotFoundError(
                        f"Dictionary 文件引用不安全或损坏: {dataset_id}"
                    ) from error
                if (
                    dictionary.get("datasetVersionId") != dataset_id
                    or int(dictionary.get("version", -1)) != dictionary_version
                ):
                    raise DatasetNotFoundError(f"Dictionary 文件身份不匹配: {dataset_id}")
                confirmed = dictionary["confirmedTypes"]

        variables = []
        for variable in manifest["variables"]:
            merged = dict(variable)
            merged["confirmedType"] = confirmed.get(variable["id"])
            variables.append(merged)

        confirmed_count = sum(variable["confirmedType"] is not None for variable in variables)
        response = dict(manifest)
        response["variables"] = variables
        response["dictionary"] = {
            "version": dictionary_version,
            "confirmedCount": confirmed_count,
            "totalCount": len(variables),
            "status": "confirmed" if confirmed_count == len(variables) else "draft",
        }
        self._dataset_cache[dataset_id] = response
        return response

    def get_dataset_data_path(self, dataset_id: str) -> Path:
        dataset = self.get_dataset(dataset_id)
        dataset_root = self.settings.state_root / "projects" / "default" / "datasets" / dataset_id
        storage = dataset.get("storage")
        if not isinstance(storage, dict) or not isinstance(storage.get("normalized"), str):
            raise DatasetNotFoundError(f"DatasetVersion 缺少规范化数据路径: {dataset_id}")
        return resolve_owned_path(
            self.settings.state_root,
            storage["normalized"],
            label="dataset normalized path",
            expected_parent=dataset_root / "normalized",
            expected_name="data.parquet",
        )

    def confirm_dictionary(self, dataset_id: str, updates: dict[str, str]) -> dict[str, Any]:
        dataset = self.get_dataset(dataset_id)
        known_ids = {variable["id"] for variable in dataset["variables"]}
        unknown_ids = sorted(set(updates) - known_ids)
        if unknown_ids:
            raise DictionaryUpdateError("未知变量 ID: " + ", ".join(unknown_ids))

        confirmed = {
            variable["id"]: variable["confirmedType"]
            for variable in dataset["variables"]
            if variable["confirmedType"] is not None
        }
        confirmed.update(updates)
        row = self._dataset_row(dataset_id)
        next_version = int(row["current_dictionary_version"]) + 1
        dictionary = {
            "schemaVersion": "1.0.0",
            "datasetVersionId": dataset_id,
            "version": next_version,
            "createdAt": _utc_now(),
            "confirmedTypes": confirmed,
        }
        relative_path = (
            Path("projects")
            / "default"
            / "datasets"
            / dataset_id
            / "dictionary"
            / f"v{next_version}.json"
        )
        absolute_path = self.settings.state_root / relative_path
        _write_json_atomic(absolute_path, dictionary)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO dictionary_versions (
                    dataset_id, version, created_at, path, confirmed_count
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    dataset_id,
                    next_version,
                    dictionary["createdAt"],
                    relative_path.as_posix(),
                    len(confirmed),
                ),
            )
            connection.execute(
                "UPDATE dataset_versions SET current_dictionary_version = ? WHERE id = ?",
                (next_version, dataset_id),
            )
        self._clear_caches(dataset_id)
        return self.get_dataset(dataset_id)

    def execute_dataset_merge(
        self,
        primary_dataset_id: str,
        target_dataset_id: str,
        subject_key: str,
        wave_key: str | None = None,
    ) -> tuple[dict[str, object], dict[str, object]]:
        from app.services.dataset_import import preview_dataset, profile_variables, utc_now_iso
        from app.services.dataset_merge import merge_datasets

        primary = self.get_dataset(primary_dataset_id)
        target = self.get_dataset(target_dataset_id)

        primary_path = self.get_dataset_data_path(primary_dataset_id)
        target_path = self.get_dataset_data_path(target_dataset_id)

        primary_df = pd.read_parquet(primary_path)
        target_df = pd.read_parquet(target_path)

        merged_df, summary = merge_datasets(
            primary_df,
            target_df,
            subject_key,
            wave_key,
        )

        new_dataset_id = f"dataset_{uuid.uuid4().hex[:16]}"
        dataset_root = (
            self.settings.state_root / "projects" / "default" / "datasets" / new_dataset_id
        )
        raw_path = dataset_root / "raw" / "source.csv"
        normalized_path = dataset_root / "normalized" / "data.parquet"
        manifest_path = dataset_root / "manifest.json"

        raw_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_path.parent.mkdir(parents=True, exist_ok=True)

        merged_df.to_csv(raw_path, index=False, encoding="utf-8")
        merged_df.to_parquet(normalized_path, index=False, engine="pyarrow")
        os.chmod(raw_path, stat.S_IREAD)

        raw_bytes = raw_path.read_bytes()
        size_bytes = len(raw_bytes)
        sha256 = hashlib.sha256(raw_bytes).hexdigest()

        format_metadata = {
            "labels": {
                **primary.get("dictionary", {}).get("labels", {}),
                **target.get("dictionary", {}).get("labels", {}),
            },
            "valueLabels": {
                **primary.get("dictionary", {}).get("valueLabels", {}),
                **target.get("dictionary", {}).get("valueLabels", {}),
            },
        }

        warnings_list = summary.get("warnings", [])
        if not isinstance(warnings_list, list):
            warnings_list = []

        manifest = {
            "schemaVersion": "1.0.0",
            "id": new_dataset_id,
            "projectId": "default",
            "createdAt": utc_now_iso(),
            "originalFile": {
                "name": f"Merged: {primary['originalFile']['name']} + {target['originalFile']['name']}",
                "format": "csv",
                "sizeBytes": size_bytes,
                "sha256": sha256,
            },
            "storage": {
                "raw": raw_path.relative_to(self.settings.state_root).as_posix(),
                "normalized": normalized_path.relative_to(self.settings.state_root).as_posix(),
            },
            "rowCount": int(merged_df.shape[0]),
            "columnCount": int(merged_df.shape[1]),
            "variables": profile_variables(merged_df, format_metadata),
            "preview": preview_dataset(merged_df),
            "warnings": [
                {"code": "IMPORT_NOTE", "severity": "warning", "message": str(message)}
                for message in warnings_list
            ],
            "lineage": {
                "operation": "outer_merge",
                "sources": [
                    {
                        "datasetVersionId": primary["id"],
                        "sha256": primary["originalFile"]["sha256"],
                    },
                    {
                        "datasetVersionId": target["id"],
                        "sha256": target["originalFile"]["sha256"],
                    },
                ],
                "subjectKey": subject_key,
                "waveKey": wave_key,
                "joinType": summary.get("joinType", "outer"),
                "joinKeys": summary.get("joinKeys", []),
                "reportSha256": hashlib.sha256(
                    json.dumps(summary, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest(),
            },
        }

        _write_json_atomic(manifest_path, manifest)
        self.record_dataset(manifest, manifest_path)
        new_dataset = self.get_dataset(new_dataset_id)
        return new_dataset, summary
