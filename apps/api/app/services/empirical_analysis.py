from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from contextlib import ExitStack
from pathlib import Path
from threading import Event
from typing import Any, Callable

import pandas as pd

from app.services.dataset_import import utc_now_iso
from app.services.dataset_repository import DatasetRepository, _write_json_atomic
from app.services.empirical_data_prep import prepare_empirical_data
from app.services.empirical_options_validator import (
    EmpiricalAnalysisError,
    validate_empirical_options,
)
from app.services.empirical_procedures import validate_procedure
from app.services.r_engine import AnalysisCancelled, EngineExecutionError
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

EMPIRICAL_TIMEOUT_SECONDS = 180.0
EMPIRICAL_POWER_TIMEOUT_SECONDS = 1800.0


def _prepare_data(
    dataset: dict[str, Any], measurement: dict[str, Any], settings: Settings
) -> tuple[pd.DataFrame, dict[str, Any]]:
    return prepare_empirical_data(dataset, measurement, settings)


def _validate_options(metadata: dict[str, Any], options: dict[str, Any]) -> None:
    validate_empirical_options(metadata, options)


def _run_rscript_fallback(
    *,
    command: list[str],
    environment: dict[str, str],
    settings: Settings,
    cancel_event: Event | None,
    cancel_path: Path,
    progress_path: Path,
    progress_callback: Callable[[dict[str, Any]], None] | None,
    timeout: float,
    stdout_log: Path,
    stderr_log: Path,
) -> tuple[int, str, str]:
    try:
        result: SubprocessResult = run_subprocess(
            SubprocessRuntimeSpec(
                command=command,
                cwd=settings.project_root,
                environment=environment,
                stdout_log=stdout_log,
                stderr_log=stderr_log,
                cancel_event=cancel_event,
                cancel_path=cancel_path,
                progress_path=progress_path,
                progress_callback=progress_callback,
                timeout=timeout,
                poll_interval=0.1,
                cancel_grace=1.5,
                termination_grace=1.0,
                kill_grace=1.0,
                create_no_window=True,
            )
        )
    except RuntimeCancelled as error:
        raise AnalysisCancelled(str(error)) from error
    except RuntimeTimedOut as error:
        raise EngineExecutionError("问卷实证分析超过运行时限") from error
    return result.returncode, result.stdout, result.stderr


def run_empirical_analysis(
    dataset_id: str,
    measurement_version: int | None,
    options: dict[str, Any],
    repository: DatasetRepository,
    settings: Settings,
    worker_pool: RWorkerPool | None = None,
    *,
    cancel_event: Event | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    work_dir: Path | None = None,
    report_id: str | None = None,
    context_lineage: dict[str, object] | None = None,
) -> dict[str, Any]:
    if progress_callback is not None:
        progress_callback({"stage": "preparing_data", "progress": 0.03})
    dataset = repository.get_dataset(dataset_id)
    measurement = repository.get_measurement(dataset_id, measurement_version) if measurement_version is not None else None
    prepared, metadata = prepare_empirical_data(dataset, measurement, settings)
    sample_lineage: dict[str, object] | None = None
    sample_version_id = options.get("sampleVersionId") or options.get("sample_version_id")
    if sample_version_id:
        sample = repository.get_analysis_sample(dataset_id, str(sample_version_id))
        if str(sample.get("datasetSha256")) != str(dataset["originalFile"]["sha256"]):
            raise EmpiricalAnalysisError("AnalysisSampleVersion 与当前数据版本 SHA-256 不一致")
        sample_cases = pd.read_parquet(
            repository.get_analysis_sample_case_path(dataset_id, str(sample_version_id))
        )
        required_columns = {"caseIndex", "included"}
        if not required_columns.issubset(sample_cases.columns):
            raise EmpiricalAnalysisError("AnalysisSampleVersion 缺少 caseIndex/included 字段")
        included_indices = (
            pd.to_numeric(
                sample_cases.loc[sample_cases["included"].astype(bool), "caseIndex"],
                errors="coerce",
            )
            .dropna()
            .astype(int)
            .tolist()
        )
        if not included_indices:
            raise EmpiricalAnalysisError("AnalysisSampleVersion 的纳入样本数为 0")
        if min(included_indices) < 1 or max(included_indices) > len(prepared):
            raise EmpiricalAnalysisError("AnalysisSampleVersion 的案例索引超出派生数据范围")
        if len(set(included_indices)) != len(included_indices):
            raise EmpiricalAnalysisError("AnalysisSampleVersion 包含重复案例索引")
        prepared = prepared.iloc[[index - 1 for index in included_indices]].reset_index(drop=True)
        sample_lineage = {
            "sampleVersionId": sample["id"],
            "sampleHash": sample["sampleHash"],
            "qualityRunId": sample["qualityRunId"],
            "includedCount": sample["includedCount"],
            "excludedCount": sample["excludedCount"],
        }
    normalized_options = {
        "procedure": options.get("procedure"),
        "analysisVariableIds": options.get("analysisVariableIds", []),
        "constructIds": options.get("constructIds", []),
        "factorCount": options.get("factorCount") or len(metadata["constructs"]),
        "groupVariableId": options.get("groupVariableId"),
        "aggregationVariableId": options.get("aggregationVariableId"),
        "outcomeVariableId": options.get("outcomeVariableId"),
        "predictorVariableIds": list(dict.fromkeys(options.get("predictorVariableIds", []))),
        "controlVariableIds": list(dict.fromkeys(options.get("controlVariableIds", []))),
        "responseSurfacePredictorIds": list(
            dict.fromkeys(options.get("responseSurfacePredictorIds", []))
        ),
        "correlationMethod": options.get("correlationMethod") or "pearson",
        "correlationPAdjust": options.get("correlationPAdjust") or "BH",
        "groupOmnibusPAdjust": options.get("groupOmnibusPAdjust") or "holm",
        "multiplicityPAdjust": options.get("multiplicityPAdjust") or "BH",
        "confidenceLevel": float(options.get("confidenceLevel") or 0.95),
        "multiplicityFamilyId": str(
            options.get("multiplicityFamilyId") or "cross_sectional_inference"
        ),
        "rotation": options.get("rotation") or "varimax",
        "factorCountMethod": options.get("factorCountMethod") or "kaiser",
        "parallelIterations": int(options.get("parallelIterations") or 1000),
        "randomSeed": int(options.get("randomSeed") or 20260714),
        "contextHash": options.get("contextHash"),
        "contextTimeStructure": options.get("contextTimeStructure"),
        "contextDependenceStructure": options.get("contextDependenceStructure"),
        "contextDesign": options.get("contextDesign"),
        "applicableCapabilitySlices": list(options.get("applicableCapabilitySlices") or []),
        "studyPlanBinding": options.get("studyPlanBinding"),
        "studyPlanMultiplicity": options.get("studyPlanMultiplicity"),
        "longitudinalPanel": options.get("longitudinalPanel"),
        "diaryMultilevel": options.get("diaryMultilevel"),
    }
    if sample_lineage is not None:
        normalized_options["sampleVersionId"] = sample_lineage["sampleVersionId"]
    validate_procedure(metadata, normalized_options)
    validate_empirical_options(metadata, normalized_options)
    if not settings.rscript_path.exists():
        raise EngineExecutionError(f"Rscript 不存在: {settings.rscript_path}")
    engine_path = settings.project_root / "engine" / "R" / "run_empirical_analysis.R"
    report_id = report_id or f"empirical_{uuid.uuid4().hex[:16]}"
    from app.services.empirical_export import empirical_report_path

    report_root = empirical_report_path(dataset_id, measurement_version, report_id, settings).parent
    with ExitStack() as stack:
        if work_dir is None:
            temporary = stack.enter_context(
                tempfile.TemporaryDirectory(prefix="researchpath-empirical-")
            )
            temporary_root = Path(temporary)
        else:
            temporary_root = work_dir
            temporary_root.mkdir(parents=True, exist_ok=True)
        data_path = temporary_root / "analysis-data.csv"
        input_path = temporary_root / "input.json"
        output_path = temporary_root / "output.json"
        progress_path = temporary_root / "progress.json"
        cancel_path = temporary_root / "cancel"
        for stale_path in (output_path, progress_path, cancel_path):
            stale_path.unlink(missing_ok=True)
        prepared.to_csv(data_path, index=False, encoding="utf-8")
        if progress_callback is not None:
            progress_callback({"stage": "starting_r_engine", "progress": 0.08})
        input_path.write_text(
            json.dumps(
                {
                    "reportId": report_id,
                    "datasetId": dataset_id,
                    "measurementVersionId": measurement["id"] if measurement else None,
                    "createdAt": utc_now_iso(),
                    "dataPath": str(data_path),
                    "metadata": metadata,
                    "sampleVersion": sample_lineage,
                    "options": normalized_options,
                    "progressPath": str(progress_path),
                    "cancelPath": str(cancel_path),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        includes_power_analysis = any(
            isinstance(options.get(method), dict)
            and options[method].get("powerAnalysis") is not None
            for method in ("longitudinalPanel", "diaryMultilevel")
        )
        timeout_seconds = (
            EMPIRICAL_POWER_TIMEOUT_SECONDS
            if includes_power_analysis
            else EMPIRICAL_TIMEOUT_SECONDS
        )
        deadline = time.monotonic() + timeout_seconds
        worker_error: RWorkerUnavailable | None = None
        if worker_pool is not None:
            try:
                worker_pool.run(
                    script_path=engine_path,
                    input_path=input_path,
                    output_path=output_path,
                    log_path=temporary_root / "worker.log",
                    cancel_event=cancel_event,
                    cancel_path=cancel_path,
                    progress_path=progress_path,
                    progress_callback=progress_callback,
                    timeout=max(0.1, deadline - time.monotonic()),
                    repair_capacity_on_cancel=False,
                )
            except RWorkerCancelled as error:
                raise AnalysisCancelled(str(error)) from error
            except RWorkerTaskError as error:
                from app.services.r_engine import translate_r_error

                raise EngineExecutionError(translate_r_error(str(error))) from error
            except RWorkerUnavailable as error:
                worker_error = error
        if worker_pool is None or worker_error is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise EngineExecutionError(f"实证分析引擎超过 {int(timeout_seconds)} 秒总执行期限")
            environment = os.environ.copy()
            environment["R_LIBS_USER"] = str(settings.r_library_path)
            environment["LC_ALL"] = "English_United States.utf8"
            environment["RESEARCHPATH_RUNTIME_MODE"] = "rscript"
            environment["RESEARCHPATH_PARALLEL_WORKERS"] = str(settings.r_parallel_workers)
            returncode, stdout, stderr = _run_rscript_fallback(
                command=[
                    str(settings.rscript_path),
                    "--vanilla",
                    str(engine_path),
                    str(input_path),
                    str(output_path),
                ],
                environment=environment,
                settings=settings,
                cancel_event=cancel_event,
                cancel_path=cancel_path,
                progress_path=progress_path,
                progress_callback=progress_callback,
                timeout=remaining,
                stdout_log=temporary_root / "stdout.log",
                stderr_log=temporary_root / "stderr.log",
            )
            if returncode != 0 or not output_path.exists():
                message = stderr.strip() or stdout.strip()
                if worker_error is not None:
                    message = f"resident pool unavailable ({worker_error}); fallback: {message}"
                from app.services.r_engine import translate_r_error

                raise EngineExecutionError(translate_r_error(message))
        report = json.loads(output_path.read_text(encoding="utf-8"))
        apply_status_model(report)
        report = normalize_and_validate(report, settings.empirical_result_schema_path)
        if sample_lineage is not None:
            report["sampleVersion"] = sample_lineage
        if context_lineage is not None:
            provenance = report.setdefault("provenance", {})
            provenance["analysisContext"] = context_lineage
            provenance["contextHash"] = context_lineage.get("contextHash")

        try:
            from app.services.academic_interpreter import generate_interpretation_assets
            from app.services.publication_assurance import ensure_publication_assurance
            from app.services.report_facts import ensure_report_facts

            ensure_report_facts(report)
            ensure_publication_assurance(
                report,
                replay_command=None,
            )
            interpretation, tables = generate_interpretation_assets(report, normalized_options)
            report["academicInterpretation"] = interpretation
            report["apaTables"] = tables
        except Exception as interpret_err:
            report["academicInterpretation"] = f"自动解读生成失败：{str(interpret_err)}"
            report["apaTables"] = ""
    report_root.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(report_root / "report.json", report)
    if progress_callback is not None:
        progress_callback({"stage": "persisting_report", "progress": 0.98})
    return report


def export_empirical_workbook(
    dataset_id: str,
    measurement_version: int | None,
    report_id: str,
    settings: Settings,
) -> Path:
    from app.services.empirical_export import export_empirical_workbook as export_workbook

    return export_workbook(dataset_id, measurement_version, report_id, settings)
