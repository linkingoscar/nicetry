from __future__ import annotations

import json
from typing import Any, TypeAlias

from app.advanced_contracts import AdvancedAnalysisSpec
from app.services.report_facts import report_fact_rows

# The result bundle is schema-validated at the export boundary and intentionally
# preserves family-specific JSON shapes that are not representable by one static
# Python model. Keep the looseness isolated to this serialization module.
JsonValue: TypeAlias = Any
JsonObject = dict[str, JsonValue]


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
    fact_rows = report_fact_rows(result)
    if fact_rows:
        tables.append(_table("报告事实", fact_rows))
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
                _table("CFA method execution", _metric_rows(cfa.get("methodExecution") if isinstance(cfa, dict) else None)),
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
                _table("Bifactor method execution", _metric_rows(bifactor.get("methodExecution") if isinstance(bifactor, dict) else None)),
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
                _table("ESEM method execution", _metric_rows(esem.get("methodExecution") if isinstance(esem, dict) else None)),
                _table(
                    "IRT item parameters",
                    _rows(irt.get("itemParameters") if isinstance(irt, dict) else None),
                ),
                _table("IRT method execution", _metric_rows(irt.get("methodExecution") if isinstance(irt, dict) else None)),
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
    fact_table = next((table for table in tables if table["title"] == "报告事实"), None)
    if fact_table:
        lines.extend(["## 报告事实叙述", ""])
        for row in fact_table["rows"]:
            label = row.get("label", row.get("factId", "fact"))
            lines.append(
                f"- {label}：{_cell(row.get('value'))}（sourcePath `{row.get('sourcePath')}`）"
            )
        lines.append("")
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
