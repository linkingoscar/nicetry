from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from threading import Event
from typing import Any

import pandas as pd

from app.contracts import canonical_model_hash, file_sha256
from app.process_catalog import match_process_model
from app.services.owned_resources import resolve_derived_dataset_path
from app.services.r_workers import (
    RWorkerCancelled,
    RWorkerPool,
    RWorkerTaskError,
    RWorkerUnavailable,
)
from app.services.result_normalizer import normalize_and_validate
from app.services.status_model import apply_status_model
from app.services.subprocess_runtime import (
    RuntimeCancelled,
    RuntimeTimedOut,
    SubprocessResult,
    SubprocessRuntimeSpec,
    run_subprocess,
)
from app.settings import Settings

ENGINE_TIMEOUT_SECONDS = 180.0
logger = logging.getLogger("researchpath")


def _process_model_number(model_spec: dict[str, object]) -> int | None:
    match = match_process_model(model_spec)
    return match.model_number if match.match_status == "exact" else None


def _prepare_model_column(node: dict[str, Any], values: pd.Series) -> pd.Series:
    method = node.get("encoding", {}).get("method")
    if node.get("dataType") in {"binary", "nominal"} or (
        method == "ordinal_score" and node.get("encoding", {}).get("levels")
    ):
        return values.astype("string")
    return pd.to_numeric(values, errors="coerce")


class EngineExecutionError(RuntimeError):
    def __init__(self, message: str, diagnostic: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.diagnostic = diagnostic


class AnalysisCancelled(EngineExecutionError):
    pass


def _remaining_engine_time(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise EngineExecutionError("R 统计引擎超过 180 秒总执行期限")
    return remaining


def run_mediation(
    model_spec: dict[str, Any],
    data_path: Path,
    settings: Settings,
    worker_pool: RWorkerPool | None = None,
) -> dict[str, Any]:
    if not settings.rscript_path.exists():
        logger.error("Rscript is unavailable at the configured runtime path")
        raise EngineExecutionError("R 运行时不可用，请先运行项目安装脚本并检查本机 R 安装")
    if not data_path.exists():
        logger.error("Analysis data file is unavailable for mediation run")
        raise EngineExecutionError("分析数据文件不存在，无法启动统计引擎")

    return _execute_analysis(model_spec, data_path, settings, "demo", worker_pool=worker_pool)


def _execute_analysis(
    model_spec: dict[str, Any],
    data_path: Path,
    settings: Settings,
    model_version_id: str,
    data_sha256: str | None = None,
    lavaan_syntax: str | None = None,
    required_variables: list[str] | None = None,
    ordered_variables: list[str] | None = None,
    worker_pool: RWorkerPool | None = None,
) -> dict[str, Any]:
    if not settings.rscript_path.exists():
        logger.error("Rscript is unavailable at the configured runtime path")
        raise EngineExecutionError("R 运行时不可用，请先运行项目安装脚本并检查本机 R 安装")
    if not data_path.exists():
        logger.error("Analysis data file is unavailable for engine execution")
        raise EngineExecutionError("分析数据文件不存在，无法启动统计引擎")
    run_id = f"run_{uuid.uuid4().hex}"
    engine_input = {
        "runId": run_id,
        "modelHash": canonical_model_hash(model_spec),
        "modelVersionId": model_version_id,
        "dataSha256": data_sha256 or file_sha256(data_path),
        "dataPath": str(data_path.resolve()),
        "modelSpec": model_spec,
        "processModelNumber": _process_model_number(model_spec),
    }
    if lavaan_syntax is not None:
        engine_input["lavaanSyntax"] = lavaan_syntax
        engine_input["requiredVariables"] = required_variables
        engine_input["orderedVariables"] = ordered_variables

    with tempfile.TemporaryDirectory(prefix="researchpath-") as temp_dir:
        input_path = Path(temp_dir) / "input.json"
        output_path = Path(temp_dir) / "result.json"
        input_path.write_text(json.dumps(engine_input, ensure_ascii=False), encoding="utf-8")

        deadline = time.monotonic() + ENGINE_TIMEOUT_SECONDS
        worker_error: RWorkerUnavailable | None = None
        if worker_pool is not None:
            try:
                worker_pool.run(
                    script_path=settings.r_engine_path,
                    input_path=input_path,
                    output_path=output_path,
                    log_path=Path(temp_dir) / "worker.log",
                    timeout=_remaining_engine_time(deadline),
                )
            except RWorkerTaskError as error:
                raise EngineExecutionError(
                    translate_r_error(str(error)),
                    diagnostic={"workerError": str(error)},
                ) from error
            except RWorkerCancelled as error:
                raise AnalysisCancelled(str(error)) from error
            except RWorkerUnavailable as error:
                worker_error = error
        if worker_pool is None or worker_error is not None:
            environment = os.environ.copy()
            environment["R_LIBS_USER"] = str(settings.r_library_path)
            environment["LC_ALL"] = "English_United States.utf8"
            environment["RESEARCHPATH_RUNTIME_MODE"] = "rscript"
            environment["RESEARCHPATH_PARALLEL_WORKERS"] = str(settings.r_parallel_workers)
            try:
                completed = subprocess.run(
                    [
                        str(settings.rscript_path),
                        "--vanilla",
                        str(settings.r_engine_path),
                        str(input_path),
                        str(output_path),
                    ],
                    cwd=settings.project_root,
                    env=environment,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=_remaining_engine_time(deadline),
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise EngineExecutionError("R 统计引擎超过 180 秒总执行期限") from error
            if completed.returncode != 0:
                message = completed.stderr.strip() or completed.stdout.strip()
                logger.error(
                    "Rscript fallback failed with exit code %s: %s",
                    completed.returncode,
                    message,
                )
                if worker_error is not None:
                    message = f"resident pool unavailable ({worker_error}); fallback: {message}"
                raise EngineExecutionError(
                    translate_r_error(message),
                    diagnostic={
                        "stderr": completed.stderr,
                        "stdout": completed.stdout,
                        "exitCode": completed.returncode,
                    },
                )
        if not output_path.exists():
            raise EngineExecutionError("R 统计引擎未生成 ResultBundle")

        result = json.loads(output_path.read_text(encoding="utf-8"))
        apply_status_model(result)
        result = normalize_and_validate(result, settings.result_schema_path)
        return result


def translate_r_error(message: str) -> str:
    err_lower = message.lower()
    if "singular gradient" in err_lower:
        return "模型拟合失败：估计的梯度奇异。这通常意味着模型过于复杂、变量间存在极高共线性或初始估计值不合适。请检查变量设计或简化模型。"
    if "computationally singular" in err_lower:
        return "矩阵计算失败：协方差矩阵是奇异的（计算上不可逆）。这表明变量之间存在严重的多重共线性（如某个变量可被其他变量完全预测）。请检查并剔除高共线性的自变量。"
    if "not positive definite" in err_lower:
        return "协方差矩阵非正定：这可能由于样本量过小、变量间高度共线性，或存在负残差方差。请检查样本数据，或者尝试合并部分高相关构念。"
    if "negative eigenvalues" in err_lower:
        return "观测协方差矩阵存在负特征值：数据在特征分解中表现异常，建议检查是否有极端异常值、缺失值未清洗，或数据取值范围是否过窄。"
    if "fitting failed" in err_lower:
        return "lavaan 结构方程估计失败：算法无法收敛。请检查是否存在设定错误的路径、悬空的节点，或者变量方差差异过大，建议将各指标变量标准化后再试。"
    if "system is computationally singular" in err_lower:
        return "系统在计算中呈奇异状态：可能存在高度共线性的变量，或样本数据存在完全重复的行。请检查数据字典中的自变量和控制变量配置。"
    if "object 'moderation' not found" in err_lower:
        return "引擎内部错误：未找到调节路径对应关系。这可能是由于模型配置不匹配，请清除草稿重试。"
    if "binary_mediator_not_supported" in err_lower:
        return (
            "BINARY_MEDIATOR_NOT_SUPPORTED：当前模型包含二分类中介变量，暂不支持运行。"
            "logit 方程的中介路径系数与 OLS 结果方程系数直接相乘不构成可解释的间接效应；"
            "请将中介变量改为连续变量，或改用支持二分类中介的方法。"
        )
    logger.warning("R engine error was translated to a sanitized client message: %s", message)
    return "R 统计引擎执行失败。原始诊断已写入服务日志，请通过任务详情中的诊断信息进一步排查。"


def execute_cancellable_analysis(
    model_spec: dict[str, Any],
    dataset: dict[str, Any],
    measurement: dict[str, Any],
    model_version_id: str,
    run_id: str,
    work_dir: Path,
    settings: Settings,
    cancel_event: Event,
    progress_callback: Any,
    worker_pool: RWorkerPool | None = None,
) -> dict[str, Any]:
    if not settings.rscript_path.exists():
        raise EngineExecutionError(f"Rscript 不存在: {settings.rscript_path}")
    derived_path = resolve_derived_dataset_path(settings.state_root, measurement)
    data = pd.read_parquet(derived_path)
    family = model_spec.get("estimation", {}).get("family", "ols")
    if family == "sem":
        from app.services.model_service import _model_variables
        from app.services.sem_compiler import compile_sem_model

        available = _model_variables(dataset, measurement)
        compiled = compile_sem_model(model_spec, data, available)
        if not compiled["valid"]:
            raise EngineExecutionError(f"SEM 编译错误: {'; '.join(compiled['errors'])}")

        required_vars = compiled["requiredVariables"]
        observed_columns = {
            variable["id"]: variable["originalName"] for variable in dataset["variables"]
        }
        derived_score_ids = {var["id"] for var in measurement["derivedDataset"]["scoreVariables"]}

        # 获取分组变量的映射 ID，以避免将其转换为 numeric
        group_var_id = model_spec.get("estimation", {}).get("groupVariableId")
        group_var_id_mapped = None
        if group_var_id:
            node_group = next(
                (n for n in model_spec.get("nodes", []) if n.get("id") == group_var_id), None
            )
            group_var_id_mapped = (
                node_group.get("variableId", group_var_id) if node_group else group_var_id
            )

        prepared = pd.DataFrame(index=data.index)
        for var_id in required_vars:
            column = var_id if var_id in derived_score_ids else observed_columns.get(var_id, var_id)
            if column not in data.columns:
                raise EngineExecutionError(f"分析变量不存在: {var_id}")
            if var_id == group_var_id_mapped:
                prepared[var_id] = data[column]
            else:
                prepared[var_id] = pd.to_numeric(data[column], errors="coerce")

        work_dir.mkdir(parents=True, exist_ok=True)
        data_path = work_dir / "analysis-data.csv"
        input_path = work_dir / "input.json"
        output_path = work_dir / "result.json"
        progress_path = work_dir / "progress.json"
        cancel_path = work_dir / "cancel.requested"
        prepared.to_csv(data_path, index=False, encoding="utf-8")
        engine_input = {
            "runId": run_id,
            "modelHash": canonical_model_hash(model_spec),
            "modelVersionId": model_version_id,
            "dataSha256": measurement["derivedDataset"]["sha256"],
            "dataPath": str(data_path.resolve()),
            "progressPath": str(progress_path.resolve()),
            "cancelPath": str(cancel_path.resolve()),
            "modelSpec": model_spec,
            "processModelNumber": _process_model_number(model_spec),
            "lavaanSyntax": compiled["lavaanSyntax"],
            "requiredVariables": compiled["requiredVariables"],
            "orderedVariables": compiled["orderedVariables"],
        }
    else:
        observed_columns = {
            variable["id"]: variable["originalName"] for variable in dataset["variables"]
        }
        prepared = pd.DataFrame(index=data.index)
        for node in model_spec["nodes"]:
            variable_id = node["variableId"]
            column = (
                variable_id if node["kind"] == "scale_score" else observed_columns.get(variable_id)
            )
            if column is None or column not in data.columns:
                raise EngineExecutionError(f"分析变量不存在: {variable_id}")
            prepared[variable_id] = _prepare_model_column(node, data[column])

        work_dir.mkdir(parents=True, exist_ok=True)
        data_path = work_dir / "analysis-data.csv"
        input_path = work_dir / "input.json"
        output_path = work_dir / "result.json"
        progress_path = work_dir / "progress.json"
        cancel_path = work_dir / "cancel.requested"
        prepared.to_csv(data_path, index=False, encoding="utf-8")
        engine_input = {
            "runId": run_id,
            "modelHash": canonical_model_hash(model_spec),
            "modelVersionId": model_version_id,
            "dataSha256": measurement["derivedDataset"]["sha256"],
            "dataPath": str(data_path.resolve()),
            "progressPath": str(progress_path.resolve()),
            "cancelPath": str(cancel_path.resolve()),
            "modelSpec": model_spec,
            "processModelNumber": _process_model_number(model_spec),
        }
    input_path.write_text(json.dumps(engine_input, ensure_ascii=False), encoding="utf-8")
    stdout_log = work_dir / "stdout.log"
    stderr_log = work_dir / "stderr.log"
    deadline = time.monotonic() + ENGINE_TIMEOUT_SECONDS
    worker_error: RWorkerUnavailable | None = None
    if worker_pool is not None:
        try:
            worker_pool.run(
                script_path=settings.r_engine_path,
                input_path=input_path,
                output_path=output_path,
                log_path=work_dir / "worker.log",
                cancel_event=cancel_event,
                cancel_path=cancel_path,
                progress_path=progress_path,
                progress_callback=progress_callback,
                timeout=_remaining_engine_time(deadline),
                repair_capacity_on_cancel=False,
            )
        except RWorkerCancelled as error:
            raise AnalysisCancelled(str(error)) from error
        except RWorkerTaskError as error:
            raise EngineExecutionError(translate_r_error(str(error))) from error
        except RWorkerUnavailable as error:
            worker_error = error
    if worker_pool is None or worker_error is not None:
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        environment["LC_ALL"] = "English_United States.utf8"
        environment["RESEARCHPATH_RUNTIME_MODE"] = "rscript"
        environment["RESEARCHPATH_PARALLEL_WORKERS"] = str(settings.r_parallel_workers)
        remaining = _remaining_engine_time(deadline)
        try:
            fallback: SubprocessResult = run_subprocess(
                SubprocessRuntimeSpec(
                    command=[
                        str(settings.rscript_path),
                        "--vanilla",
                        str(settings.r_engine_path),
                        str(input_path),
                        str(output_path),
                    ],
                    cwd=settings.project_root,
                    environment=environment,
                    stdout_log=stdout_log,
                    stderr_log=stderr_log,
                    cancel_event=cancel_event,
                    cancel_path=cancel_path,
                    progress_path=progress_path,
                    progress_callback=progress_callback,
                    timeout=max(0.0, remaining),
                    poll_interval=0.1,
                    cancel_grace=0.75,
                    termination_grace=0.75,
                    kill_grace=0.5,
                    create_no_window=True,
                )
            )
        except RuntimeCancelled as error:
            raise AnalysisCancelled(str(error)) from error
        except RuntimeTimedOut as error:
            raise EngineExecutionError("R 统计引擎超过 180 秒总执行期限") from error
        if fallback.returncode != 0:
            message = fallback.stderr.strip() or fallback.stdout.strip()
            logger.error(
                "Rscript process failed with exit code %s: %s",
                fallback.returncode,
                message,
            )
            if worker_error is not None:
                message = f"resident pool unavailable ({worker_error}); fallback: {message}"
            raise EngineExecutionError(
                translate_r_error(message),
                diagnostic={
                    "stderr": fallback.stderr,
                    "stdout": fallback.stdout,
                    "exitCode": fallback.returncode,
                },
            )
    if not output_path.exists():
        raise EngineExecutionError("R 统计引擎未生成 ResultBundle")
    result = json.loads(output_path.read_text(encoding="utf-8"))
    apply_status_model(result)

    try:
        from app.services.academic_interpreter import generate_interpretation_assets
        from app.services.publication_assurance import ensure_publication_assurance
        from app.services.report_facts import ensure_report_facts

        ensure_report_facts(result)
        ensure_publication_assurance(
            result,
            replay_command="pwsh -NoProfile -File reproducibility/reproduce.ps1",
        )
        interpretation, tables = generate_interpretation_assets(result, model_spec)
        result["academicInterpretation"] = interpretation
        result["apaTables"] = tables
    except Exception as interpret_err:
        result["academicInterpretation"] = f"自动解读生成失败：{str(interpret_err)}"
        result["apaTables"] = ""

    result = normalize_and_validate(result, settings.result_schema_path)
    return result
