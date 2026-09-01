from __future__ import annotations

import json
import sqlite3

from app.services.canonical_identity import canonical_sha256
from app.services.repository_io import _utc_now


class StudyPlanRepositoryMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    @staticmethod
    def _study_plan_response(row: sqlite3.Row) -> dict[str, object]:
        payload = json.loads(row["payload_json"])
        response = dict(payload)
        response.update(
            {
                "id": row["id"],
                "projectId": row["project_id"],
                "revision": row["revision"],
                "status": row["status"],
                "planHash": row["plan_hash"],
                "createdAt": row["created_at"],
            }
        )
        return response

    def get_study_plan(self, plan_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM study_plan_versions WHERE id = ?", (plan_id,)
            ).fetchone()
        return None if row is None else self._study_plan_response(row)

    def _insert_study_plan(
        self,
        connection: sqlite3.Connection,
        project_id: str,
        revision: int,
        payload: dict[str, object],
        created_at: str,
    ) -> dict[str, object]:
        plan_hash = canonical_sha256(payload)
        plan_id = "study_plan_" + canonical_sha256(
            {"projectId": project_id, "revision": revision, "planHash": plan_hash}
        )[:32]
        connection.execute(
            "INSERT INTO study_plan_versions "
            "(id, project_id, revision, status, plan_hash, payload_json, created_at) "
            "VALUES (?, ?, ?, 'draft', ?, ?, ?)",
            (
                plan_id,
                project_id,
                revision,
                plan_hash,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                created_at,
            ),
        )
        row = connection.execute(
            "SELECT * FROM study_plan_versions WHERE id = ?", (plan_id,)
        ).fetchone()
        assert row is not None
        return self._study_plan_response(row)

    def create_study_plan(self, project_id: str, payload: dict[str, object]) -> dict[str, object]:
        with self._connect() as connection:
            latest = connection.execute(
                "SELECT MAX(revision) AS revision FROM study_plan_versions WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            revision = 1 if latest is None or latest["revision"] is None else int(latest["revision"]) + 1
            return self._insert_study_plan(connection, project_id, revision, payload, _utc_now())

    def create_study_plan_revision(
        self, plan_id: str, expected_revision: int, payload: dict[str, object]
    ) -> dict[str, object]:
        with self._connect() as connection:
            current = connection.execute(
                "SELECT * FROM study_plan_versions WHERE id = ?", (plan_id,)
            ).fetchone()
            if current is None:
                raise LookupError("研究计划版本不存在")
            if int(current["revision"]) != expected_revision:
                raise ValueError("REVISION_CONFLICT: 研究计划 revision 已变化")
            return self._insert_study_plan(
                connection,
                str(current["project_id"]),
                expected_revision + 1,
                payload,
                _utc_now(),
            )

    def get_latest_study_plan(self, project_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM study_plan_versions WHERE project_id = ? ORDER BY revision DESC LIMIT 1",
                (project_id,),
            ).fetchone()
        return None if row is None else self._study_plan_response(row)

    def update_study_plan(
        self, plan_id: str, expected_revision: int, payload: dict[str, object]
    ) -> dict[str, object]:
        with self._connect() as connection:
            current = connection.execute(
                "SELECT * FROM study_plan_versions WHERE id = ?", (plan_id,)
            ).fetchone()
            if current is None:
                raise LookupError("研究计划版本不存在")
            if current["status"] == "frozen":
                raise ValueError("STUDY_PLAN_FROZEN: 冻结计划只能创建下一版本")
            if int(current["revision"]) != expected_revision:
                raise ValueError("REVISION_CONFLICT: 研究计划 revision 已变化")
            return self._insert_study_plan(
                connection,
                str(current["project_id"]),
                expected_revision + 1,
                payload,
                _utc_now(),
            )

    def freeze_study_plan(self, plan_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM study_plan_versions WHERE id = ?", (plan_id,)
            ).fetchone()
            if row is None:
                raise LookupError("研究计划版本不存在")
            if row["status"] == "frozen":
                return self._study_plan_response(row)
            connection.execute(
                "UPDATE study_plan_versions SET status = 'frozen' WHERE id = ?", (plan_id,)
            )
            row = connection.execute(
                "SELECT * FROM study_plan_versions WHERE id = ?", (plan_id,)
            ).fetchone()
        assert row is not None
        return self._study_plan_response(row)

    def map_study_plan_dataset(
        self,
        plan_id: str,
        dataset_id: str,
        mapping: dict[str, object],
        status: str,
    ) -> dict[str, object]:
        mapping_hash = canonical_sha256(mapping)
        mapping_id = "mapping_" + canonical_sha256(
            {"studyPlanVersionId": plan_id, "datasetVersionId": dataset_id, "mappingHash": mapping_hash}
        )[:32]
        created_at = _utc_now()
        with self._connect() as connection:
            plan = connection.execute(
                "SELECT id FROM study_plan_versions WHERE id = ?", (plan_id,)
            ).fetchone()
            if plan is None:
                raise LookupError("研究计划版本不存在")
            dataset = connection.execute(
                "SELECT id FROM dataset_versions WHERE id = ?", (dataset_id,)
            ).fetchone()
            if dataset is None:
                raise LookupError("数据版本不存在")
            connection.execute(
                "INSERT OR REPLACE INTO study_plan_dataset_mappings "
                "(id, study_plan_version_id, dataset_version_id, mapping_json, mapping_hash, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    mapping_id,
                    plan_id,
                    dataset_id,
                    json.dumps(mapping, ensure_ascii=False, sort_keys=True),
                    mapping_hash,
                    status,
                    created_at,
                ),
            )
        return {
            "id": mapping_id,
            "studyPlanVersionId": plan_id,
            "datasetVersionId": dataset_id,
            "mapping": mapping,
            "mappingHash": mapping_hash,
            "status": status,
            "createdAt": created_at,
        }
