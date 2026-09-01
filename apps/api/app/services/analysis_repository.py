from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.analysis_advanced_repository import AnalysisAdvancedRepositoryMixin
from app.services.repository_io import (
    JsonObject,
    UnsafePathError,
    _read_json_safe,
    _utc_now,
    _write_json_atomic,
    remove_path_tree,
    resolve_owned_path,
    safe_identifier,
)
from app.settings import Settings


class AnalysisRepositoryMixin(AnalysisAdvancedRepositoryMixin):
    settings: Settings

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_analysis_result(
        self,
        dataset_id: str,
        model_id: str,
        model_version: int,
        result: JsonObject,
    ) -> Path:
        run_id = result["run"]["id"]
        created_at = _utc_now()
        path = self.settings.state_root / "projects" / "default" / "runs" / run_id / "result.json"
        _write_json_atomic(path, result)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO analysis_runs (
                    id, dataset_id, model_id, model_version,
                    created_at, status, result_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    dataset_id,
                    model_id,
                    model_version,
                    created_at,
                    result["run"]["status"],
                    path.relative_to(self.settings.state_root).as_posix(),
                ),
            )
        return path

    def get_analysis_result(self, run_id: str) -> JsonObject:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_path FROM analysis_runs WHERE id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise LookupError(f"AnalysisRun 不存在: {run_id}")
        path = resolve_owned_path(
            self.settings.state_root,
            row["result_path"],
            label="analysis result path",
            expected_parent=self.settings.state_root / "projects" / "default" / "runs" / run_id,
            expected_name="result.json",
        )
        result = _read_json_safe(path)
        if result.get("run", {}).get("id") != run_id:
            raise LookupError(f"AnalysisResult 身份不匹配: {run_id}")
        return result

    def _validate_job_state_identity(self, row: sqlite3.Row, state: JsonObject) -> None:
        run_id = safe_identifier(row["id"], label="analysis run id")
        expected = {
            "id": run_id,
            "datasetId": row["dataset_id"],
            "modelId": row["model_id"],
            "modelVersion": int(row["model_version"]),
            "jobKind": row["job_kind"],
        }
        actual = {
            "id": state.get("id"),
            "datasetId": state.get("datasetId"),
            "modelId": state.get("modelId"),
            "modelVersion": state.get("modelVersion"),
            "jobKind": state.get("jobKind", "model"),
        }
        if actual != expected:
            raise LookupError(f"AnalysisJob 身份不匹配: {row['id']}")

        state_result_path = state.get("resultPath")
        row_result_path = row["result_path"]
        # The state file and SQLite row are replaced in separate atomic operations.
        # During the successful-result transition a reader can therefore observe
        # exactly one side as null.  Compare values once both are present, while
        # independently proving that every non-null state path is owned by the
        # exact job/report before returning it to a caller.
        if state_result_path is not None and row_result_path is not None:
            if state_result_path != row_result_path:
                raise LookupError(f"AnalysisJob 结果身份不匹配: {run_id}")
        if state_result_path is None:
            return
        if state.get("jobKind") == "empirical":
            self.resolve_empirical_report_path(state)
            return
        resolve_owned_path(
            self.settings.state_root,
            state_result_path,
            label="analysis job result path",
            expected_parent=self.settings.state_root / "projects" / "default" / "runs" / run_id,
            expected_name="result.json",
        )

    def resolve_empirical_report_path(self, state: JsonObject) -> Path:
        if state.get("jobKind") != "empirical":
            raise LookupError("AnalysisJob 不是实证分析任务")
        dataset_id = safe_identifier(state.get("datasetId"), label="dataset id")
        report_id = safe_identifier(state.get("reportId"), label="report id")
        measurement_version = state.get("measurementVersion")
        if measurement_version is not None and (not isinstance(measurement_version, int) or isinstance(measurement_version, bool) or measurement_version < 1):
            raise UnsafePathError("measurement version is invalid")
        if measurement_version is None and ("measurementVersion" not in state or state.get("measurementVersionId") is not None or state.get("modelVersion") != 0):
            raise UnsafePathError("raw analysis measurement identity is invalid")
        expected_parent = (
            self.settings.state_root
            / "projects"
            / "default"
            / "datasets"
            / dataset_id
        )
        if measurement_version is not None:
            expected_parent = expected_parent / "measurement" / f"v{measurement_version}"
        expected_parent = expected_parent / "empirical" / report_id
        return resolve_owned_path(
            self.settings.state_root,
            state.get("resultPath"),
            label="empirical report path",
            expected_parent=expected_parent,
            expected_name="report.json",
        )

    def get_empirical_report(self, state: JsonObject) -> JsonObject:
        report = _read_json_safe(self.resolve_empirical_report_path(state))
        if (
            report.get("reportId") != state.get("reportId")
            or report.get("datasetId") != state.get("datasetId")
            or report.get("measurementVersionId") != state.get("measurementVersionId")
        ):
            raise LookupError(f"EmpiricalReport 身份不匹配: {state.get('reportId')}")
        return report

    def save_analysis_job(self, state: JsonObject, path: Path) -> None:
        state_copy = dict(state)
        state_copy["result"] = None
        _write_json_atomic(path, state_copy)
        relative = path.relative_to(self.settings.state_root).as_posix()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO analysis_jobs (
                    id, dataset_id, model_id, model_version, status,
                    stage, progress, created_at, updated_at, state_path,
                    job_kind, cancel_requested, result_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    stage = excluded.stage,
                    progress = excluded.progress,
                    updated_at = excluded.updated_at,
                    state_path = excluded.state_path,
                    job_kind = excluded.job_kind,
                    cancel_requested = excluded.cancel_requested,
                    result_path = excluded.result_path
                """,
                (
                    state["id"],
                    state["datasetId"],
                    state["modelId"],
                    state["modelVersion"],
                    state["status"],
                    state["stage"],
                    state["progress"],
                    state["createdAt"],
                    state["updatedAt"],
                    relative,
                    state.get("jobKind", "model"),
                    int(bool(state.get("cancelRequested"))),
                    state.get("resultPath"),
                ),
            )

    def delete_analysis_job_and_run(self, run_id: str) -> None:
        state: JsonObject | None = None
        state_path: Path | None = None
        result_path: Path | None = None
        empirical_report_path: Path | None = None
        with self._connect() as connection:
            row_run = connection.execute(
                "SELECT result_path FROM analysis_runs WHERE id = ?", (run_id,)
            ).fetchone()
            row_job = connection.execute(
                """
                SELECT id, dataset_id, model_id, model_version, state_path,
                       job_kind, result_path
                FROM analysis_jobs WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
            if row_job:
                state_path = resolve_owned_path(
                    self.settings.state_root,
                    row_job["state_path"],
                    label="analysis job state path",
                    expected_parent=self.settings.state_root
                    / "projects"
                    / "default"
                    / "runs"
                    / run_id,
                    expected_name="state.json",
                )
                if state_path.exists():
                    state = _read_json_safe(state_path)
                    self._validate_job_state_identity(row_job, state)
                    if state.get("jobKind") == "empirical" and state.get("resultPath"):
                        empirical_report_path = self.resolve_empirical_report_path(state)
            if row_run:
                result_path = resolve_owned_path(
                    self.settings.state_root,
                    row_run["result_path"],
                    label="analysis result path",
                    expected_parent=self.settings.state_root
                    / "projects"
                    / "default"
                    / "runs"
                    / run_id,
                    expected_name="result.json",
                )
            connection.execute("DELETE FROM analysis_runs WHERE id = ?", (run_id,))
            connection.execute("DELETE FROM analysis_jobs WHERE id = ?", (run_id,))

        state_root = self.settings.state_root.resolve()

        def remove_known_directory(path: Path, expected_parent: str) -> None:
            resolved = path.resolve()
            if (
                resolved != state_root
                and resolved.is_relative_to(state_root)
                and resolved.parent.name == expected_parent
            ):
                remove_path_tree(resolved)

        if state_path is not None:
            remove_known_directory(state_path.parent, "runs")
        elif result_path is not None:
            remove_known_directory(result_path.parent, "runs")

        if empirical_report_path is not None:
            remove_path_tree(empirical_report_path.parent)

    def list_terminal_analysis_run_ids(
        self,
        *,
        older_than_days: float | None = None,
        keep_count: int | None = None,
    ) -> set[str]:
        """Return terminal analysis run ids eligible for cleanup."""
        if keep_count is not None and keep_count < 0:
            raise ValueError("keep_count 不能小于 0")
        if older_than_days is not None and older_than_days < 0:
            raise ValueError("older_than_days 不能小于 0")
        terminal = "('succeeded', 'failed', 'cancelled')"
        run_ids: set[str] = set()
        with self._connect() as connection:
            if older_than_days is not None:
                cutoff = (
                    datetime.now(timezone.utc) - timedelta(days=older_than_days)
                ).isoformat()
                rows = connection.execute(
                    f"SELECT id FROM analysis_jobs WHERE status IN {terminal} AND created_at < ?",
                    (cutoff,),
                ).fetchall()
                run_ids.update(row["id"] for row in rows)
            if keep_count is not None:
                rows = connection.execute(
                    f"SELECT id FROM analysis_jobs WHERE status IN {terminal} "
                    "ORDER BY created_at DESC"
                ).fetchall()
                run_ids.update(row["id"] for row in rows[keep_count:])
        return run_ids

    def get_analysis_job(self, run_id: str) -> JsonObject:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, dataset_id, model_id, model_version, state_path,
                       job_kind, result_path
                FROM analysis_jobs WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            raise LookupError(f"AnalysisRun 不存在: {run_id}")
        path = resolve_owned_path(
            self.settings.state_root,
            row["state_path"],
            label="analysis job state path",
            expected_parent=self.settings.state_root / "projects" / "default" / "runs" / run_id,
            expected_name="state.json",
        )
        state = _read_json_safe(path)
        self._validate_job_state_identity(row, state)
        return state

    def list_unfinished_analysis_jobs(self) -> list[JsonObject]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, dataset_id, model_id, model_version, state_path,
                       job_kind, result_path
                FROM analysis_jobs
                WHERE status IN ('queued', 'running', 'cancelling')
                """
            ).fetchall()
        states = []
        for row in rows:
            try:
                path = resolve_owned_path(
                    self.settings.state_root,
                    row["state_path"],
                    label="analysis recovery state path",
                    expected_parent=self.settings.state_root
                    / "projects"
                    / "default"
                    / "runs"
                    / row["id"],
                    expected_name="state.json",
                )
                state = _read_json_safe(path)
                self._validate_job_state_identity(row, state)
                states.append(state)
            except (UnsafePathError, OSError, LookupError, ValueError, json.JSONDecodeError):
                continue
        return states
