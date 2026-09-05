from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.services.repository_io import (
    JsonObject,
    UnsafePathError,
    _read_json_safe,
    _write_json_atomic,
    remove_path_tree,
    resolve_owned_path,
    safe_identifier,
)
from app.settings import Settings


class AnalysisAdvancedRepositoryMixin:
    """Repository surface for advanced job state and immutable results."""

    settings: Settings

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def save_advanced_job(self, state: JsonObject, path: Path) -> None:
        state_copy = dict(state)
        state_copy["result"] = None
        _write_json_atomic(path, state_copy)
        relative = path.relative_to(self.settings.state_root).as_posix()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO advanced_analysis_jobs (
                    id, analysis_id, family, spec_hash, dataset_version_id,
                    status, stage, progress, cancel_requested, created_at,
                    updated_at, state_path, result_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status = excluded.status,
                    stage = excluded.stage,
                    progress = excluded.progress,
                    cancel_requested = excluded.cancel_requested,
                    updated_at = excluded.updated_at,
                    state_path = excluded.state_path,
                    result_path = excluded.result_path
                """,
                (
                    state["id"],
                    state["analysisId"],
                    state["family"],
                    state["specHash"],
                    state.get("datasetVersionId"),
                    state["status"],
                    state["stage"],
                    state["progress"],
                    int(bool(state.get("cancelRequested"))),
                    state["createdAt"],
                    state["updatedAt"],
                    relative,
                    state.get("resultPath"),
                ),
            )

    def _validate_advanced_job_state_identity(
        self, row: sqlite3.Row, state: JsonObject
    ) -> None:
        run_id = safe_identifier(row["id"], label="advanced job run id")
        expected = {
            "id": run_id,
            "analysisId": row["analysis_id"],
            "family": row["family"],
            "specHash": row["spec_hash"],
            "datasetVersionId": row["dataset_version_id"],
        }
        actual = {
            "id": state.get("id"),
            "analysisId": state.get("analysisId"),
            "family": state.get("family"),
            "specHash": state.get("specHash"),
            "datasetVersionId": state.get("datasetVersionId"),
        }
        if actual != expected:
            raise LookupError(f"AdvancedAnalysisJob 身份不匹配: {row['id']}")

        state_result_path = state.get("resultPath")
        row_result_path = row["result_path"]
        if state_result_path is not None and row_result_path is not None:
            if state_result_path != row_result_path:
                raise LookupError(f"AdvancedAnalysisJob 结果身份不匹配: {run_id}")
        if state_result_path is None:
            return
        resolve_owned_path(
            self.settings.state_root,
            state_result_path,
            label="advanced analysis job result path",
            expected_parent=self.settings.state_root / "projects" / "default" / "runs" / run_id,
            expected_name="result.json",
        )

    def get_advanced_job(self, run_id: str) -> JsonObject:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, analysis_id, family, spec_hash, dataset_version_id, "
                "state_path, result_path FROM advanced_analysis_jobs WHERE id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise LookupError(f"AdvancedAnalysisJob 不存在: {run_id}")
        path = resolve_owned_path(
            self.settings.state_root,
            row["state_path"],
            label="advanced job state path",
            expected_parent=self.settings.state_root / "projects" / "default" / "runs" / run_id,
            expected_name="state.json",
        )
        state = _read_json_safe(path)
        self._validate_advanced_job_state_identity(row, state)
        return state

    def delete_advanced_job(self, run_id: str) -> None:
        state: JsonObject | None = None
        state_path: Path | None = None
        with self._connect() as connection:
            row_job = connection.execute(
                """
                SELECT id, analysis_id, family, spec_hash, dataset_version_id,
                       state_path, result_path
                FROM advanced_analysis_jobs WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
            if row_job:
                state_path = resolve_owned_path(
                    self.settings.state_root,
                    row_job["state_path"],
                    label="advanced job state path",
                    expected_parent=self.settings.state_root
                    / "projects"
                    / "default"
                    / "runs"
                    / run_id,
                    expected_name="state.json",
                )
                if state_path.exists():
                    state = _read_json_safe(state_path)
                    self._validate_advanced_job_state_identity(row_job, state)
            connection.execute("DELETE FROM advanced_analysis_jobs WHERE id = ?", (run_id,))

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

    def list_advanced_jobs_for_index(self) -> list[JsonObject]:
        """Return every readable advanced job after strict persisted-state validation."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, analysis_id, family, spec_hash, dataset_version_id,
                       state_path, result_path
                FROM advanced_analysis_jobs
                ORDER BY created_at DESC
                """
            ).fetchall()
        states: list[JsonObject] = []
        for row in rows:
            try:
                path = resolve_owned_path(
                    self.settings.state_root,
                    row["state_path"],
                    label="advanced index recovery state path",
                    expected_parent=self.settings.state_root
                    / "projects"
                    / "default"
                    / "runs"
                    / row["id"],
                    expected_name="state.json",
                )
                state = _read_json_safe(path)
                self._validate_advanced_job_state_identity(row, state)
                states.append(state)
            except (UnsafePathError, OSError, LookupError, ValueError, json.JSONDecodeError):
                continue
        return states

    def list_unfinished_advanced_jobs(self) -> list[JsonObject]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, analysis_id, family, spec_hash, dataset_version_id,
                       state_path, result_path
                FROM advanced_analysis_jobs
                WHERE status IN ('queued', 'running', 'cancelling')
                """
            ).fetchall()
        states = []
        for row in rows:
            try:
                path = resolve_owned_path(
                    self.settings.state_root,
                    row["state_path"],
                    label="advanced job recovery state path",
                    expected_parent=self.settings.state_root
                    / "projects"
                    / "default"
                    / "runs"
                    / row["id"],
                    expected_name="state.json",
                )
                state = _read_json_safe(path)
                self._validate_advanced_job_state_identity(row, state)
                states.append(state)
            except (UnsafePathError, OSError, LookupError, ValueError, json.JSONDecodeError):
                continue
        return states

    def record_advanced_result(self, run_id: str, result: JsonObject) -> Path:
        path = self.settings.state_root / "projects" / "default" / "runs" / run_id / "result.json"
        _write_json_atomic(path, result)
        return path

    def get_advanced_result(self, run_id: str) -> JsonObject:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, analysis_id, family, spec_hash, dataset_version_id,
                       state_path, result_path
                FROM advanced_analysis_jobs WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            raise LookupError(f"AdvancedResult 不存在: {run_id}")

        result_path = row["result_path"]
        if result_path is None:
            # State JSON can publish `succeeded` immediately before SQLite
            # commits result_path; the result file is already committed.
            state_parent = self.settings.state_root / "projects" / "default" / "runs" / run_id
            state_path = resolve_owned_path(
                self.settings.state_root,
                row["state_path"],
                label="advanced job state path",
                expected_parent=state_parent,
                expected_name="state.json",
            )
            state = _read_json_safe(state_path)
            self._validate_advanced_job_state_identity(row, state)
            if state.get("status") != "succeeded" or not state.get("resultPath"):
                raise LookupError(f"AdvancedResult 不存在: {run_id}")
            result_path = state["resultPath"]
        path = resolve_owned_path(
            self.settings.state_root,
            result_path,
            label="advanced result path",
            expected_parent=self.settings.state_root / "projects" / "default" / "runs" / run_id,
            expected_name="result.json",
        )
        result = _read_json_safe(path)
        if result.get("run", {}).get("id") != run_id:
            raise LookupError(f"AdvancedResult 身份不匹配: {run_id}")
        return result
