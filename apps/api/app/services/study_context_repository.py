from __future__ import annotations

import json
import sqlite3
from typing import cast

from app.services.repository_io import _utc_now
from app.settings import Settings


class StudyContextRepositoryMixin:
    settings: Settings

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def _dataset_row(self, dataset_id: str) -> sqlite3.Row:
        raise NotImplementedError

    def get_dataset(self, dataset_id: str) -> dict[str, object]:
        raise NotImplementedError

    def get_study_context(self, project_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM study_contexts WHERE project_id = ?", (project_id,)
            ).fetchone()
        if row is None:
            return None
        return {
            "schemaVersion": row["schema_version"],
            "projectId": row["project_id"],
            "timeStructure": row["time_structure"],
            "dependenceStructure": row["dependence_structure"],
            "design": row["design"],
            "revision": row["revision"],
            "updatedAt": row["updated_at"],
        }

    def save_study_context(
        self, project_id: str, context: dict[str, object]
    ) -> dict[str, object]:
        updated_at = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO study_contexts (
                    project_id, schema_version, time_structure,
                    dependence_structure, design, revision, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    schema_version = excluded.schema_version,
                    time_structure = excluded.time_structure,
                    dependence_structure = excluded.dependence_structure,
                    design = excluded.design,
                    revision = study_contexts.revision + 1,
                    updated_at = excluded.updated_at
                """,
                (
                    project_id,
                    context["schemaVersion"],
                    context["timeStructure"],
                    context["dependenceStructure"],
                    context["design"],
                    updated_at,
                ),
            )
        saved = self.get_study_context(project_id)
        assert saved is not None
        return saved

    def get_dataset_structure(self, dataset_id: str) -> dict[str, object] | None:
        self._dataset_row(dataset_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM dataset_structures WHERE dataset_version_id = ?", (dataset_id,)
            ).fetchone()
        if row is None:
            return None
        return {
            "datasetVersionId": row["dataset_version_id"],
            "context": json.loads(row["context_json"]),
            "subjectId": row["subject_id"],
            "clusterId": row["cluster_id"],
            "timeId": row["time_id"],
            "revision": row["revision"],
            "updatedAt": row["updated_at"],
        }

    def save_dataset_structure(
        self, dataset_id: str, structure: dict[str, object]
    ) -> dict[str, object]:
        dataset = self.get_dataset(dataset_id)
        variables = cast(list[dict[str, object]], dataset["variables"])
        known_ids = {str(variable["id"]) for variable in variables}
        assigned: dict[str, str] = {
            role: value
            for role, value in {
                "subjectId": structure.get("subjectId"),
                "clusterId": structure.get("clusterId"),
                "timeId": structure.get("timeId"),
            }.items()
            if isinstance(value, str) and value
        }
        unknown = sorted(set(assigned.values()) - known_ids)
        if unknown:
            raise ValueError("DATA_STRUCTURE_UNKNOWN_VARIABLES: " + ", ".join(unknown))
        updated_at = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO dataset_structures (
                    dataset_version_id, context_json, subject_id, cluster_id,
                    time_id, revision, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(dataset_version_id) DO UPDATE SET
                    context_json = excluded.context_json,
                    subject_id = excluded.subject_id,
                    cluster_id = excluded.cluster_id,
                    time_id = excluded.time_id,
                    revision = dataset_structures.revision + 1,
                    updated_at = excluded.updated_at
                """,
                (
                    dataset_id,
                    json.dumps(structure["context"], ensure_ascii=False, sort_keys=True),
                    structure.get("subjectId"),
                    structure.get("clusterId"),
                    structure.get("timeId"),
                    updated_at,
                ),
            )
        saved = self.get_dataset_structure(dataset_id)
        assert saved is not None
        return saved
