from __future__ import annotations

import json
import sqlite3

from app.services.canonical_identity import canonical_sha256
from app.services.repository_io import _utc_now


class ImputationPlanRepositoryMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    @staticmethod
    def _imputation_plan_response(row: sqlite3.Row) -> dict[str, object]:
        payload = json.loads(row["payload_json"])
        return {
            "schemaVersion": "1.0.0",
            "id": row["id"],
            "datasetVersionId": row["dataset_version_id"],
            "datasetSha256": payload["datasetSha256"],
            "contextHash": row["context_hash"],
            "sampleVersionId": payload["sampleVersionId"],
            "sampleHash": payload["sampleHash"],
            "measurementVersionId": payload.get("measurementVersionId"),
            "measurementHash": payload.get("measurementHash"),
            "structureVersionId": row["structure_version_id"],
            "structureHash": payload.get("structureHash"),
            "substantiveModel": payload["substantiveModel"],
            "variables": payload["variables"],
            "passiveRules": payload.get("passiveRules", []),
            "clusterVariableId": payload.get("clusterVariableId"),
            "imputations": payload["imputations"],
            "iterations": payload["iterations"],
            "seed": payload["seed"],
            "diagnostics": payload["diagnostics"],
            "predictorMatrixHash": payload["predictorMatrixHash"],
            "substantiveModelHash": row["substantive_model_hash"],
            "planHash": row["plan_hash"],
            "createdAt": row["created_at"],
        }

    def get_imputation_plan(self, plan_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM imputation_plan_versions WHERE id = ?", (plan_id,)
            ).fetchone()
        return None if row is None else self._imputation_plan_response(row)

    def save_imputation_plan(
        self,
        dataset_id: str,
        structure_version_id: str | None,
        context_hash: str,
        sample_hash: str,
        substantive_model_hash: str,
        plan_hash: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        created_at = _utc_now()
        plan_id = "imputation_plan_" + plan_hash[:32]
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO imputation_plan_versions "
                "(id, dataset_version_id, structure_version_id, sample_identity, sample_hash, "
                "measurement_version_id, context_hash, substantive_model_hash, plan_hash, "
                "payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    plan_id,
                    dataset_id,
                    structure_version_id,
                    str(payload["sampleVersionId"]),
                    sample_hash,
                    payload.get("measurementVersionId"),
                    context_hash,
                    substantive_model_hash,
                    plan_hash,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    created_at,
                ),
            )
            row = connection.execute(
                "SELECT * FROM imputation_plan_versions WHERE id = ?", (plan_id,)
            ).fetchone()
        assert row is not None
        return self._imputation_plan_response(row)

    def list_imputation_plans(self, dataset_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM imputation_plan_versions WHERE dataset_version_id = ? ORDER BY created_at DESC",
                (dataset_id,),
            ).fetchall()
        return [self._imputation_plan_response(row) for row in rows]

    @staticmethod
    def imputation_dataset_id(plan_id: str, job_id: str) -> str:
        return "imputation_dataset_" + canonical_sha256(
            {"planVersionId": plan_id, "jobId": job_id}
        )[:32]

    def save_imputation_dataset_version(
        self, plan_id: str, job_id: str, result: dict[str, object]
    ) -> str:
        family_result = result.get("familyResult")
        family_result = family_result if isinstance(family_result, dict) else {}
        artifacts = family_result.get("artifacts")
        artifacts = artifacts if isinstance(artifacts, list) else []
        artifact_hash = canonical_sha256(artifacts)
        artifact_manifest_path = f"projects/default/runs/{job_id}/imputation-manifest.json"
        version_id = self.imputation_dataset_id(plan_id, job_id)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO imputation_dataset_versions "
                "(id, plan_version_id, job_id, artifact_manifest_path, artifact_hash, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'ready', ?)",
                (version_id, plan_id, job_id, artifact_manifest_path, artifact_hash, _utc_now()),
            )
        return version_id

    def get_imputation_dataset_version(self, dataset_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM imputation_dataset_versions WHERE id = ?", (dataset_id,)
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "imputationPlanVersionId": row["plan_version_id"],
            "jobId": row["job_id"],
            "artifactManifestPath": row["artifact_manifest_path"],
            "artifactHash": row["artifact_hash"],
            "status": row["status"],
            "createdAt": row["created_at"],
        }

    def get_imputation_dataset_plan_id(self, dataset_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT plan_version_id FROM imputation_dataset_versions WHERE id = ?",
                (dataset_id,),
            ).fetchone()
        return None if row is None else str(row["plan_version_id"])
