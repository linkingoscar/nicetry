from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from app.advanced_contracts import (
    AdvancedAnalysisSpec,
    ExperimentalDesignSpec,
    LongitudinalModelSpec,
    MultilevelModelSpec,
    MultipleImputationSpec,
    QuestionnaireMeasurementSpec,
)
from app.contracts import file_sha256, validate_contract
from app.services.dataset_repository import DatasetRepository
from app.services.owned_resources import resolve_normalized_dataset_path
from app.services.repository_io import JsonObject, _read_json_safe, safe_identifier
from app.settings import Settings

ADVANCED_TIMEOUT_SECONDS = 180


class AdvancedExecutionError(ValueError):
    def __init__(self, code: str, message: str, details: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


_R_FAILURES: tuple[tuple[str, str], ...] = (
    ("EXPERIMENT_MISSING_SUBJECT_OR_WITHIN_LEVEL", "重复测量存在缺失的被试标识或组内水平"),
    ("EXPERIMENT_DUPLICATE_SUBJECT_CELL", "重复测量存在重复的被试内单元格"),
    ("EXPERIMENT_INCOMPLETE_WITHIN_SUBJECT_CELLS", "重复测量存在缺失波次或不完整被试内单元格"),
    ("EXPERIMENT_INSUFFICIENT_COMPLETE_OBSERVATIONS", "实验分析的完整观测少于四个"),
    ("EXPERIMENT_EMPTY_CELL", "实验设计存在空单元格"),
    ("EXPERIMENT_DESIGN_MATRIX_RANK_DEFICIENT", "实验设计矩阵秩亏"),
    ("EXPERIMENT_ESTIMATION_FAILED", "实验模型估计失败"),
    ("POWER_MONTE_CARLO_PARAMETERS_REQUIRED", "Monte Carlo 功效必须提供显式数据生成参数"),
    ("POWER_MONTE_CARLO_DGP_INVALID", "Monte Carlo 功效的数据生成参数无效"),
    ("POWER_MONTE_CARLO_CONVERGENCE_FAILURE", "Monte Carlo 功效存在未允许的拟合失败"),
    ("POWER_MONTE_CARLO_TOO_MANY_FAILURES", "Monte Carlo 功效有效复制数不足"),
    ("POWER_MONTE_CARLO_TARGET_UNREACHABLE", "Monte Carlo 功效目标在当前搜索边界内不可达"),
    ("GLM_CLUSTER_INSUFFICIENT_CLUSTERS", "cluster-robust GLM 至少需要两个 cluster"),
    ("GLM_CLUSTER_ESTIMATION_FAILED", "cluster-robust GLM 估计失败"),
    ("AGGREGATION_SCALE_OUT_OF_RANGE", "聚合量表分数超出声明范围"),
    ("AGGREGATION_INSUFFICIENT_CLUSTERS", "聚合证据至少需要两个 cluster"),
    ("MLM_RANDOM_EFFECTS_MATRIX_NOT_POSITIVE_DEFINITE", "多层模型随机效应矩阵非正定"),
    ("MLM_NONCONVERGENCE", "多层模型未收敛"),
    ("MLM_ESTIMATION_FAILED", "多层模型估计失败"),
    ("LONGITUDINAL_SAMPLE_COVARIANCE_NOT_POSITIVE_DEFINITE", "纵向模型样本协方差矩阵非正定"),
    ("LONGITUDINAL_NONCONVERGENCE", "纵向模型未收敛"),
    ("LONGITUDINAL_POST_ESTIMATION_INVALID", "纵向模型收敛后检查失败"),
    ("LONGITUDINAL_ESTIMATION_FAILED", "纵向模型估计失败"),
    ("LONGITUDINAL_INVARIANCE_GROUP_REQUIRED", "纵向等值性必须显式指定 group 变量"),
    ("LONGITUDINAL_INVARIANCE_FAILED", "纵向等值性模型估计失败"),
    ("RI_CLPM_ESTIMATION_FAILED", "RI-CLPM 估计失败"),
    ("RI_CLPM_REQUIRES_TWO_CONSTRUCTS", "RI-CLPM 当前需要恰好两个构念"),
    ("MEASUREMENT_PACKAGE_NOT_INSTALLED", "问卷测量 runner 缺少统计软件依赖"),
    ("MEASUREMENT_ESTIMATION_FAILED", "问卷测量模型估计失败"),
)


def _translate_r_failure(details: str) -> AdvancedExecutionError:
    for code, message in _R_FAILURES:
        if code in details:
            return AdvancedExecutionError(code, message, details=details)
    return AdvancedExecutionError("R_EXECUTION_FAILED", "高级统计执行失败", details=details)


def _normalize_optional_presentation_assets(engine_result: JsonObject) -> None:
    """Normalize optional R presentation data before applying the strict result contract."""
    reports = engine_result.get("apaReports")
    if reports is None:
        return
    if not isinstance(reports, list):
        raise AdvancedExecutionError(
            "INVALID_APA_REPORTS",
            "高级统计引擎返回的 APA 报告必须是文本数组",
        )

    normalized_reports: list[str] = []
    for report in reports:
        if isinstance(report, str) and report.strip():
            normalized_reports.append(report)
        elif report is None or (isinstance(report, list) and not report):
            # jsonlite serializes R character(0) as []; it represents an absent
            # optional report rather than a report value for the frontend to render.
            continue
        else:
            raise AdvancedExecutionError(
                "INVALID_APA_REPORT",
                f"高级统计引擎返回了无效的 APA 报告文本类型：{type(report).__name__}",
            )
    engine_result["apaReports"] = normalized_reports


def _canonical_advanced_hash(spec: AdvancedAnalysisSpec) -> str:
    value = copy.deepcopy(spec.model_dump(mode="json", by_alias=True))
    for key, item in list(value.items()):
        if key in {"waves", "levels"} or not isinstance(item, list):
            continue
        if item and all(isinstance(entry, dict) for entry in item):
            value[key] = sorted(
                item,
                key=lambda entry: str(
                    entry.get("id")
                    or entry.get("variableId")
                    or entry.get("groupingVariableId")
                    or entry.get("targetVariableId")
                    or ""
                ),
            )
        elif all(isinstance(entry, str) for entry in item):
            value[key] = sorted(item)
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def _spec_provenance(spec: AdvancedAnalysisSpec, spec_hash: str) -> JsonObject:
    """Return explicit design metadata needed to interpret advanced estimates."""
    metadata: JsonObject = {
        "family": spec.family,
        "specHash": spec_hash,
    }
    if isinstance(spec, ExperimentalDesignSpec):
        metadata.update(
            {
                "analysisType": spec.analysis_type,
                "designType": spec.design_type,
                "dataLayout": spec.data_layout,
                "postHocAdjustment": spec.post_hoc_adjustment,
                "sumOfSquares": spec.sum_of_squares,
                "clusterVariableId": spec.cluster_variable_id,
            }
        )
    elif isinstance(spec, MultilevelModelSpec):
        metadata.update(
            {
                "analysisType": spec.analysis_type,
                "distribution": spec.distribution,
                "clusterVariableId": spec.cluster_variable_id,
                "higherLevelClusterVariableId": spec.higher_level_cluster_variable_id,
                "estimator": spec.estimator,
                "degreesOfFreedomMethod": spec.degrees_of_freedom,
                "centering": [
                    rule.model_dump(mode="json", by_alias=True) for rule in spec.centering
                ],
                "missingMethod": "complete_cases",
                **(
                    {
                        "scaleItemIds": spec.scale_item_ids,
                        "scaleMin": spec.scale_min,
                        "scaleMax": spec.scale_max,
                        "aggregationMethod": spec.aggregation_method,
                    }
                    if spec.analysis_type == "aggregation"
                    else {}
                ),
            }
        )
    elif isinstance(spec, LongitudinalModelSpec):
        metadata.update(
            {
                "modelType": spec.model_type,
                "groupVariableId": spec.group_variable_id,
                "estimator": spec.estimator,
                "missingMethod": spec.missing,
                "waveLabels": [wave.wave for wave in spec.waves],
                "timeValues": [wave.time_value for wave in spec.waves],
            }
        )
    elif isinstance(spec, QuestionnaireMeasurementSpec):
        metadata.update(
            {
                "modelType": spec.model_type,
                "markerVariableId": spec.marker_variable_id,
                "itemScale": spec.item_scale,
            }
        )
    return metadata


def _analysis_dataframe(
    repository: DatasetRepository, dataset_id: str
) -> tuple[pd.DataFrame, JsonObject]:
    dataset = repository.get_dataset(dataset_id)
    path = resolve_normalized_dataset_path(repository.settings.state_root, dataset)
    dataframe = pd.read_parquet(path)
    renamed: dict[str, str] = {}
    for variable in dataset["variables"]:
        source = str(variable["originalName"])
        if source not in dataframe.columns:
            raise AdvancedExecutionError("DATA_COLUMN_NOT_FOUND", f"数据变量存储列不存在: {source}")
        renamed[source] = str(variable["id"])
    dataframe = dataframe.rename(columns=renamed)
    return dataframe, dataset


def _persist_imputations(
    spec: MultipleImputationSpec,
    run_id: str,
    temporary_root: Path,
    repository: DatasetRepository,
) -> list[JsonObject]:
    if spec.dataset_version_id is None:
        raise AdvancedExecutionError("MISSING_DATASET_VERSION", "多重插补缺少数据版本")
    dataset_id = safe_identifier(spec.dataset_version_id, label="dataset id")
    analysis_id = safe_identifier(spec.analysis_id, label="analysis id")
    artifact_root = (
        repository.settings.state_root
        / "projects"
        / "default"
        / "datasets"
        / dataset_id
        / "imputations"
        / analysis_id
        / run_id
    )
    artifacts: list[JsonObject] = []
    sources = sorted(temporary_root.glob("imputation-*.csv"))
    if len(sources) != spec.imputations:
        raise AdvancedExecutionError(
            "IMPUTATION_INCOMPLETE", "插补引擎未生成完整的不可变数据版本集合"
        )
    artifact_root.mkdir(parents=True, exist_ok=False)
    try:
        for index, source in enumerate(sources, start=1):
            frame = pd.read_csv(source)
            target = artifact_root / f"imputation-{index:03d}.parquet"
            temporary = target.with_suffix(".parquet.tmp")
            frame.to_parquet(temporary, index=False, engine="pyarrow")
            os.replace(temporary, target)
            digest = file_sha256(target)
            artifacts.append(
                {
                    "imputation": index,
                    "path": target.relative_to(repository.settings.state_root).as_posix(),
                    "sha256": digest,
                }
            )
    except BaseException:
        for path in sorted(artifact_root.glob("*")):
            path.unlink(missing_ok=True)
        artifact_root.rmdir()
        raise
    return artifacts


def execute_cancellable_advanced_analysis(
    spec: AdvancedAnalysisSpec,
    repository: DatasetRepository,
    run_id: str,
    work_dir: Path,
    settings: Settings,
    cancel_event: threading.Event,
    progress_callback: Callable[[dict[str, Any]], None],
    on_started: Callable[[int], None] | None = None,
) -> JsonObject:
    if not settings.rscript_path.is_file():
        raise AdvancedExecutionError("RSCRIPT_NOT_FOUND", "Rscript 不存在，不能执行高级统计")
    engine_path = settings.project_root / "engine" / "R" / "run_advanced_analysis.R"
    if not engine_path.is_file():
        raise AdvancedExecutionError("RUNNER_NOT_FOUND", "高级统计 R runner 不存在")

    started = time.monotonic()
    dataset: JsonObject | None = None
    data_path: Path | None = None

    dataset_version_id = getattr(spec, "dataset_version_id", None)
    if dataset_version_id is not None:
        dataframe, dataset = _analysis_dataframe(repository, dataset_version_id)

        transform_provenance = None
        if (
            isinstance(spec, ExperimentalDesignSpec)
            and spec.data_layout == "wide"
            and spec.within_factors
        ):
            factor = spec.within_factors[0]
            value_vars = list(factor.columns.values())
            id_vars = [col for col in dataframe.columns if col not in value_vars]

            melted = dataframe.melt(
                id_vars=id_vars,
                value_vars=value_vars,
                var_name=factor.id,
                value_name=spec.outcome_ids[0],
            )

            inv_map = {v: k for k, v in factor.columns.items()}
            melted[factor.id] = melted[factor.id].map(lambda source: inv_map.get(str(source)))

            transform_provenance = {
                "action": "wide_to_long_transformation",
                "inputColumns": value_vars,
                "withinFactor": factor.id,
                "levels": factor.levels,
                "outputRows": len(melted),
            }

            spec_copy = spec.model_copy(deep=True)
            spec_copy.data_layout = "long"
            spec_copy.within_factors[0].columns = {}
            dataframe = melted
            spec_for_r = spec_copy.model_dump(mode="json", by_alias=True)
        else:
            spec_for_r = spec.model_dump(mode="json", by_alias=True)

        data_path = work_dir / "analysis-data.csv"
        dataframe.to_csv(data_path, index=False, encoding="utf-8")

    input_path = work_dir / "input.json"
    output_path = work_dir / "output.json"
    progress_path = work_dir / "progress.json"
    cancel_marker = work_dir / "cancel.marker"

    input_path.write_text(
        json.dumps(
            {
                "spec": spec_for_r
                if dataset_version_id is not None
                else spec.model_dump(mode="json", by_alias=True),
                "dataPath": str(data_path) if data_path else None,
                "artifactDirectory": str(work_dir),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    environment = os.environ.copy()
    environment["R_LIBS_USER"] = str(settings.r_library_path)
    environment["LC_ALL"] = "English_United States.utf8"

    kwargs: dict[str, Any] = {
        "cwd": settings.project_root,
        "env": environment,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["preexec_fn"] = os.setsid

    process = subprocess.Popen(
        [
            str(settings.rscript_path),
            "--vanilla",
            str(engine_path),
            str(input_path),
            str(output_path),
        ],
        **kwargs,
    )

    if on_started:
        try:
            on_started(process.pid)
        except Exception:
            pass

    def _kill_process_tree(p: subprocess.Popen[Any]) -> None:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
            else:
                import signal

                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception:
            p.kill()

    last_progress_mtime = 0.0
    try:
        while True:
            if cancel_event.is_set():
                cancel_marker.touch(exist_ok=True)
                _kill_process_tree(process)
                process.wait(timeout=5)
                raise AdvancedExecutionError("ANALYSIS_CANCELLED", "高级分析已由用户取消")

            if time.monotonic() - started > ADVANCED_TIMEOUT_SECONDS:
                _kill_process_tree(process)
                process.wait()
                raise AdvancedExecutionError("ANALYSIS_TIMEOUT", "高级统计执行超过 180 秒期限")

            if process.poll() is not None:
                break

            if progress_path.is_file():
                mtime = progress_path.stat().st_mtime
                if mtime > last_progress_mtime:
                    try:
                        prog_data = _read_json_safe(progress_path)
                        progress_callback(prog_data)
                        last_progress_mtime = mtime
                    except Exception:
                        pass

            time.sleep(0.5)

    except BaseException:
        if process.poll() is None:
            _kill_process_tree(process)
            process.wait()
        raise

    if process.returncode != 0 or not output_path.is_file():
        message = (process.stdout.read() if process.stdout else "").strip()
        raise _translate_r_failure(message)

    engine_result = json.loads(output_path.read_text(encoding="utf-8"))
    if isinstance(spec, MultipleImputationSpec):
        artifacts = _persist_imputations(spec, run_id, work_dir, repository)
        engine_result["familyResult"]["artifacts"] = artifacts
        engine_result["familyResult"]["derivedDatasetSet"] = {
            "sourceDatasetVersionId": spec.dataset_version_id,
            "runId": run_id,
            "items": [
                {
                    "imputation": art["imputation"],
                    "path": art["path"],
                    "sha256": art["sha256"],
                    "iterations": spec.iterations,
                    "seed": spec.seed,
                }
                for art in artifacts
            ],
        }

    _normalize_optional_presentation_assets(engine_result)

    data_sha256 = None if dataset is None else dataset["originalFile"]["sha256"]
    spec_hash = _canonical_advanced_hash(spec)
    result = {
        "schemaVersion": "0.1.0",
        "run": {
            "id": run_id,
            "status": "succeeded",
            "analysisId": getattr(spec, "analysis_id", None),
            "family": spec.family,
            "specHash": spec_hash,
            "durationMilliseconds": int((time.monotonic() - started) * 1000),
        },
        **engine_result,
        "provenance": {
            **engine_result.get("provenance", {}),
            **_spec_provenance(spec, spec_hash),
            "dataSha256": data_sha256,
            "seed": getattr(spec, "seed", 20260720),
            "specVersion": getattr(spec, "schema_version", "0.1.0"),
            **(
                {"wideToLong": transform_provenance}
                if "transform_provenance" in locals() and transform_provenance
                else {}
            ),
        },
    }
    validate_contract(result, settings.advanced_result_schema_path)
    return result
