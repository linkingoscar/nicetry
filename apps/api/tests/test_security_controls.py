from __future__ import annotations

import os
import stat
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app, create_app
from app.services import repository_io
from app.services.empirical_export import _append_sheet, empirical_report_path
from app.services.repository_io import (
    UnsafePathError,
    is_link_or_reparse_point,
    remove_path_tree,
    resolve_owned_path,
    safe_relative_path,
)
from app.services.tabular_security import escape_spreadsheet_formula
from app.settings import get_settings


def test_mutations_require_random_session_token() -> None:
    unauthenticated = TestClient(app)
    assert unauthenticated.get("/api/v1/session").status_code == 403
    missing_bootstrap = unauthenticated.post(
        "/api/v1/session/bootstrap", json={"bootstrapToken": ""}
    )
    wrong_bootstrap = unauthenticated.post(
        "/api/v1/session/bootstrap", json={"bootstrapToken": "wrong"}
    )
    assert missing_bootstrap.status_code == wrong_bootstrap.status_code == 403

    session = unauthenticated.post(
        "/api/v1/session/bootstrap",
        json={"bootstrapToken": app.state.services.settings.session_bootstrap_token},
    )
    assert session.status_code == 200
    assert session.headers["cache-control"] == "no-store"
    token = session.json()["token"]
    assert len(token) >= 32
    replay = unauthenticated.post(
        "/api/v1/session/bootstrap",
        json={"bootstrapToken": app.state.services.settings.session_bootstrap_token},
    )
    assert replay.status_code == 403

    missing = unauthenticated.post("/api/v1/demo/load")
    wrong = unauthenticated.post("/api/v1/demo/load", headers={"X-ResearchPath-Token": "wrong"})
    assert missing.status_code == wrong.status_code == 403

    authorized = unauthenticated.post("/api/v1/demo/load", headers={"X-ResearchPath-Token": token})
    assert authorized.status_code == 201, authorized.text


def test_data_exposing_get_endpoints_require_session_token() -> None:
    unauthenticated = TestClient(app)
    sensitive = [
        "/api/v1/datasets/dataset_x",
        "/api/v1/datasets/dataset_x/quality-runs",
        "/api/v1/datasets/dataset_x/sample-versions",
        "/api/v1/datasets/dataset_x/measurement",
        "/api/v1/datasets/dataset_x/measurements/1/empirical-analyses/empirical_1/segments/summary",
        "/api/v1/datasets/dataset_x/measurements/1/empirical-analyses/empirical_1/export",
        "/api/v1/analyses/run_x",
        "/api/v1/analyses/run_x/result",
        "/api/v1/analyses/run_x/export",
        "/api/v1/advanced-analyses/advanced_x",
        "/api/v1/advanced-analyses/advanced_x/result",
        "/api/v1/advanced-analyses/advanced_x/export",
        "/api/v1/projects/default/study-context",
    ]
    for path in sensitive:
        response = unauthenticated.get(path)
        assert response.status_code == 403, f"{path} should require a session token"

    wrong = unauthenticated.get("/api/v1/analyses/run_x/result", headers={"X-ResearchPath-Token": "wrong"})
    assert wrong.status_code == 403


def test_public_get_endpoints_stay_open() -> None:
    unauthenticated = TestClient(app)
    assert unauthenticated.get("/api/v1/health").status_code == 200
    assert unauthenticated.get("/api/v1/demo").status_code == 200
    assert unauthenticated.get("/api/v1/demo/data/longitudinal").status_code == 200
    assert unauthenticated.get("/api/v1/advanced-analyses/capabilities").status_code == 200
    assert unauthenticated.get("/api/v1/analyses/run_x/progress").status_code == 404
    assert unauthenticated.get("/api/v1/session").status_code == 403


def test_public_allowlist_uses_exact_routes_and_rejects_prefix_expansion() -> None:
    unauthenticated = TestClient(app)
    assert unauthenticated.get("/api/v1/demo-hidden").status_code == 403
    assert unauthenticated.get("/api/v1/demo/data/longitudinal/extra").status_code == 403
    assert unauthenticated.request("TRACE", "/api/v1/datasets/dataset_x").status_code == 403


def test_docs_and_openapi_require_session_token() -> None:
    unauthenticated = TestClient(app)
    assert unauthenticated.get("/api/openapi.json").status_code == 403
    assert unauthenticated.get("/api/docs").status_code == 403
    authorized = TestClient(
        app,
        headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
    )
    assert authorized.get("/api/openapi.json").status_code == 200
    assert authorized.get("/api/docs").status_code == 200


def test_settings_fail_closed_on_empty_or_short_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESEARCHPATH_BOOTSTRAP_TOKEN", raising=False)
    for variable in ("RESEARCHPATH_SESSION_TOKEN", "RESEARCHPATH_BOOTSTRAP_TOKEN"):
        monkeypatch.setenv(variable, "")
        with pytest.raises(ValueError, match=variable):
            get_settings()
        monkeypatch.setenv(variable, "too-short")
        with pytest.raises(ValueError, match=variable):
            get_settings()
        monkeypatch.delenv(variable)


def test_middleware_fails_closed_when_configured_with_empty_token() -> None:
    settings = replace(get_settings(), session_token="", session_bootstrap_token="")
    client = TestClient(create_app(settings))
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/datasets/dataset_x").status_code == 403
    assert client.get("/api/openapi.json").status_code == 403


def test_unhandled_errors_do_not_expose_exception_type_or_path() -> None:
    settings = get_settings()
    application = create_app(settings)

    @application.get("/api/v1/crash")
    def crash() -> None:
        raise RuntimeError(r"failure while reading C:\Users\someone\secret.csv")

    client = TestClient(
        application,
        headers={"X-ResearchPath-Token": settings.session_token},
        raise_server_exceptions=False,
    )
    response = client.get("/api/v1/crash")
    assert response.status_code == 500
    body = response.json()["detail"]
    assert body["code"] == "INTERNAL_ERROR"
    assert body["details"] is None
    assert "RuntimeError" not in response.text
    assert r"C:\Users\someone\secret.csv" not in response.text


def test_empirical_report_path_rejects_traversal_and_invalid_identifiers() -> None:
    settings = get_settings()
    from app.services.empirical_analysis import EmpiricalAnalysisError

    for dataset_id in ("../other_dataset", "..", "dataset/../x", "dataset..", "..\\dataset"):
        with pytest.raises(EmpiricalAnalysisError):
            empirical_report_path(dataset_id, 1, "empirical_1", settings)
    for report_id in ("../../report", "empirical_../x", "EMPIRICAL_1", "empirical_1/x"):
        with pytest.raises(EmpiricalAnalysisError):
            empirical_report_path("dataset_x", 1, report_id, settings)


def test_empirical_segment_endpoint_rejects_invalid_identifiers() -> None:
    authorized = TestClient(
        app,
        headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
    )
    invalid = authorized.get(
        "/api/v1/datasets/dataset!x/measurements/1/empirical-analyses/empirical_BAD/segments/summary"
    )
    assert invalid.status_code == 400
    missing = authorized.get(
        "/api/v1/datasets/dataset_x/measurements/1/empirical-analyses/empirical_1/segments/summary"
    )
    assert missing.status_code == 404


def test_settings_generate_distinct_session_tokens() -> None:
    assert get_settings().session_token != get_settings().session_token
    assert get_settings().session_bootstrap_token != get_settings().session_bootstrap_token


def test_formula_like_user_text_is_exported_as_literal() -> None:
    dangerous = ["=1+1", "+SUM(A1:A2)", "-2+3", "@cmd", "\tformula", "\rformula"]
    assert [escape_spreadsheet_formula(value) for value in dangerous] == [
        "'" + value for value in dangerous
    ]
    assert escape_spreadsheet_formula("ordinary label") == "ordinary label"
    assert escape_spreadsheet_formula(12.5) == 12.5

    workbook = Workbook()
    active_sheet = workbook.active
    if active_sheet is not None:
        workbook.remove(active_sheet)
    _append_sheet(workbook, "安全", [["标签"], ["=1+1"], ["  @cmd"]])
    sheet = workbook["安全"]
    assert sheet["A2"].value == "'=1+1"
    assert sheet["A3"].value == "'  @cmd"
    assert sheet["A2"].data_type != "f"
    assert sheet["A3"].data_type != "f"


def test_persisted_paths_are_portable_relative_capabilities(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    owned = state_root / "projects" / "default" / "runs" / "run-1"
    owned.mkdir(parents=True)
    assert safe_relative_path("projects/default/runs/run-1/result.json").as_posix() == (
        "projects/default/runs/run-1/result.json"
    )
    assert (
        resolve_owned_path(
            state_root,
            "projects/default/runs/run-1/result.json",
            expected_parent=owned,
            expected_name="result.json",
        )
        == owned / "result.json"
    )
    for value in (
        "../outside.json",
        "projects//result.json",
        "projects/./result.json",
        r"..\outside.json",
        r"C:\outside.json",
        r"\\server\share\x",
    ):
        with pytest.raises(UnsafePathError):
            safe_relative_path(value)

    nested = owned / "nested"
    nested.mkdir()
    with pytest.raises(UnsafePathError, match="expected object directory"):
        resolve_owned_path(
            state_root,
            "projects/default/runs/run-1/nested/result.json",
            expected_parent=owned,
            expected_name="result.json",
        )


def test_windows_reparse_attribute_is_rejected_without_following_target() -> None:
    class ReparsePoint:
        def lstat(self):
            return SimpleNamespace(st_file_attributes=0x400)

        def is_symlink(self) -> bool:
            return False

    assert is_link_or_reparse_point(ReparsePoint()) is True  # type: ignore[arg-type]


def test_json_read_retries_a_transient_windows_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TransientlyLockedPath:
        attempts = 0

        def read_text(self, *, encoding: str) -> str:
            assert encoding == "utf-8"
            self.attempts += 1
            if self.attempts == 1:
                raise PermissionError("file is temporarily locked")
            return '{"ok": true}'

    path = TransientlyLockedPath()
    sleep_calls: list[float] = []
    monkeypatch.setattr(repository_io.time, "sleep", sleep_calls.append)

    assert repository_io._read_json_safe(path) == {"ok": True}  # type: ignore[arg-type]
    assert path.attempts == 2
    assert sleep_calls == [0.01]


def test_json_read_reraises_after_windows_lock_retry_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class PermanentlyLockedPath:
        attempts = 0

        def read_text(self, *, encoding: str) -> str:
            assert encoding == "utf-8"
            self.attempts += 1
            raise PermissionError("file remains locked")

    path = PermanentlyLockedPath()
    sleep_calls: list[float] = []
    monkeypatch.setattr(repository_io.time, "sleep", sleep_calls.append)

    with pytest.raises(PermissionError, match="file remains locked"):
        repository_io._read_json_safe(path)  # type: ignore[arg-type]

    assert path.attempts == 10
    assert sleep_calls == [0.01] * 9


def test_atomic_json_write_retries_a_transient_windows_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "document.json"
    replace_attempts = 0
    original_replace = repository_io.os.replace

    def transiently_locked_replace(source: Path, target: Path) -> None:
        nonlocal replace_attempts
        replace_attempts += 1
        if replace_attempts == 1:
            raise PermissionError("destination is temporarily locked")
        original_replace(source, target)

    sleep_calls: list[float] = []
    monkeypatch.setattr(repository_io.os, "replace", transiently_locked_replace)
    monkeypatch.setattr(repository_io.time, "sleep", sleep_calls.append)

    repository_io._write_json_atomic(destination, {"ok": True})

    assert repository_io._read_json_safe(destination) == {"ok": True}
    assert replace_attempts == 2
    assert sleep_calls == [0.01]
    assert list(tmp_path.glob("document.json.*.tmp")) == []


def test_atomic_json_write_cleans_up_after_windows_lock_retry_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "document.json"
    replace_attempts = 0

    def permanently_locked_replace(_source: Path, _target: Path) -> None:
        nonlocal replace_attempts
        replace_attempts += 1
        raise PermissionError("destination remains locked")

    sleep_calls: list[float] = []
    monkeypatch.setattr(repository_io.os, "replace", permanently_locked_replace)
    monkeypatch.setattr(repository_io.time, "sleep", sleep_calls.append)

    with pytest.raises(PermissionError, match="destination remains locked"):
        repository_io._write_json_atomic(destination, {"ok": True})

    assert replace_attempts == 20
    assert sleep_calls == [0.01 * attempt for attempt in range(1, 20)]
    assert not destination.exists()
    assert list(tmp_path.glob("document.json.*.tmp")) == []


def test_remove_path_tree_clears_windows_readonly_before_deleting(tmp_path: Path) -> None:
    target = tmp_path / "run_tree"
    nested = target / "nested"
    nested.mkdir(parents=True)
    raw = nested / "raw.csv"
    raw.write_text("a,b\n1,2\n", encoding="utf-8")
    os.chmod(raw, stat.S_IREAD)
    os.chmod(nested, stat.S_IREAD)

    remove_path_tree(target)

    assert not target.exists()
    assert not raw.exists()


def test_remove_path_tree_ignores_missing_target(tmp_path: Path) -> None:
    remove_path_tree(tmp_path / "does_not_exist")


def test_empirical_result_bundle_schema_gates_persisted_reports() -> None:
    settings = get_settings()
    schema_path = settings.empirical_result_schema_path
    assert schema_path.is_file()

    from app.contracts import ContractValidationError, validate_contract

    damaged = {
        "schemaVersion": "1.0.0",
        "reportId": "empirical_0123456789abcdef",
        "warnings": [],
    }
    with pytest.raises(ContractValidationError):
        validate_contract(damaged, schema_path)

    valid = {
        "schemaVersion": "1.0.0",
        "reportId": "empirical_0123456789abcdef",
        "datasetId": "dataset_0123456789abcdef",
        "measurementVersionId": "measurement_0123456789abcdef",
        "jobStatus": "completed",
        "estimationStatus": "succeeded",
        "inferenceStatus": "reliable",
        "publicationEligibility": "conditional",
        "sample": {"rowCount": 260},
        "options": {"factorCount": 3},
        "warnings": [
            {
                "code": "ASSOCIATIONAL_ONLY",
                "severity": "warning",
                "message": "解释边界说明",
            }
        ],
        "provenance": {"engine": "ResearchPath empirical base-R engine"},
        "descriptives": [
            {
                "label": "x",
                "n": 260,
                "missing": 0,
                "mean": 3.2,
                "sd": 1.1,
                "minimum": 1.0,
                "maximum": 5.0,
            }
        ],
    }
    validate_contract(valid, schema_path)
