from __future__ import annotations

import copy
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Callable

import pandas as pd

from app.advanced_contracts import (
    AdvancedAnalysisSpec,
    ExperimentalDesignSpec,
    LongitudinalModelSpec,
    MultilevelModelSpec,
    MultipleImputationSpec,
    QuestionnaireMeasurementSpec,
)
from app.contracts import file_sha256
from app.services.dataset_repository import DatasetRepository
from app.services.owned_resources import resolve_normalized_dataset_path
from app.services.publication_assurance import ensure_publication_assurance
from app.services.report_facts import ensure_report_facts
from app.services.repository_io import JsonObject, safe_identifier
from app.services.result_normalizer import normalize_and_validate
from app.services.subprocess_runtime import (
    RuntimeCancelled,
    RuntimeTimedOut,
    SubprocessResult,
    SubprocessRuntimeSpec,
    run_subprocess,
)
from app.settings import Settings

ADVANCED_TIMEOUT_SECONDS = 180


class AdvancedExecutionError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        details: str | None = None,
        remediation: str | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.remediation = remediation


_R_FAILURES: tuple[tuple[str, str, str], ...] = (
    ("EXPERIMENT_MISSING_SUBJECT_OR_WITHIN_LEVEL", "重复测量存在缺失的被试标识或组内水平", "补全或排除缺少被试标识、波次或组内条件的数据行，再重新运行。"),
    ("EXPERIMENT_DUPLICATE_SUBJECT_CELL", "重复测量存在重复的被试内单元格", "每位被试在每个组内条件组合只能保留一条观测；请先核对重复记录的处理规则。"),
    ("EXPERIMENT_INCOMPLETE_WITHIN_SUBJECT_CELLS", "重复测量存在缺失波次或不完整被试内单元格", "核对每位被试是否拥有全部组内条件；若设计允许不平衡重复测量，请改用混合效应模型。"),
    ("EXPERIMENT_INSUFFICIENT_COMPLETE_OBSERVATIONS", "实验分析的完整观测少于四个", "补充完整案例或调整变量选择；四条完整观测不足以支撑该实验模型。"),
    ("EXPERIMENT_EMPTY_CELL", "实验设计存在空单元格", "检查各因素组合的样本量；空单元格不能通过事后统计修复，需合并不可区分的水平或补充数据。"),
    ("EXPERIMENT_DESIGN_MATRIX_RANK_DEFICIENT", "实验设计矩阵秩亏", "删除与因素完全共线的协变量或冗余水平，并确认每个条件组合均有可估计数据。"),
    ("EXPERIMENT_ESTIMATION_FAILED", "实验模型估计失败", "先检查单元格样本量、因变量变异和协变量共线性；原始 R 诊断保留在运行详情中。"),
    ("POWER_MONTE_CARLO_PARAMETERS_REQUIRED", "Monte Carlo 功效必须提供显式数据生成参数", "明确效应大小、误差方差、预测变量相关和目标估计量，避免由界面默认值隐式生成数据。"),
    ("POWER_MONTE_CARLO_DGP_INVALID", "Monte Carlo 功效的数据生成参数无效", "检查数据生成参数的范围与量纲，尤其是相关系数、方差和样本量。"),
    ("POWER_MONTE_CARLO_CONVERGENCE_FAILURE", "Monte Carlo 功效存在未允许的拟合失败", "先降低模型复杂度或增加样本量；报告失败比例，不能只删除失败复制后宣称功效。"),
    ("POWER_MONTE_CARLO_TOO_MANY_FAILURES", "Monte Carlo 功效有效复制数不足", "检查数据生成机制与模型可识别性；修正后重新模拟，并同时报告有效复制数和失败率。"),
    ("POWER_MONTE_CARLO_TARGET_UNREACHABLE", "Monte Carlo 功效目标在当前搜索边界内不可达", "扩大预先声明的样本量搜索范围，或重新评估目标功效与最小可检测效应。"),
    ("GLM_CLUSTER_INSUFFICIENT_CLUSTERS", "cluster-robust GLM 至少需要两个 cluster", "指定实际的聚类变量，并确保保留至少两个非空 cluster。"),
    ("GLM_CLUSTER_ESTIMATION_FAILED", "cluster-robust GLM 估计失败", "检查 cluster 数、完全分离和每个 cluster 的有效观测；必要时简化固定效应。"),
    ("AGGREGATION_SCALE_OUT_OF_RANGE", "聚合量表分数超出声明范围", "核对题项反向计分、最小值/最大值和缺失编码，修正后再计算聚合证据。"),
    ("AGGREGATION_INSUFFICIENT_CLUSTERS", "聚合证据至少需要两个 cluster", "补充 cluster，或取消聚合推断；单一 cluster 不能估计组间方差。"),
    ("MLM_RANDOM_EFFECTS_MATRIX_NOT_POSITIVE_DEFINITE", "多层模型随机效应矩阵非正定", "检查随机斜率是否被数据支持；先从随机截距模型开始，并检查 cluster 数和预测变量尺度。"),
    ("MLM_NONCONVERGENCE", "多层模型未收敛", "检查尺度、稀疏 cluster 和随机效应复杂度；不要将未收敛模型的系数用于结论。"),
    ("MLM_ESTIMATION_FAILED", "多层模型估计失败", "检查因变量分布、cluster 结构和完整案例数；原始 R 诊断可用于进一步定位。"),
    ("LONGITUDINAL_SAMPLE_COVARIANCE_NOT_POSITIVE_DEFINITE", "纵向模型样本协方差矩阵非正定", "检查波次变量是否重复、常数或近乎完全相关；修正测量或简化模型后重估。"),
    ("LONGITUDINAL_NONCONVERGENCE", "纵向模型未收敛", "检查波次数、样本量和模型识别；从更简单的 CLPM/增长模型开始，勿解释未收敛结果。"),
    ("LONGITUDINAL_POST_ESTIMATION_INVALID", "纵向模型收敛后检查失败", "该解不满足后验有效性检查；检查 Heywood 情形、负方差和不合理参数，并调整模型。"),
    ("LONGITUDINAL_ESTIMATION_FAILED", "纵向模型估计失败", "检查缺失模式、变量尺度和模型识别；原始 R 诊断保留在运行详情中。"),
    ("LONGITUDINAL_INVARIANCE_GROUP_REQUIRED", "纵向等值性必须显式指定 group 变量", "在规格中指定分组变量，并确认每个组在各波次有足够完整案例。"),
    ("LONGITUDINAL_INVARIANCE_FAILED", "纵向等值性模型估计失败", "先检查配置模型，再逐级检验约束；必要时预先声明部分等值约束。"),
    ("RI_CLPM_ESTIMATION_FAILED", "RI-CLPM 估计失败", "检查每个构念至少三个波次、构念间变异和样本量；可先估计较简单的 CLPM。"),
    ("RI_CLPM_REQUIRES_TWO_CONSTRUCTS", "RI-CLPM 当前需要恰好两个构念", "将规格限定为两个构念，或使用支持多构念结构的其他纵向模型。"),
    ("MEASUREMENT_PACKAGE_NOT_INSTALLED", "问卷测量 runner 缺少统计软件依赖", "安装并锁定运行详情列出的 R 包后重试；不要以缺包时的替代输出代表该方法。"),
    ("MEASUREMENT_INSUFFICIENT_COMPLETE_OBSERVATIONS", "问卷测量的完整案例少于 20", "检查题项缺失和编码；先处理缺失或补充样本，完整案例不足时不应解释 ESEM、Bifactor 或 IRT。"),
    ("MEASUREMENT_COLUMN_NOT_FOUND", "问卷测量规格引用了不存在的题项", "重新选择当前数据版本中的题项，并确认测量版本与分析规格绑定一致。"),
    ("MEASUREMENT_CORRELATION_ESTIMATION_FAILED", "题项相关矩阵无法估计", "检查常数题项、全缺失题项和有序分类编码；移除无变异题项后重试。"),
    ("MEASUREMENT_CORRELATION_NOT_FINITE", "题项相关矩阵包含无效值", "检查零方差、完全重复题项和异常编码；修复数据后重估。"),
    ("MEASUREMENT_EFA_ESTIMATION_FAILED", "探索性因子分析估计失败", "减少因子数或检查相关矩阵的正定性；不要把失败后的降级诊断当作正式 EFA。"),
    ("MEASUREMENT_CFA_ESTIMATION_FAILED", "验证性因子分析估计失败", "检查每个因子的题项数、样本量、分类尺度与模型识别；先报告未收敛而非拟合指标。"),
    ("MEASUREMENT_INVARIANCE_GROUP_REQUIRED", "测量等值性必须指定分组变量", "在规格中选择分组变量，并检查各组的完整案例和类别覆盖。"),
    ("MEASUREMENT_INVARIANCE_ESTIMATION_FAILED", "测量等值性模型估计失败", "从配置模型开始逐级检查约束，并在有理论依据时使用部分等值。"),
    ("MEASUREMENT_ESTIMATION_FAILED", "问卷测量模型估计失败", "检查题项质量、样本量和模型识别；原始 R 诊断保留在运行详情中。"),
    ("MI_COLUMN_NOT_FOUND", "多重插补规格引用了不存在的变量", "重新选择当前数据版本中的插补变量、预测变量和被动变量，并确认数据版本绑定一致。"),
    ("MI_PASSIVE_COLUMN_NOT_FOUND", "被动插补公式引用了不存在的变量", "检查被动变量目标及乘积公式中的两个变量是否都已包含在当前分析数据中。"),
    ("MI_PASSIVE_EXPRESSION_NOT_SUPPORTED", "被动插补公式不在当前支持范围内", "当前仅支持两个变量的乘积；请在数据预处理阶段完成更复杂的派生，或缩小公式。"),
    ("MI_POOLED_COLUMN_NOT_FOUND", "Rubin 合并模型引用了不存在的变量", "检查 pooled analysis 的因变量和预测变量是否已被纳入插补数据集。"),
    ("MI_POOLED_MODEL_NOT_SUPPORTED", "当前不支持所声明的 Rubin 合并模型", "当前仅支持逐份线性回归并按 Rubin/Barnard–Rubin 规则合并。"),
    ("MI_POOLED_RANK_DEFICIENT", "插补后的 Rubin 合并模型存在秩亏", "检查完全共线的预测变量或无变异变量；不要报告无法稳定估计的合并系数。"),
    ("MI_POOLED_MODEL_FAILED", "插补后的下游模型拟合失败", "检查因变量、预测变量和每份完成数据中的变异性；原始 R 诊断保留在运行详情中。"),
    ("MI_RESOURCE_BUDGET_EXCEEDED", "多重插补请求超过资源预算", "降低插补次数、迭代次数或变量数；先用诊断性小规模运行确认预测矩阵和收敛，再扩大规模。"),
    ("MI_ESTIMATION_FAILED", "多重插补估计失败", "检查缺失模式、变量类型和预测矩阵；先以较小的插补次数验证后再正式运行。"),
)


def _translate_r_failure(details: str) -> AdvancedExecutionError:
    for code, message, remediation in _R_FAILURES:
        if code in details:
            return AdvancedExecutionError(code, message, details=details, remediation=remediation)
    return AdvancedExecutionError(
        "R_EXECUTION_FAILED",
        "高级统计执行失败",
        details=details,
        remediation="请核对运行详情中的原始 R 诊断、数据版本和分析规格；修正后重新运行。",
    )


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
    elif isinstance(spec, MultipleImputationSpec):
        plan_version_id = spec.imputation_plan_version_id or spec.plan_version_id
        metadata.update(
            {
                "planVersionId": spec.plan_version_id or plan_version_id,
                "imputationPlanVersionId": plan_version_id,
                "contextHash": spec.context_hash,
                "sampleVersionId": spec.sample_version_id,
                "sampleHash": spec.sample_hash,
                "structureVersionId": spec.structure_version_id,
                "structureHash": spec.structure_hash,
                "measurementVersionId": spec.measurement_version_id,
                "measurementHash": spec.measurement_hash,
                "datasetSha256": spec.dataset_sha256,
                "predictorMatrixHash": spec.predictor_matrix_hash,
                "substantiveModelHash": spec.substantive_model_hash,
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
    progress_callback: Callable[[JsonObject], None],
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
                "progressPath": str(progress_path),
                "cancelPath": str(cancel_marker),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    environment = os.environ.copy()
    environment["R_LIBS_USER"] = str(settings.r_library_path)
    environment["LC_ALL"] = "English_United States.utf8"

    command = [
        str(settings.rscript_path),
        "--vanilla",
        str(engine_path),
        str(input_path),
        str(output_path),
    ]
    runner_log_path = work_dir / "runner.log"
    try:
        runtime_result: SubprocessResult = run_subprocess(
            SubprocessRuntimeSpec(
                command=command,
                cwd=settings.project_root,
                environment=environment,
                stdout_log=runner_log_path,
                merge_stderr=True,
                cancel_event=cancel_event,
                cancel_path=cancel_marker,
                progress_path=progress_path,
                progress_callback=progress_callback,
                timeout=ADVANCED_TIMEOUT_SECONDS,
                poll_interval=0.5,
                cancel_grace=0.0,
                termination_grace=0.0,
                kill_grace=5.0,
                new_process_group=True,
                on_started=on_started,
            )
        )
    except RuntimeCancelled as error:
        raise AdvancedExecutionError("ANALYSIS_CANCELLED", "高级分析已由用户取消") from error
    except RuntimeTimedOut as error:
        raise AdvancedExecutionError("ANALYSIS_TIMEOUT", "高级统计执行超过 180 秒期限") from error

    if runtime_result.returncode != 0 or not output_path.is_file():
        message = runtime_result.stdout.strip()
        if "ANALYSIS_CANCELLED" in message:
            raise AdvancedExecutionError("ANALYSIS_CANCELLED", "高级分析已由用户取消")
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
    ensure_report_facts(result)
    ensure_publication_assurance(
        result,
        replay_command="pwsh -NoProfile -File reproduction/reproduce.ps1",
    )
    result = normalize_and_validate(result, settings.advanced_result_schema_path)
    return result
