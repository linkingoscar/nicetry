from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.repository_errors import ModelDraftNotFoundError, ModelVersionNotFoundError
from app.services.repository_io import (
    UnsafePathError,
    _read_json_safe,
    resolve_owned_path,
    safe_identifier,
)


class ModelRepositoryMixin:
    def record_model_draft(
        self,
        dataset_id: str,
        model_id: str,
        updated_at: str,
        path: Path,
        model_hash: str,
    ) -> None:
        relative_path = path.relative_to(self.settings.state_root).as_posix()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO model_drafts (model_id, dataset_id, updated_at, path, model_hash)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(model_id) DO UPDATE SET
                    dataset_id = excluded.dataset_id,
                    updated_at = excluded.updated_at,
                    path = excluded.path,
                    model_hash = excluded.model_hash
                """,
                (model_id, dataset_id, updated_at, relative_path, model_hash),
            )

    def get_model_draft(self, dataset_id: str, model_id: str) -> dict[str, Any]:
        safe_identifier(dataset_id, label="dataset id")
        safe_identifier(model_id, label="model id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT path, model_hash FROM model_drafts WHERE model_id = ? AND dataset_id = ?",
                (model_id, dataset_id),
            ).fetchone()
        if row is None:
            raise ModelDraftNotFoundError(f"模型草稿不存在: {model_id}")
        try:
            path = resolve_owned_path(
                self.settings.state_root,
                row["path"],
                label="model draft path",
                expected_parent=self.settings.state_root
                / "projects"
                / "default"
                / "models"
                / model_id,
                expected_name="draft.json",
            )
            draft = _read_json_safe(path)
        except (UnsafePathError, OSError, json.JSONDecodeError) as error:
            raise ModelDraftNotFoundError(f"模型草稿文件引用不安全或损坏: {model_id}") from error
        if (
            draft.get("datasetId") != dataset_id
            or draft.get("modelId") != model_id
            or draft.get("modelHash") != row["model_hash"]
            or draft.get("modelSpec", {}).get("modelId") != model_id
        ):
            raise ModelDraftNotFoundError(f"模型草稿文件身份不匹配: {model_id}")
        return draft

    def next_model_version(self, model_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM model_versions WHERE model_id = ?",
                (model_id,),
            ).fetchone()
        return int(row["version"]) + 1

    def record_model_version(
        self,
        dataset_id: str,
        model_id: str,
        version: int,
        created_at: str,
        path: Path,
        model_hash: str,
        override_reason: str | None,
    ) -> None:
        relative_path = path.relative_to(self.settings.state_root).as_posix()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO model_versions (
                    model_id, version, dataset_id, created_at, path,
                    model_hash, override_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model_id,
                    version,
                    dataset_id,
                    created_at,
                    relative_path,
                    model_hash,
                    override_reason,
                ),
            )

    def get_model_version(self, model_id: str, version: int) -> dict[str, Any]:
        safe_identifier(model_id, label="model id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT path, dataset_id, model_hash FROM model_versions WHERE model_id = ? AND version = ?",
                (model_id, version),
            ).fetchone()
        if row is None:
            raise ModelVersionNotFoundError(f"ModelVersion 不存在: {model_id} v{version}")
        try:
            path = resolve_owned_path(
                self.settings.state_root,
                row["path"],
                label="model version path",
                expected_parent=self.settings.state_root
                / "projects"
                / "default"
                / "models"
                / model_id,
                expected_name=f"v{version}.json",
            )
            frozen = _read_json_safe(path)
        except (UnsafePathError, OSError, json.JSONDecodeError) as error:
            raise ModelVersionNotFoundError(
                f"ModelVersion 文件引用不安全或损坏: {model_id} v{version}"
            ) from error
        if (
            frozen.get("datasetId") != row["dataset_id"]
            or frozen.get("modelId") != model_id
            or frozen.get("version") != version
            or frozen.get("modelHash") != row["model_hash"]
            or frozen.get("modelSpec", {}).get("modelId") != model_id
        ):
            raise ModelVersionNotFoundError(f"ModelVersion 文件身份不匹配: {model_id} v{version}")
        return frozen
