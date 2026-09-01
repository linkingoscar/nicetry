from __future__ import annotations

import json
import sqlite3

from app.services.canonical_identity import canonical_sha256
from app.services.repository_io import _utc_now


class AnalysisDraftRepositoryMixin:
    """Store mutable draft revisions while preserving immutable context identity."""

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    @staticmethod
    def _invalidation_details(reasons: list[str]) -> dict[str, object] | None:
        labels = {
            "DATASET_VERSION_CHANGED": "数据版本发生变化",
            "STUDY_CONTEXT_CHANGED": "研究上下文版本发生变化",
            "STRUCTURE_CHANGED": "结构角色或结构画像发生变化",
            "MEASUREMENT_CHANGED": "测量版本发生变化",
            "SAMPLE_CHANGED": "分析样本版本发生变化",
            "IMPUTATION_CHANGED": "插补产物发生变化",
            "ANALYSIS_CONTEXT_CHANGED": "分析上下文哈希发生变化",
        }
        affected_by_reason = {
            "DATASET_VERSION_CHANGED": "数据版本绑定",
            "STUDY_CONTEXT_CHANGED": "研究问题的设计与时间假设",
            "STRUCTURE_CHANGED": "角色绑定、嵌套关系与结构方法",
            "MEASUREMENT_CHANGED": "构念、题项与测量结果",
            "SAMPLE_CHANGED": "纳入/排除规则与分析样本",
            "IMPUTATION_CHANGED": "插补数据与合并推断",
            "ANALYSIS_CONTEXT_CHANGED": "该分析草稿及其派生运行结果",
        }
        known = [reason for reason in reasons if reason in labels]
        if not known:
            return None
        return {
            "upstreamChanges": list(dict.fromkeys(labels[reason] for reason in known)),
            "affectedObjects": list(dict.fromkeys(affected_by_reason[reason] for reason in known)),
            "historyStatus": "available",
            "requiredAction": "rerun",
        }

    @staticmethod
    def _draft_response(row: sqlite3.Row) -> dict[str, object]:
        invalidation_reasons = json.loads(row["invalidation_reasons_json"])
        return {
            "schemaVersion": "1.0.0",
            "id": row["id"],
            "revision": row["revision"],
            "datasetVersionId": row["dataset_version_id"],
            "family": row["family"],
            "sliceId": row["slice_id"],
            "contextHash": row["context_hash"],
            "contextSnapshotId": row["context_snapshot_id"],
            "spec": json.loads(row["spec_json"]),
            "roleOverrides": json.loads(row["role_overrides_json"]),
            "validity": row["validity"],
            "invalidationReasons": invalidation_reasons,
            "invalidation": AnalysisDraftRepositoryMixin._invalidation_details(invalidation_reasons),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def get_analysis_draft(self, draft_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM analysis_drafts WHERE id = ?", (draft_id,)
            ).fetchone()
        return None if row is None else self._draft_response(row)

    def create_analysis_draft(
        self,
        dataset_id: str,
        family: str,
        slice_id: str,
        context_hash: str,
        snapshot_id: str,
        spec: dict[str, object],
        role_overrides: dict[str, dict[str, str]],
        validity: str,
    ) -> dict[str, object]:
        created_at = _utc_now()
        draft_id = "draft_" + canonical_sha256(
            {
                "datasetVersionId": dataset_id,
                "sliceId": slice_id,
                "contextHash": context_hash,
                "createdAt": created_at,
            }
        )[:32]
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO analysis_drafts "
                "(id, dataset_version_id, revision, family, slice_id, context_snapshot_id, "
                "context_hash, spec_json, role_overrides_json, validity, "
                "invalidation_reasons_json, created_at, updated_at) "
                "VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, '[]', ?, ?)",
                (
                    draft_id,
                    dataset_id,
                    family,
                    slice_id,
                    snapshot_id,
                    context_hash,
                    json.dumps(spec, ensure_ascii=False, sort_keys=True),
                    json.dumps(role_overrides, ensure_ascii=False, sort_keys=True),
                    validity,
                    created_at,
                    created_at,
                ),
            )
            row = connection.execute(
                "SELECT * FROM analysis_drafts WHERE id = ?", (draft_id,)
            ).fetchone()
        assert row is not None
        return self._draft_response(row)

    def update_analysis_draft(
        self,
        draft_id: str,
        expected_revision: int,
        context_hash: str,
        spec: dict[str, object],
        role_overrides: dict[str, dict[str, str]],
        validity: str,
    ) -> dict[str, object] | None:
        updated_at = _utc_now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM analysis_drafts WHERE id = ?", (draft_id,)
            ).fetchone()
            if row is None:
                return None
            if int(row["revision"]) != expected_revision:
                raise ValueError("REVISION_CONFLICT: 分析草稿 revision 已变化")
            connection.execute(
                "UPDATE analysis_drafts SET revision = ?, context_hash = ?, spec_json = ?, "
                "role_overrides_json = ?, validity = ?, invalidation_reasons_json = '[]', "
                "updated_at = ? WHERE id = ?",
                (
                    expected_revision + 1,
                    context_hash,
                    json.dumps(spec, ensure_ascii=False, sort_keys=True),
                    json.dumps(role_overrides, ensure_ascii=False, sort_keys=True),
                    validity,
                    updated_at,
                    draft_id,
                ),
            )
            row = connection.execute(
                "SELECT * FROM analysis_drafts WHERE id = ?", (draft_id,)
            ).fetchone()
        assert row is not None
        return self._draft_response(row)

    def mark_analysis_drafts_stale(
        self,
        dataset_id: str,
        current_context_hash: str,
        current_context: dict[str, object] | None = None,
    ) -> int:
        updated_at = _utc_now()
        changed = 0
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT d.id, d.invalidation_reasons_json, s.payload_json "
                "FROM analysis_drafts d "
                "LEFT JOIN analysis_context_snapshots s ON s.id = d.context_snapshot_id "
                "WHERE d.dataset_version_id = ? AND d.context_hash <> ? "
                "AND validity IN ('ready', 'incomplete')",
                (dataset_id, current_context_hash),
            ).fetchall()
            for row in rows:
                reasons = json.loads(row["invalidation_reasons_json"])
                if current_context is not None and row["payload_json"]:
                    try:
                        previous = json.loads(row["payload_json"])
                    except json.JSONDecodeError:
                        previous = {}
                    for reason, key in (
                        ("DATASET_VERSION_CHANGED", "dataset"),
                        ("STUDY_CONTEXT_CHANGED", "studyContext"),
                        ("STRUCTURE_CHANGED", "structure"),
                        ("MEASUREMENT_CHANGED", "measurement"),
                        ("SAMPLE_CHANGED", "sample"),
                        ("IMPUTATION_CHANGED", "imputation"),
                    ):
                        old_artifact = previous.get(key) if isinstance(previous, dict) else None
                        current_artifact = current_context.get(key)
                        old_hash = old_artifact.get("hash") if isinstance(old_artifact, dict) else None
                        current_hash = current_artifact.get("hash") if isinstance(current_artifact, dict) else None
                        if old_hash != current_hash and reason not in reasons:
                            reasons.append(reason)
                if "ANALYSIS_CONTEXT_CHANGED" not in reasons:
                    reasons.append("ANALYSIS_CONTEXT_CHANGED")
                connection.execute(
                    "UPDATE analysis_drafts SET validity = 'stale', "
                    "invalidation_reasons_json = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(reasons, ensure_ascii=False), updated_at, row["id"]),
                )
                changed += 1
        return changed
