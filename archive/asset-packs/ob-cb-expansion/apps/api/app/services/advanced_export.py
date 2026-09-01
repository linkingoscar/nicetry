from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeAlias
from zipfile import ZIP_DEFLATED, ZipFile

from app.advanced_contracts import AdvancedAnalysisSpec
from app.contracts import validate_contract
from app.services.advanced_runner import _canonical_advanced_hash
from app.services.dataset_repository import DatasetRepository
from app.services.owned_resources import resolve_normalized_dataset_path
from app.services.repository_io import UnsafePathError, safe_identifier
from app.settings import Settings

# The result bundle is schema-validated at the export boundary and intentionally
# preserves family-specific JSON shapes that are not representable by one static
# Python model. Keep the looseness isolated to this serialization module.
JsonValue: TypeAlias = Any
JsonObject = dict[str, JsonValue]


def _write_json(path: Path, value: JsonValue) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _cell(value: JsonValue) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(title: str, rows: list[JsonObject]) -> JsonObject:
    return {"title": title, "rows": rows}


def _rows(value: JsonValue) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _metric_rows(value: JsonValue) -> list[JsonObject]:
    if not isinstance(value, dict):
        return []
    return [{"metric": key, "value": item} for key, item in value.items()]


def _object_value_rows(value: JsonValue, key: str = "level") -> list[JsonObject]:
    if not isinstance(value, dict):
        return []
    rows: list[JsonObject] = []
    for label, item in value.items():
        if isinstance(item, dict):
            rows.append({key: label, **item})
        else:
            rows.append({key: label, "value": item})
    return rows


def _aligned_rows(ids: JsonValue, values: JsonValue, value_key: str) -> list[JsonObject]:
    if not isinstance(ids, list) or not isinstance(values, list):
        return []
    return [
        {"itemId": item_id, value_key: values[index]}
        for index, item_id in enumerate(ids)
        if index < len(values)
    ]


def build_advanced_paper_tables(result: JsonObject) -> list[JsonObject]:
    """Map the stable result bundle into family-specific paper-ready tables."""
    tables = [
        _table("估计结果", list(result.get("estimates", []))),
    ]
    family_result = result.get("familyResult", {})
    family = family_result.get("family")
    if family == "experimental_design":
        tables.extend(
            [
                _table("Omnibus tests", list(family_result.get("omnibusTests", []))),
                _table(
                    "Estimated marginal means",
                    list(family_result.get("estimatedMarginalMeans", [])),
                ),
                _table("Contrasts", list(family_result.get("contrasts", []))),
                _table("Planned contrasts", list(family_result.get("plannedContrasts", []))),
            ]
        )
    elif family == "multilevel_model":
        tables.extend(
            [
                _table("Fixed effects", list(family_result.get("fixedEffects", []))),
                _table("Random effects", list(family_result.get("randomEffects", []))),
                _table("Variance components", list(family_result.get("varianceComponents", []))),
                _table("ICC", list(family_result.get("icc", []))),
            ]
        )
    elif family == "longitudinal_model":
        invariance = family_result.get("invariance")
        tables.extend(
            [
                _table("Longitudinal parameters", list(family_result.get("parameters", []))),
                _table("Wave sample flow", list(family_result.get("waveSampleFlow", []))),
                _table(
                    "Fit indices",
                    [
                        {"metric": key, "value": value}
                        for key, value in family_result.get("fitIndices", {}).items()
                    ],
                ),
                _table(
                    "Invariance models",
                    _object_value_rows(
                        invariance.get("models") if isinstance(invariance, dict) else None
                    ),
                ),
                _table(
                    "Invariance comparisons",
                    _object_value_rows(
                        invariance.get("comparisons") if isinstance(invariance, dict) else None
                    ),
                ),
                _table(
                    "Longitudinal latent means",
                    _rows(invariance.get("latentMeans") if isinstance(invariance, dict) else None),
                ),
                _table(
                    "Missing-pattern evidence",
                    (
                        [{"pattern": family_result["missingPatterns"]}]
                        if family_result.get("missingPatterns")
                        else []
                    ),
                ),
            ]
        )
    elif family == "multiple_imputation":
        tables.extend(
            [
                _table("Imputation diagnostics", list(family_result.get("convergence", []))),
                _table("Missing information", list(family_result.get("missingInformation", []))),
                _table("Derived datasets", list(family_result.get("artifacts", []))),
                _table("Imputation trace", list(family_result.get("trace", []))),
                _table("Imputed distributions", list(family_result.get("distribution", []))),
                _table(
                    "Fraction of missing information",
                    list(family_result.get("fractionMissingInformation", [])),
                ),
            ]
        )
    elif family == "questionnaire_measurement":
        reliability = family_result.get("reliability")
        efa = family_result.get("efa")
        cfa = family_result.get("cfa")
        invariance = family_result.get("invariance")
        bifactor = family_result.get("bifactor")
        esem = family_result.get("esem")
        irt = family_result.get("irt")
        cmb = family_result.get("commonMethodBias")
        marker = cmb.get("markerVariable") if isinstance(cmb, dict) else None
        ulmc = cmb.get("ulmc") if isinstance(cmb, dict) else None
        cfa_fit = (
            {
                key: cfa.get(key)
                for key in (
                    "chiSquare",
                    "degreesOfFreedom",
                    "pValue",
                    "cfi",
                    "tli",
                    "rmsea",
                    "rmseaCiLower",
                    "rmseaCiUpper",
                    "srmr",
                    "estimator",
                    "hasHeywoodCase",
                )
            }
            if isinstance(cfa, dict)
            else {}
        )
        tables.extend(
            [
                _table(
                    "Reliability by construct",
                    _rows(reliability.get("constructs") if isinstance(reliability, dict) else None),
                ),
                _table(
                    "Structural missingness",
                    _object_value_rows(
                        reliability.get("structuralMissingness")
                        if isinstance(reliability, dict)
                        else None,
                        "constructId",
                    ),
                ),
                _table(
                    "EFA factor-selection diagnostics",
                    _metric_rows(efa.get("map") if isinstance(efa, dict) else None)
                    + _metric_rows(efa.get("parallelAnalysis") if isinstance(efa, dict) else None)
                    + _metric_rows(efa.get("splitValidation") if isinstance(efa, dict) else None),
                ),
                _table(
                    "EFA loadings", _rows(efa.get("loadings") if isinstance(efa, dict) else None)
                ),
                _table("CFA fit indices", _metric_rows(cfa_fit)),
                _table(
                    "CFA standardized loadings",
                    _aligned_rows(
                        cfa.get("itemIds") if isinstance(cfa, dict) else None,
                        cfa.get("standardizedLoadings") if isinstance(cfa, dict) else None,
                        "standardizedLoading",
                    ),
                ),
                _table(
                    "Measurement invariance models",
                    _object_value_rows(
                        invariance.get("models") if isinstance(invariance, dict) else None
                    ),
                ),
                _table(
                    "Measurement invariance comparisons",
                    _object_value_rows(
                        invariance.get("comparisons") if isinstance(invariance, dict) else None
                    ),
                ),
                _table(
                    "Latent means",
                    _rows(invariance.get("latentMeans") if isinstance(invariance, dict) else None),
                ),
                _table(
                    "Partial-invariance diagnostics",
                    _rows(
                        invariance.get("partialReleasedParameters")
                        if isinstance(invariance, dict)
                        else None
                    ),
                ),
                _table(
                    "Bifactor fit indices",
                    _metric_rows(
                        bifactor.get("fitIndices") if isinstance(bifactor, dict) else None
                    ),
                ),
                _table(
                    "Bifactor indices",
                    _metric_rows(
                        bifactor.get("bifactorMetrics") if isinstance(bifactor, dict) else None
                    ),
                ),
                _table(
                    "Bifactor item details",
                    _rows(bifactor.get("itemDetails") if isinstance(bifactor, dict) else None),
                ),
                _table(
                    "ESEM loadings", _rows(esem.get("loadings") if isinstance(esem, dict) else None)
                ),
                _table(
                    "IRT item parameters",
                    _rows(irt.get("itemParameters") if isinstance(irt, dict) else None),
                ),
                _table(
                    "IRT DIF diagnostics",
                    _rows(irt.get("difAnalysis") if isinstance(irt, dict) else None),
                ),
                _table(
                    "Marker-variable CMB diagnostics",
                    _metric_rows(
                        {
                            key: marker.get(key)
                            for key in (
                                "method",
                                "markerVariableId",
                                "r_m",
                                "sampleSize",
                                "methodologicalWarning",
                            )
                        }
                        if isinstance(marker, dict)
                        else None
                    ),
                ),
                _table(
                    "ULMC model comparison",
                    _metric_rows(ulmc.get("baselineModel") if isinstance(ulmc, dict) else None)
                    + _metric_rows(ulmc.get("ulmcModel") if isinstance(ulmc, dict) else None)
                    + _metric_rows(ulmc.get("modelComparison") if isinstance(ulmc, dict) else None),
                ),
            ]
        )
    elif family == "power_analysis":
        tables.extend(
            [
                _table("Power result", [family_result]),
                _table("Power curve", list(family_result.get("powerCurve", []))),
            ]
        )
    return tables


def _markdown_table(rows: list[JsonObject]) -> str:
    if not rows:
        return "（无记录）"
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    lines = ["| " + " | ".join(keys) + " |", "| " + " | ".join("---" for _ in keys) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_cell(row.get(key)) for key in keys) + " |")
    return "\n".join(lines)


def build_advanced_paper_report(
    spec: AdvancedAnalysisSpec,
    result: JsonObject,
    tables: list[JsonObject],
    *,
    include_data: bool,
) -> str:
    lines = [
        f"# {spec.name} 高级分析报告",
        "",
        "> 本报告由 AdvancedResultBundle 的原始字段映射生成；显示格式不重新计算统计量。高级方法当前仍属于 experimental，不能替代方法学复核。",
        "",
        "## 研究规格",
        "",
        f"- 分析 ID：`{spec.analysis_id}`",
        f"- family：`{spec.family}`",
        f"- 规格哈希：`{result['run']['specHash']}`",
        f"- 数据版本：`{spec.dataset_version_id or '不适用（解析功效）'}`",
        f"- 数据是否包含在本包：`{'是' if include_data else '否'}`",
        "",
        "## 样本流与结果",
        "",
        _markdown_table([result.get("sampleFlow", {})]),
        "",
    ]
    for table in tables:
        lines.extend([f"## {table['title']}", "", _markdown_table(table["rows"]), ""])
    apa_reports = [
        text for text in result.get("apaReports", []) if isinstance(text, str) and text.strip()
    ]
    lines.extend(["## APA 结果文本", ""])
    if apa_reports:
        lines.extend([f"- {text}" for text in apa_reports])
    else:
        lines.append("（当前结果没有可报告的 APA 文本）")
    lines.extend(["", "## 警告与诊断", ""])
    messages = [*result.get("diagnostics", []), *result.get("warnings", [])]
    if messages:
        lines.extend(
            f"- `{item.get('code', 'UNKNOWN')}` {item.get('message', '')}" for item in messages
        )
    else:
        lines.append("（无结构化警告或诊断）")
    lines.extend(
        ["", "## 复现说明", "", "完整规格、结果、R runner、provenance 和文件校验值见本导出包。"]
    )
    return "\n".join(lines) + "\n"


def _write_manifest(root: Path, *, run_id: str, spec_hash: str, include_data: bool) -> None:
    files: list[JsonObject] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    _write_json(
        root / "provenance" / "manifest.json",
        {
            "schemaVersion": "1.0.0",
            "runId": run_id,
            "specHash": spec_hash,
            "includeData": include_data,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "files": files,
        },
    )


def create_advanced_export_bundle(
    requested_run_id: str,
    state: JsonObject,
    spec: AdvancedAnalysisSpec,
    result: JsonObject,
    repository: DatasetRepository,
    settings: Settings,
    include_data: bool,
) -> Path:
    try:
        run_id = safe_identifier(requested_run_id, label="advanced analysis run id")
    except UnsafePathError as error:
        raise ValueError("高级分析运行标识不安全") from error
    if state.get("id") != run_id or result.get("run", {}).get("id") != run_id:
        raise ValueError("高级分析结果身份与请求不匹配")
    if state.get("status") != "succeeded" or not state.get("resultPath"):
        raise ValueError("只有成功完成的高级分析可以导出")
    spec_hash = _canonical_advanced_hash(spec)
    if state.get("specHash") != spec_hash or result.get("run", {}).get("specHash") != spec_hash:
        raise ValueError("高级分析规格哈希与结果不匹配")
    validate_contract(result, settings.advanced_result_schema_path)

    dataset: JsonObject | None = None
    data_path: Path | None = None
    if spec.dataset_version_id is not None:
        dataset = repository.get_dataset(spec.dataset_version_id)
        data_path = resolve_normalized_dataset_path(settings.state_root, dataset)
    if include_data and data_path is None:
        raise ValueError("解析功效没有数据版本，不能请求包含数据的导出包")

    export_dir = settings.state_root / "projects" / "default" / "runs" / run_id / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    target = export_dir / f"{run_id}-advanced-{'with-data' if include_data else 'no-data'}.zip"
    temporary_target = target.with_suffix(".zip.tmp")
    if temporary_target.exists():
        temporary_target.unlink()

    tables = build_advanced_paper_tables(result)
    report = build_advanced_paper_report(spec, result, tables, include_data=include_data)
    with tempfile.TemporaryDirectory(
        prefix="researchpath-advanced-export-", dir=export_dir
    ) as temporary:
        root = Path(temporary) / f"{run_id}-export"
        root.mkdir()
        _write_json(
            root / "specification" / "advanced-spec.json",
            spec.model_dump(mode="json", by_alias=True),
        )
        _write_json(root / "result" / "advanced-result.json", result)
        _write_json(root / "paper" / "tables.json", tables)
        _write_json(root / "paper" / "apa.json", {"reports": result.get("apaReports", [])})
        (root / "paper" / "report.md").parent.mkdir(parents=True, exist_ok=True)
        (root / "paper" / "report.md").write_text(report, encoding="utf-8")
        _write_json(root / "provenance" / "result-provenance.json", result.get("provenance", {}))
        _write_json(
            root / "provenance" / "data-manifest.json",
            {
                "datasetVersionId": spec.dataset_version_id,
                "sourceSha256": dataset.get("originalFile", {}).get("sha256") if dataset else None,
                "included": include_data,
                "normalizedSha256": _sha256(data_path) if data_path is not None else None,
            },
        )
        (root / "README.md").write_text(
            "# ResearchPath 高级分析复现包\n\n"
            f"对应运行：`{run_id}`\n\n"
            "先阅读 `paper/report.md`，再核对 `specification/advanced-spec.json`、"
            "`result/advanced-result.json` 和 `provenance/manifest.json`。\n"
            "本包不把 experimental 方法声明为 supported。\n",
            encoding="utf-8",
        )
        reproduction = root / "reproduction"
        reproduction.mkdir()
        runner = settings.project_root / "engine" / "R" / "run_advanced_analysis.R"
        if not runner.is_file():
            raise ValueError("高级分析 R runner 不存在")
        shutil.copy2(runner, reproduction / "run_advanced_analysis.R")
        reproduction_input = {
            "spec": spec.model_dump(mode="json", by_alias=True),
            "dataPath": "../data/analysis-data.parquet" if include_data else None,
            "artifactDirectory": "../artifacts",
        }
        _write_json(reproduction / "input.json", reproduction_input)
        (reproduction / "reproduce.ps1").write_text(
            "$ErrorActionPreference = 'Stop'\n"
            "New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot '..\\artifacts') | Out-Null\n"
            "& Rscript --vanilla (Join-Path $PSScriptRoot 'run_advanced_analysis.R') "
            "(Join-Path $PSScriptRoot 'input.json') (Join-Path $PSScriptRoot '..\\reproduced-result.json')\n",
            encoding="utf-8",
        )
        if include_data and data_path is not None:
            (root / "data").mkdir()
            shutil.copy2(data_path, root / "data" / "analysis-data.parquet")
        _write_manifest(root, run_id=run_id, spec_hash=spec_hash, include_data=include_data)
        with ZipFile(temporary_target, "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(item for item in root.rglob("*") if item.is_file()):
                archive.write(path, path.relative_to(root).as_posix())
    os.replace(temporary_target, target)
    return target
