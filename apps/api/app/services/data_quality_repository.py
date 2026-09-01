from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

from app.services.repository_io import (
    _read_json_safe,
    _utc_now,
    resolve_owned_path,
    safe_identifier,
)
from app.settings import Settings


class DataQualityRepositoryMixin:
    settings: Settings

    def _connect(self):
        raise NotImplementedError

    def _quality_root(self, dataset_id: str) -> Path:
        dataset_id = safe_identifier(dataset_id, label="dataset id")
        return (
            self.settings.state_root / "projects" / "default" / "datasets" / dataset_id / "quality"
        )

    def record_data_quality_run(self, run: dict[str, object], run_path: Path) -> None:
        dataset_id = safe_identifier(str(run["datasetVersionId"]), label="dataset id")
        run_id = safe_identifier(str(run["id"]), label="quality run id")
        relative_path = run_path.relative_to(self.settings.state_root).as_posix()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO data_quality_runs (
                    id, dataset_version_id, dataset_sha256, request_hash, created_at,
                    row_count, case_metrics_path, case_metrics_hash, summary_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    dataset_id,
                    str(run["datasetSha256"]),
                    _hash_json(run.get("request", {})),
                    str(run["createdAt"]),
                    int(cast(int, run["rowCount"])),
                    str(run["caseMetricsPath"]),
                    str(run["caseMetricsHash"]),
                    relative_path,
                ),
            )

    def get_data_quality_run(self, dataset_id: str, run_id: str) -> dict[str, object]:
        dataset_id = safe_identifier(dataset_id, label="dataset id")
        run_id = safe_identifier(run_id, label="quality run id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT summary_path FROM data_quality_runs WHERE id = ? AND dataset_version_id = ?",
                (run_id, dataset_id),
            ).fetchone()
        if row is None:
            raise LookupError(f"DataQualityRun 不存在: {run_id}")
        path = resolve_owned_path(
            self.settings.state_root,
            row["summary_path"],
            label="data quality run path",
            expected_parent=self._quality_root(dataset_id) / "runs" / run_id,
            expected_name="run.json",
        )
        data = _read_json_safe(path)
        if data.get("id") != run_id or data.get("datasetVersionId") != dataset_id:
            raise LookupError(f"DataQualityRun 身份不匹配: {run_id}")
        return data

    def list_data_quality_runs(self, dataset_id: str) -> list[dict[str, object]]:
        dataset_id = safe_identifier(dataset_id, label="dataset id")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT summary_path FROM data_quality_runs WHERE dataset_version_id = ? ORDER BY created_at DESC",
                (dataset_id,),
            ).fetchall()
        results: list[dict[str, object]] = []
        for row in rows:
            path = resolve_owned_path(
                self.settings.state_root,
                row["summary_path"],
                label="data quality run path",
                expected_parent=self._quality_root(dataset_id)
                / "runs"
                / Path(row["summary_path"]).parent.name,
                expected_name="run.json",
            )
            results.append(_read_json_safe(path))
        return results

    def get_data_quality_case_path(self, dataset_id: str, run_id: str) -> Path:
        run = self.get_data_quality_run(dataset_id, run_id)
        return resolve_owned_path(
            self.settings.state_root,
            str(run["caseMetricsPath"]),
            label="data quality case metrics path",
            expected_parent=self._quality_root(dataset_id)
            / "runs"
            / safe_identifier(run_id, label="quality run id"),
            expected_name="cases.parquet",
        )

    def record_analysis_sample(self, sample: dict[str, object], sample_path: Path) -> None:
        dataset_id = safe_identifier(str(sample["datasetVersionId"]), label="dataset id")
        sample_id = safe_identifier(str(sample["id"]), label="sample version id")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO analysis_sample_versions (
                    id, dataset_version_id, dataset_sha256, quality_run_id, created_at,
                    label, combine_operator, rules_hash, row_count, included_count,
                    excluded_count, boundary_count, sample_hash, case_records_path,
                    case_records_hash, summary_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sample_id,
                    dataset_id,
                    str(sample["datasetSha256"]),
                    str(sample["qualityRunId"]),
                    str(sample["createdAt"]),
                    str(sample["label"]),
                    str(sample["combineOperator"]),
                    _hash_json(sample.get("rules", [])),
                    int(cast(int, sample["rowCount"])),
                    int(cast(int, sample["includedCount"])),
                    int(cast(int, sample["excludedCount"])),
                    int(cast(int, sample["boundaryCount"])),
                    str(sample["sampleHash"]),
                    str(sample["caseRecordsPath"]),
                    str(sample["caseRecordsHash"]),
                    sample_path.relative_to(self.settings.state_root).as_posix(),
                ),
            )

    def get_analysis_sample(self, dataset_id: str, sample_id: str) -> dict[str, object]:
        dataset_id = safe_identifier(dataset_id, label="dataset id")
        sample_id = safe_identifier(sample_id, label="sample version id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT summary_path FROM analysis_sample_versions WHERE id = ? AND dataset_version_id = ?",
                (sample_id, dataset_id),
            ).fetchone()
        if row is None:
            raise LookupError(f"AnalysisSampleVersion 不存在: {sample_id}")
        path = resolve_owned_path(
            self.settings.state_root,
            row["summary_path"],
            label="analysis sample path",
            expected_parent=self._quality_root(dataset_id) / "samples" / sample_id,
            expected_name="sample.json",
        )
        data = _read_json_safe(path)
        if data.get("id") != sample_id or data.get("datasetVersionId") != dataset_id:
            raise LookupError(f"AnalysisSampleVersion 身份不匹配: {sample_id}")
        return data

    def list_analysis_samples(self, dataset_id: str) -> list[dict[str, object]]:
        dataset_id = safe_identifier(dataset_id, label="dataset id")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT summary_path FROM analysis_sample_versions "
                "WHERE dataset_version_id = ? ORDER BY created_at DESC",
                (dataset_id,),
            ).fetchall()
        results: list[dict[str, object]] = []
        for row in rows:
            summary_path = Path(str(row["summary_path"]))
            sample_id = summary_path.parent.name
            path = resolve_owned_path(
                self.settings.state_root,
                row["summary_path"],
                label="analysis sample path",
                expected_parent=self._quality_root(dataset_id)
                / "samples"
                / safe_identifier(sample_id, label="sample version id"),
                expected_name="sample.json",
            )
            results.append(_read_json_safe(path))
        return results

    def get_analysis_sample_case_path(self, dataset_id: str, sample_id: str) -> Path:
        sample = self.get_analysis_sample(dataset_id, sample_id)
        return resolve_owned_path(
            self.settings.state_root,
            str(sample["caseRecordsPath"]),
            label="analysis sample case records path",
            expected_parent=self._quality_root(dataset_id)
            / "samples"
            / safe_identifier(sample_id, label="sample version id"),
            expected_name="cases.parquet",
        )

    def invalidate_dataset_results(
        self, dataset_id: str, sample_id: str, sample_hash: str, reason: str
    ) -> list[str]:
        dataset_id = safe_identifier(dataset_id, label="dataset id")
        invalidated: list[str] = []
        with self._connect() as connection:
            analysis_rows = connection.execute(
                "SELECT id FROM analysis_runs WHERE dataset_id = ? AND status = 'succeeded'",
                (dataset_id,),
            ).fetchall()
            for row in analysis_rows:
                analysis_id = str(row["id"])
                invalidated.append(analysis_id)
                connection.execute(
                    """
                    INSERT INTO result_invalidations (
                        id, dataset_version_id, sample_version_id, sample_hash,
                        analysis_id, reason, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"invalidation_{uuid4_hex()}",
                        dataset_id,
                        sample_id,
                        sample_hash,
                        analysis_id,
                        reason,
                        _utc_now(),
                    ),
                )
        return invalidated


def uuid4_hex() -> str:
    import uuid

    return uuid.uuid4().hex[:16]


def _hash_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
