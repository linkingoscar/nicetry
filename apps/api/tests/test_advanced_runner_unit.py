from __future__ import annotations

import itertools
import json
import threading
from dataclasses import replace
from pathlib import Path
from typing import Callable, cast

import pandas as pd
import pytest
from _advanced_runner_test_helpers import _Process, _Repository

from app.advanced_contracts import (
    EffectSize,
    ExperimentalDesignSpec,
    ImputationVariable,
    MultipleImputationSpec,
    PowerAnalysisSpec,
    WithinFactor,
)
from app.services import advanced_runner, process_ownership, subprocess_runtime
from app.services.advanced_runner import (
    AdvancedExecutionError,
    _canonical_advanced_hash,
    _normalize_optional_presentation_assets,
    _translate_r_failure,
)
from app.services.dataset_repository import DatasetRepository
from app.services.repository_io import JsonObject
from app.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def mocked_process_job(monkeypatch):
    # This module replaces Popen with a protocol fake; native tree ownership is
    # exercised separately with real children in test_windows_process_job.py.
    class FakeJob:
        def __init__(self, _process):
            pass

        def close(self):
            pass

    monkeypatch.setattr(subprocess_runtime, "WindowsProcessJob", FakeJob)


def _settings(tmp_path: Path) -> Settings:
    rscript_path = tmp_path / "Rscript.exe"
    rscript_path.write_text("placeholder", encoding="utf-8")
    return replace(
        get_settings(),
        state_root=tmp_path / "workspace",
        rscript_path=rscript_path,
        r_library_path=tmp_path / "r-library",
    )


def _power_spec() -> PowerAnalysisSpec:
    return PowerAnalysisSpec(
        analysis_id="power_runner_unit",
        name="Power runner unit test",
        family="power_analysis",
        design_family="regression",
        method="analytic",
        solve_for="sample_size",
        effect_size=EffectSize(metric="cohens_f2", value=0.15),
        predictors=3,
    )


def _run(
    spec: PowerAnalysisSpec,
    repository: _Repository,
    settings: Settings,
    work_dir: Path,
    cancel_event: threading.Event,
    monkeypatch: pytest.MonkeyPatch,
    process: _Process,
    engine_result: JsonObject | None = None,
    progress_callback: Callable[[JsonObject], None] = lambda _progress: None,
    on_started: Callable[[int], None] | None = None,
) -> JsonObject:
    work_dir.mkdir()

    def popen(arguments: list[str], **kwargs: object) -> _Process:
        if engine_result is not None:
            Path(arguments[-1]).write_text(json.dumps(engine_result), encoding="utf-8")
        stdout_handle = kwargs.get("stdout")
        if hasattr(stdout_handle, "write"):
            stdout_handle.write(process.stdout.getvalue())  # type: ignore[union-attr]
            stdout_handle.flush()  # type: ignore[union-attr]
        return process

    monkeypatch.setattr(subprocess_runtime.subprocess, "Popen", popen)
    monkeypatch.setattr(advanced_runner, "normalize_and_validate", lambda document, *_args: document)
    return advanced_runner.execute_cancellable_advanced_analysis(
        spec,
        cast(DatasetRepository, repository),
        "advanced_runner_unit",
        work_dir,
        settings,
        cancel_event,
        progress_callback,
        on_started=on_started,
    )


def test_power_runner_builds_result_and_normalizes_optional_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    started: list[int] = []
    result = _run(
        _power_spec(),
        _Repository(settings),
        settings,
        tmp_path / "work",
        threading.Event(),
        monkeypatch,
        _Process([0]),
        {
            "familyResult": {
                "family": "power_analysis",
                "solveFor": "sample_size",
                "solvedValue": 77,
                "achievedPower": 0.801765521057435,
                "parameters": {
                    "alpha": 0.05,
                    "alternative": "two_sided",
                    "groups": 1,
                    "predictors": 3,
                    "effectSizeMetric": "cohens_f2",
                    "solvedValueMetric": "total_sample_size",
                    "solvedEffectSize": None,
                    "allocationRatio": None,
                },
            },
            "apaReports": ["Power analysis complete.", [], None],
            "plots": [],
            "provenance": {"engine": "mock"},
        },
        on_started=started.append,
    )

    assert started == [4242]
    assert result["run"]["family"] == "power_analysis"
    assert result["provenance"]["engine"] == "mock"
    assert result["provenance"]["dataSha256"] is None
    assert result["provenance"]["seed"] == 20260714
    assert result["provenance"]["specVersion"] == "0.1.0"
    assert result["provenance"]["family"] == "power_analysis"
    assert result["provenance"]["specHash"] == result["run"]["specHash"]
    assert result["apaReports"] == ["Power analysis complete."]


def test_optional_assets_may_be_absent_and_hashes_ignore_string_list_order() -> None:
    engine_result: JsonObject = {}
    _normalize_optional_presentation_assets(engine_result)

    first = _power_spec().model_copy(update={"assumptions": ["normality", "linearity"]})
    second = _power_spec().model_copy(update={"assumptions": ["linearity", "normality"]})
    assert _canonical_advanced_hash(first) == _canonical_advanced_hash(second)


def test_input_payload_carries_progress_and_cancel_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    work_dir = tmp_path / "work"
    result = _run(
        _power_spec(),
        _Repository(settings),
        settings,
        work_dir,
        threading.Event(),
        monkeypatch,
        _Process([0]),
        {
            "familyResult": {"family": "power_analysis", "solveFor": "sample_size"},
            "apaReports": [],
            "plots": [],
            "provenance": {"engine": "mock"},
        },
    )

    assert result["run"]["family"] == "power_analysis"
    payload = json.loads((work_dir / "input.json").read_text(encoding="utf-8"))
    assert payload["progressPath"] == str(work_dir / "progress.json")
    assert payload["cancelPath"] == str(work_dir / "cancel.marker")


def test_wide_repeated_measurements_are_transformed_before_running_r(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    dataset = {
        "variables": [
            {"originalName": "subject", "id": "subject"},
            {"originalName": "score_t1", "id": "score_t1"},
            {"originalName": "score_t2", "id": "score_t2"},
        ],
        "originalFile": {"sha256": "dataset-sha"},
    }
    repository = _Repository(settings, dataset)
    dataframe = pd.DataFrame(
        {"subject": ["s1", "s2"], "score_t1": [1.0, 2.0], "score_t2": [3.0, 4.0]}
    )
    monkeypatch.setattr(advanced_runner, "resolve_normalized_dataset_path", lambda *_args: tmp_path)
    monkeypatch.setattr(advanced_runner.pd, "read_parquet", lambda _path: dataframe)
    spec = ExperimentalDesignSpec(
        analysis_id="wide_runner_unit",
        name="Wide repeated measurements",
        dataset_version_id="dataset_runner_unit",
        family="experimental_design",
        design_type="repeated_measures",
        data_layout="wide",
        outcome_ids=["outcome"],
        subject_id="subject",
        within_factors=[
            WithinFactor(
                id="time",
                name="Time",
                levels=["T1", "T2"],
                columns={"T1": "score_t1", "T2": "score_t2"},
            )
        ],
    )
    observed_input: dict[str, object] = {}

    def popen(arguments: list[str], **_kwargs: object) -> _Process:
        observed_input.update(json.loads(Path(arguments[-2]).read_text(encoding="utf-8")))
        Path(arguments[-1]).write_text(
            json.dumps({"familyResult": {}, "apaReports": [], "plots": []})
        )
        return _Process([0])

    work_dir = tmp_path / "wide-work"
    work_dir.mkdir()
    monkeypatch.setattr(subprocess_runtime.subprocess, "Popen", popen)
    monkeypatch.setattr(advanced_runner, "normalize_and_validate", lambda document, *_args: document)
    result = advanced_runner.execute_cancellable_advanced_analysis(
        spec,
        cast(DatasetRepository, repository),
        "wide_runner_unit",
        work_dir,
        settings,
        threading.Event(),
        lambda _progress: None,
    )

    transformed = pd.read_csv(cast(str, observed_input["dataPath"]))
    input_spec = cast(dict[str, object], observed_input["spec"])
    assert input_spec["dataLayout"] == "long"
    within_factors = cast(list[dict[str, object]], input_spec["withinFactors"])
    assert within_factors[0]["columns"] == {}
    assert transformed.columns.tolist() == ["subject", "time", "outcome"]
    assert transformed["time"].tolist() == ["T1", "T1", "T2", "T2"]
    assert result["provenance"]["wideToLong"] == {
        "action": "wide_to_long_transformation",
        "inputColumns": ["score_t1", "score_t2"],
        "withinFactor": "time",
        "levels": ["T1", "T2"],
        "outputRows": 4,
    }


def test_runner_rejects_missing_runtime_and_reports_r_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    missing_settings = replace(settings, rscript_path=tmp_path / "missing-rscript.exe")
    with pytest.raises(AdvancedExecutionError, match="Rscript 不存在") as missing_runtime:
        _run(
            _power_spec(),
            _Repository(missing_settings),
            missing_settings,
            tmp_path / "missing-runtime-work",
            threading.Event(),
            monkeypatch,
            _Process([0]),
        )
    assert missing_runtime.value.code == "RSCRIPT_NOT_FOUND"

    with pytest.raises(AdvancedExecutionError, match="高级统计执行失败") as failed_r:
        _run(
            _power_spec(),
            _Repository(settings),
            settings,
            tmp_path / "failed-r-work",
            threading.Event(),
            monkeypatch,
            _Process([1], stdout="R error details"),
        )
    assert failed_r.value.code == "R_EXECUTION_FAILED"
    assert failed_r.value.details == "R error details"
    assert failed_r.value.remediation is not None


@pytest.mark.parametrize(
    ("raw_failure", "code", "message_fragment", "remediation_fragment"),
    [
        (
            "EXPERIMENT_EMPTY_CELL",
            "EXPERIMENT_EMPTY_CELL",
            "空单元格",
            "补充数据",
        ),
        (
            "POWER_MONTE_CARLO_TOO_MANY_FAILURES",
            "POWER_MONTE_CARLO_TOO_MANY_FAILURES",
            "有效复制数不足",
            "失败率",
        ),
        (
            "MEASUREMENT_INSUFFICIENT_COMPLETE_OBSERVATIONS",
            "MEASUREMENT_INSUFFICIENT_COMPLETE_OBSERVATIONS",
            "完整案例少于 20",
            "处理缺失",
        ),
        (
            "MEASUREMENT_PACKAGE_NOT_INSTALLED: mirt",
            "MEASUREMENT_PACKAGE_NOT_INSTALLED",
            "缺少统计软件依赖",
            "安装并锁定",
        ),
        (
            "MI_RESOURCE_BUDGET_EXCEEDED",
            "MI_RESOURCE_BUDGET_EXCEEDED",
            "超过资源预算",
            "降低插补次数",
        ),
        (
            "MLM_NONCONVERGENCE",
            "MLM_NONCONVERGENCE",
            "未收敛",
            "不要将未收敛模型的系数用于结论",
        ),
    ],
)
def test_r_failure_translation_preserves_code_diagnostics_and_actionable_remediation(
    raw_failure: str,
    code: str,
    message_fragment: str,
    remediation_fragment: str,
) -> None:
    error = _translate_r_failure(raw_failure)
    assert error.code == code
    assert message_fragment in error.message
    assert error.details == raw_failure
    assert error.remediation is not None
    assert remediation_fragment in error.remediation


def test_runner_cancels_and_times_out_by_terminating_the_process_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    cancelled = threading.Event()
    cancelled.set()
    taskkill_calls: list[list[str]] = []
    monkeypatch.setattr(
        process_ownership.subprocess,
        "run",
        lambda arguments, **_kwargs: taskkill_calls.append(arguments),
    )

    with pytest.raises(AdvancedExecutionError, match="已由用户取消") as cancellation:
        _run(
            _power_spec(),
            _Repository(settings),
            settings,
            tmp_path / "cancel-work",
            cancelled,
            monkeypatch,
            _Process([None]),
        )
    assert cancellation.value.code == "ANALYSIS_CANCELLED"
    assert taskkill_calls == [["taskkill", "/F", "/T", "/PID", "4242"]]
    assert (tmp_path / "cancel-work" / "cancel.marker").is_file()

    monotonic = itertools.cycle([0.0, 0.0, advanced_runner.ADVANCED_TIMEOUT_SECONDS + 1.0])
    monkeypatch.setattr(subprocess_runtime.time, "monotonic", lambda: next(monotonic))
    with pytest.raises(AdvancedExecutionError, match="超过 180 秒期限") as timeout:
        _run(
            _power_spec(),
            _Repository(settings),
            settings,
            tmp_path / "timeout-work",
            threading.Event(),
            monkeypatch,
            _Process([None]),
        )
    assert timeout.value.code == "ANALYSIS_TIMEOUT"
    assert len(taskkill_calls) == 2


def test_runner_forwards_new_progress_updates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    updates: list[JsonObject] = []
    work_dir = tmp_path / "progress-work"
    work_dir.mkdir()

    def popen(arguments: list[str], **_kwargs: object) -> _Process:
        Path(arguments[-2]).with_name("progress.json").write_text(
            json.dumps({"stage": "estimating", "progress": 0.5}), encoding="utf-8"
        )
        Path(arguments[-1]).write_text(
            json.dumps({"familyResult": {}, "apaReports": [], "plots": []})
        )
        return _Process([None, 0])

    monkeypatch.setattr(subprocess_runtime.subprocess, "Popen", popen)
    monkeypatch.setattr(advanced_runner, "normalize_and_validate", lambda document, *_args: document)
    monkeypatch.setattr(subprocess_runtime.time, "sleep", lambda _seconds: None)
    advanced_runner.execute_cancellable_advanced_analysis(
        _power_spec(),
        cast(DatasetRepository, _Repository(settings)),
        "progress_runner_unit",
        work_dir,
        settings,
        threading.Event(),
        updates.append,
    )
    assert updates == [{"stage": "estimating", "progress": 0.5}]


def test_analysis_dataframe_and_imputation_artifacts_enforce_data_integrity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    dataset = {
        "variables": [{"originalName": "required", "id": "required_id"}],
        "originalFile": {"sha256": "dataset-sha"},
    }
    repository = _Repository(settings, dataset)
    monkeypatch.setattr(advanced_runner, "resolve_normalized_dataset_path", lambda *_args: tmp_path)
    monkeypatch.setattr(
        advanced_runner.pd, "read_parquet", lambda _path: pd.DataFrame({"other": [1]})
    )
    with pytest.raises(AdvancedExecutionError, match="数据变量存储列不存在") as missing_column:
        advanced_runner._analysis_dataframe(
            cast(DatasetRepository, repository), "dataset_runner_unit"
        )
    assert missing_column.value.code == "DATA_COLUMN_NOT_FOUND"

    spec = MultipleImputationSpec(
        analysis_id="imputation_runner_unit",
        name="Imputation artifact test",
        dataset_version_id="dataset_runner_unit",
        family="multiple_imputation",
        imputations=5,
        iterations=5,
        variables=[ImputationVariable(variable_id="value", method="pmm")],
    )
    source_root = tmp_path / "imputation-work"
    source_root.mkdir()
    for index in range(1, 6):
        (source_root / f"imputation-{index:03d}.csv").write_text(
            f"value\\n{index}\\n", encoding="utf-8"
        )
    artifacts = advanced_runner._persist_imputations(
        spec, "imputation_run", source_root, cast(DatasetRepository, repository)
    )
    assert [item["imputation"] for item in artifacts] == [1, 2, 3, 4, 5]
    assert all((settings.state_root / item["path"]).is_file() for item in artifacts)

    incomplete_root = tmp_path / "incomplete-imputation-work"
    incomplete_root.mkdir()
    with pytest.raises(AdvancedExecutionError, match="未生成完整") as incomplete:
        advanced_runner._persist_imputations(
            spec, "incomplete_run", incomplete_root, cast(DatasetRepository, repository)
        )
    assert incomplete.value.code == "IMPUTATION_INCOMPLETE"
