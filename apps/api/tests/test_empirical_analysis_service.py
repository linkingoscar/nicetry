from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from threading import Event
from typing import cast

import pandas as pd
import pytest

from app.services import empirical_analysis as ea
from app.services.empirical_options_validator import EmpiricalAnalysisError
from app.services.r_engine import AnalysisCancelled, EngineExecutionError
from app.services.r_workers import (
    RWorkerCancelled,
    RWorkerPool,
    RWorkerTaskError,
    RWorkerUnavailable,
)
from app.settings import get_settings


class _FakeRepository:
    def __init__(self, sample: dict[str, object] | None = None) -> None:
        self.sample = sample
        self.sample_cases = pd.DataFrame({"caseIndex": [1, 2], "included": [True, True]})

    def get_dataset(self, dataset_id: str) -> dict[str, object]:
        return {
            "id": dataset_id,
            "projectId": "default",
            "originalFile": {"sha256": "a" * 64},
        }

    def get_measurement(self, dataset_id: str, version: int) -> dict[str, object]:
        return {"id": "measurement_v1", "datasetId": dataset_id}

    def get_analysis_sample(self, dataset_id: str, sample_id: str) -> dict[str, object]:
        assert self.sample is not None
        return self.sample

    def get_analysis_sample_case_path(self, dataset_id: str, sample_id: str) -> Path:
        return Path("unused.parquet")


def _settings(tmp_path: Path):
    return replace(get_settings(), state_root=tmp_path / "state")


def _fake_fallback(output_path: Path, returncode: int = 0, message: str = "") -> object:
    def fallback(**_: object) -> tuple[int, str, str]:
        output_path.write_text(json.dumps({"schemaVersion": "0.3.0"}), encoding="utf-8")
        return returncode, message, message

    return fallback


def _neutralize_service_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.academic_interpreter as academic_interpreter

    def fail_interpretation(*_: object, **__: object) -> object:
        raise RuntimeError("no interpretation in unit test")

    monkeypatch.setattr(ea, "prepare_empirical_data", lambda dataset, measurement, settings: (pd.DataFrame({"x": [1, 2, 3]}), {"constructs": []}))
    monkeypatch.setattr(ea, "validate_empirical_options", lambda metadata, options: None)
    monkeypatch.setattr(ea, "apply_status_model", lambda report: None)
    monkeypatch.setattr(ea, "normalize_and_validate", lambda report, schema_path: report)
    monkeypatch.setattr(
        academic_interpreter,
        "generate_interpretation_assets",
        fail_interpretation,
    )


def test_run_empirical_analysis_happy_path_without_sample(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _neutralize_service_boundaries(monkeypatch)
    repository = _FakeRepository()
    settings = _settings(tmp_path)
    progress: list[dict[str, object]] = []
    work_dir = tmp_path / "work"
    monkeypatch.setattr(
        ea,
        "_run_rscript_fallback",
        _fake_fallback(work_dir / "output.json"),
    )

    report = ea.run_empirical_analysis(
        "dataset_a",
        1,
        {},
        repository,  # type: ignore[arg-type]
        settings,
        progress_callback=progress.append,
        work_dir=work_dir,
    )
    assert report["schemaVersion"] == "0.3.0"
    assert progress[0]["stage"] == "preparing_data"
    assert progress[-1]["stage"] == "persisting_report"
    assert (settings.state_root / "projects/default/datasets/dataset_a/measurement/v1/empirical").exists()


def test_run_empirical_analysis_applies_sample_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _neutralize_service_boundaries(monkeypatch)
    sample = {
        "id": "sample_v1",
        "datasetSha256": "a" * 64,
        "sampleHash": "b" * 64,
        "qualityRunId": "quality_1",
        "includedCount": 2,
        "excludedCount": 1,
    }
    repository = _FakeRepository(sample=sample)
    settings = _settings(tmp_path)
    work_dir = tmp_path / "work"
    monkeypatch.setattr(ea, "_run_rscript_fallback", _fake_fallback(work_dir / "output.json"))
    monkeypatch.setattr(ea.pd, "read_parquet", lambda _path: repository.sample_cases)

    report = ea.run_empirical_analysis(
        "dataset_a",
        1,
        {"sampleVersionId": "sample_v1"},
        repository,  # type: ignore[arg-type]
        settings,
        work_dir=work_dir,
    )
    assert report["sampleVersion"]["sampleVersionId"] == "sample_v1"


def test_run_empirical_analysis_sample_guards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _neutralize_service_boundaries(monkeypatch)
    settings = _settings(tmp_path)
    work_dir = tmp_path / "work"
    monkeypatch.setattr(ea, "_run_rscript_fallback", _fake_fallback(work_dir / "output.json"))

    def patch_sample_cases(repository: _FakeRepository) -> None:
        monkeypatch.setattr(ea.pd, "read_parquet", lambda _path: repository.sample_cases)

    mismatched = _FakeRepository(sample={"id": "sample_v1", "datasetSha256": "f" * 64})
    with pytest.raises(EmpiricalAnalysisError, match="SHA-256"):
        ea.run_empirical_analysis(
            "dataset_a", 1, {"sampleVersionId": "sample_v1"},
            mismatched,  # type: ignore[arg-type]
            settings, work_dir=work_dir,
        )

    bad_columns = _FakeRepository(sample={"id": "sample_v1", "datasetSha256": "a" * 64})
    bad_columns.sample_cases = pd.DataFrame({"caseIndex": [1]})
    patch_sample_cases(bad_columns)
    with pytest.raises(EmpiricalAnalysisError, match="caseIndex/included"):
        ea.run_empirical_analysis(
            "dataset_a", 1, {"sampleVersionId": "sample_v1"},
            bad_columns,  # type: ignore[arg-type]
            settings, work_dir=work_dir,
        )

    out_of_range = _FakeRepository(sample={"id": "sample_v1", "datasetSha256": "a" * 64})
    out_of_range.sample_cases = pd.DataFrame({"caseIndex": [1, 9], "included": [True, True]})
    patch_sample_cases(out_of_range)
    with pytest.raises(EmpiricalAnalysisError, match="超出派生数据范围"):
        ea.run_empirical_analysis(
            "dataset_a", 1, {"sampleVersionId": "sample_v1"},
            out_of_range,  # type: ignore[arg-type]
            settings, work_dir=work_dir,
        )


def test_worker_unavailable_falls_back_and_task_error_translates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _neutralize_service_boundaries(monkeypatch)
    settings = _settings(tmp_path)
    work_dir = tmp_path / "work"
    repository = _FakeRepository()

    class UnavailablePool:
        def run(self, **_: object) -> None:
            raise RWorkerUnavailable("worker down")

    monkeypatch.setattr(ea, "_run_rscript_fallback", _fake_fallback(work_dir / "output.json"))
    report = ea.run_empirical_analysis(
        "dataset_a", 1, {}, repository,  # type: ignore[arg-type]
        settings, worker_pool=cast(RWorkerPool, UnavailablePool()), work_dir=work_dir,
    )
    assert report["schemaVersion"] == "0.3.0"

    class FailingPool:
        def run(self, **_: object) -> None:
            raise RWorkerTaskError("R blew up")

    with pytest.raises(EngineExecutionError):
        ea.run_empirical_analysis(
            "dataset_a", 1, {}, repository,  # type: ignore[arg-type]
            settings, worker_pool=cast(RWorkerPool, FailingPool()), work_dir=work_dir,
        )

    class CancelledPool:
        def run(self, **_: object) -> None:
            raise RWorkerCancelled("cancelled")

    with pytest.raises(AnalysisCancelled):
        ea.run_empirical_analysis(
            "dataset_a", 1, {}, repository,  # type: ignore[arg-type]
            settings, worker_pool=cast(RWorkerPool, CancelledPool()), work_dir=work_dir,
        )


def test_fallback_returns_progress_and_nonzero(
    tmp_path: Path,
) -> None:
    script = tmp_path / "script.py"
    script.write_text(
        "import json, pathlib, time\n"
        f"pathlib.Path(r'{tmp_path / 'progress.json'}').write_text(json.dumps({{'stage':'running'}}))\n"
        "time.sleep(0.5)\n",
        encoding="utf-8",
    )
    progress: list[dict[str, object]] = []
    returncode, stdout, stderr = ea._run_rscript_fallback(
        command=[sys.executable, str(script)],
        environment=os.environ.copy(),
        settings=_settings(tmp_path),
        cancel_event=None,
        cancel_path=tmp_path / "cancel",
        progress_path=tmp_path / "progress.json",
        progress_callback=progress.append,
        timeout=10,
        stdout_log=tmp_path / "stdout.log",
        stderr_log=tmp_path / "stderr.log",
    )
    assert returncode == 0, (stdout, stderr)
    assert progress and progress[0]["stage"] == "running"
    assert stdout == ""

    script.write_text("import sys; sys.exit(3)", encoding="utf-8")
    returncode, stdout, stderr = ea._run_rscript_fallback(
        command=[sys.executable, str(script)],
        environment=os.environ.copy(),
        settings=_settings(tmp_path),
        cancel_event=None,
        cancel_path=tmp_path / "cancel",
        progress_path=tmp_path / "progress.json",
        progress_callback=None,
        timeout=10,
        stdout_log=tmp_path / "stdout.log",
        stderr_log=tmp_path / "stderr.log",
    )
    assert returncode == 3


def test_fallback_cancels_and_times_out(tmp_path: Path) -> None:
    script = tmp_path / "sleep.py"
    script.write_text("import time; time.sleep(10)", encoding="utf-8")
    settings = _settings(tmp_path)

    cancel_event = Event()
    cancel_event.set()
    with pytest.raises(AnalysisCancelled):
        ea._run_rscript_fallback(
            command=[sys.executable, str(script)],
            environment=os.environ.copy(),
            settings=settings,
            cancel_event=cancel_event,
            cancel_path=tmp_path / "cancel",
            progress_path=tmp_path / "progress.json",
            progress_callback=None,
            timeout=10,
            stdout_log=tmp_path / "stdout.log",
            stderr_log=tmp_path / "stderr.log",
        )

    (tmp_path / "cancel").unlink(missing_ok=True)
    with pytest.raises(EngineExecutionError, match="超过运行时限"):
        ea._run_rscript_fallback(
            command=[sys.executable, str(script)],
            environment=os.environ.copy(),
            settings=settings,
            cancel_event=None,
            cancel_path=tmp_path / "cancel",
            progress_path=tmp_path / "progress.json",
            progress_callback=None,
            timeout=0.2,
            stdout_log=tmp_path / "stdout.log",
            stderr_log=tmp_path / "stderr.log",
        )
