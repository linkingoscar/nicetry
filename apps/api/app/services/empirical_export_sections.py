from __future__ import annotations

from collections.abc import Callable
from typing import Any

from openpyxl import Workbook

AppendSheet = Callable[[Workbook, str, list[list[Any]]], None]


def confidence_label(
    value: float | int | str | None, default: float = 0.95, *, suffix: str = "%CI"
) -> str:
    if value is None:
        percent = default * 100
    else:
        try:
            percent = float(value) * 100
        except ValueError:
            percent = default * 100
    rendered = f"{percent:.2f}".rstrip("0").rstrip(".")
    return f"{rendered}{suffix}"


def append_measurement_method_section(
    workbook: Workbook,
    report: dict[str, object],
    append_sheet: AppendSheet,
) -> None:
    def object_mapping(value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    efa = object_mapping(report.get("efa"))
    cfa = object_mapping(report.get("cfa"))
    validity = object_mapping(report.get("validity"))
    efa_execution = object_mapping(efa.get("methodExecution"))
    cfa_execution = object_mapping(cfa.get("methodExecution"))
    validity_execution = object_mapping(validity.get("methodExecution"))
    htmt_execution = object_mapping(validity.get("htmtMethodExecution"))
    header = [
        "分析区块",
        "请求方法",
        "实际方法",
        "发生回退",
        "回退代码",
        "回退原因",
        "受影响输出",
        "解释边界",
    ]

    def execution_row(label: str, execution: dict[str, object]) -> list[object]:
        affected = execution.get("affectedOutputs")
        return [
            label,
            execution.get("requestedMethod"),
            execution.get("executedMethod"),
            execution.get("fallbackApplied", False),
            execution.get("fallbackCode"),
            execution.get("fallbackReason"),
            ", ".join(str(item) for item in affected) if isinstance(affected, list) else "",
            execution.get("interpretationBoundary"),
        ]

    efa_row = execution_row("EFA", efa_execution)
    if not efa_row[2]:
        efa_row[2] = efa.get("method")
    append_sheet(
        workbook,
        "测量方法执行",
        [
            header,
            efa_row,
            execution_row("CFA", cfa_execution),
            execution_row("构念效度", validity_execution),
            execution_row("HTMT", htmt_execution),
        ],
    )


def append_correlation_sections(
    workbook: Workbook,
    report: dict[str, Any],
    append_sheet: AppendSheet,
) -> None:
    correlations = report["correlations"]
    labels = [item["label"] for item in correlations["variables"]]
    correlation_ci_label = confidence_label(correlations.get("confidenceLevel"))
    correlation_sheets = (
        ("相关矩阵", "coefficients"),
        ("相关p值_显示口径", "pValues"),
        ("相关p值_原始", "pValuesRaw"),
        ("相关p值_调整", "pValuesAdjusted"),
        ("相关有效N", "counts"),
        (f"相关{correlation_ci_label}下限", "ciLower"),
        (f"相关{correlation_ci_label}上限", "ciUpper"),
    )
    for sheet_name, field in correlation_sheets:
        if field not in correlations:
            continue
        rows = [[labels[index]] + row for index, row in enumerate(correlations[field])]
        append_sheet(workbook, sheet_name, [["变量"] + labels] + rows)

    multiplicity = correlations.get("multiplicity")
    if isinstance(multiplicity, dict):
        append_sheet(
            workbook,
            "相关多重性",
            [["family", "family size", "adjustment", "scope", "CI simultaneous adjusted"], [
                multiplicity.get("familyId"),
                multiplicity.get("familySize"),
                multiplicity.get("adjustment"),
                multiplicity.get("scope"),
                multiplicity.get("confidenceIntervalsAdjusted"),
            ]],
        )

    paper_table = report.get("paperSummaryTable")
    if not paper_table:
        return
    rows = [["序号", "变量", "N", "均值", "标准差", "alpha", "omega"] + labels]
    for index, row in enumerate(paper_table["rows"]):
        lower_triangle = [
            row["correlations"][column] if column <= index else None
            for column in range(len(labels))
        ]
        rows.append(
            [
                index + 1,
                row["label"],
                row["n"],
                row["mean"],
                row["sd"],
                row["alpha"],
                row["omega"],
            ]
            + lower_triangle
        )
    append_sheet(workbook, "论文整合表", rows)


def append_regression_robustness_sections(
    workbook: Workbook,
    regression: dict[str, Any],
    append_sheet: AppendSheet,
) -> None:
    robustness = regression.get("robustness")
    if not robustness:
        return
    append_sheet(
        workbook,
        "回归稳健SE",
        [["变量", "B", "经典SE", "经典p", "经典CI下限", "经典CI上限", "HC3 SE", "HC3 p", "HC3 CI下限", "HC3 CI上限"]]
        + [
            [
                row["label"], row["estimate"], row["classicStandardError"],
                row["classicPValue"], row["classicLower"], row["classicUpper"],
                row["hc3StandardError"], row["hc3PValue"], row["hc3Lower"], row["hc3Upper"],
            ]
            for row in robustness["standardErrorComparison"]
        ],
    )
    influence = robustness["influence"]
    append_sheet(
        workbook,
        "回归敏感性",
        [["变量", "未加控制B", "完整模型B", "剔除高影响观测B", "控制后变号", "敏感性变号"]]
        + [
            [
                row["label"], row["unadjustedEstimate"], row["adjustedEstimate"],
                row["withoutInfluentialEstimate"], row["signChangedAfterControls"],
                row["signChangedWithoutInfluential"],
            ]
            for row in robustness["coefficientStability"]
        ]
        + [
            [],
            ["高影响观测数", influence["influentialCount"]],
            ["敏感性样本N", influence["retainedCount"]],
            ["Cook阈值", influence["cookDistanceCutoff"]],
            ["杠杆值阈值", influence["leverageCutoff"]],
            ["规则", influence["rule"]],
        ],
    )


def append_measurement_invariance_section(
    workbook: Workbook,
    result: dict[str, Any] | None,
    append_sheet: AppendSheet,
) -> None:
    if not result or not result.get("available"):
        return
    model_rows = [["层级", "χ²", "scaled χ²", "df", "p", "CFI", "robust CFI", "TLI", "robust TLI", "RMSEA", "robust RMSEA", "SRMR"]]
    for level, model in result.get("models", {}).items():
        if not model:
            continue
        model_rows.append(
            [
                level, model.get("chiSquare"), model.get("chiSquareScaled"), model.get("df"),
                model.get("pValue"), model.get("cfi"), model.get("cfiRobust"), model.get("tli"),
                model.get("tliRobust"), model.get("rmsea"), model.get("rmseaRobust"), model.get("srmr"),
            ]
        )
    append_sheet(workbook, "测量等值性", model_rows)
    comparison_rows = [["相邻比较", "Δχ²", "Δdf", "p", "ΔCFI", "ΔRMSEA", "拟合指标口径"]]
    for level, comparison in result.get("comparisons", {}).items():
        comparison_rows.append(
            [
                level, comparison.get("deltaChiSquare"), comparison.get("deltaDf"),
                comparison.get("pValue"), comparison.get("deltaCfi"),
                comparison.get("deltaRmsea"), comparison.get("fitIndexBasis"),
            ]
        )
    append_sheet(workbook, "等值性比较", comparison_rows)


def append_response_surface_sections(
    workbook: Workbook,
    result: dict[str, Any] | None,
    append_sheet: AppendSheet,
) -> None:
    if not result or not result.get("available"):
        return
    interval_label = confidence_label(result.get("confidenceLevel"))
    append_sheet(
        workbook,
        "响应面系数",
        [["变量", "B", "SE", "t", "p", f"{interval_label}下限", f"{interval_label}上限"]]
        + [
            [
                row.get("label"), row.get("estimate"), row.get("standardError"),
                row.get("statistic"), row.get("pValue"), row.get("lower"),
                row.get("upper"),
            ]
            for row in result.get("coefficients", [])
        ],
    )
    append_sheet(
        workbook,
        "响应面检验",
        [["指标", "含义", "估计值", "SE", "t", "p", f"{interval_label}下限", f"{interval_label}上限"]]
        + [
            [
                row.get("id"), row.get("label"), row.get("estimate"),
                row.get("standardError"), row.get("statistic"), row.get("pValue"),
                row.get("lower"), row.get("upper"),
            ]
            for row in result.get("surfaceTests", [])
        ],
    )
    append_sheet(
        workbook,
        "响应面网格",
        [[result.get("xLabel", "X"), result.get("zLabel", "Z"), "预测值"]]
        + [
            [row.get("x"), row.get("z"), row.get("predicted")]
            for row in result.get("grid", [])
        ],
    )


def append_relative_importance_section(
    workbook: Workbook,
    result: dict[str, Any] | None,
    append_sheet: AppendSheet,
) -> None:
    if not result or not result.get("available"):
        return
    append_sheet(
        workbook,
        "相对重要性",
        [["排名", "预测变量", "Shapley/LMG贡献ΔR²", "占焦点ΔR²(%)"]]
        + [
            [
                row.get("rank"), row.get("label"), row.get("contribution"),
                row.get("percentIncrementalRSquared"),
            ]
            for row in result.get("rows", [])
        ]
        + [
            [],
            ["控制模型R²", result.get("baseRSquared")],
            ["完整模型R²", result.get("fullRSquared")],
            ["焦点预测变量ΔR²", result.get("incrementalRSquared")],
            ["贡献之和", result.get("contributionSum")],
            ["子集模型数", result.get("subsetModelCount")],
            ["方法", result.get("method")],
        ],
    )


def append_missing_data_sections(
    workbook: Workbook,
    report: dict[str, Any] | None,
    append_sheet: AppendSheet,
) -> None:
    if not report:
        return

    def missing_pattern_labels(row: dict[str, object]) -> list[str]:
        labels = row.get("missingLabels", [])
        if isinstance(labels, dict):
            return [str(label) for label in labels.values()]
        if isinstance(labels, list):
            return [str(label) for label in labels]
        return []

    append_sheet(
        workbook,
        "缺失变量",
        [["变量", "有效N", "缺失数", "缺失率"]]
        + [
            [
                row.get("label"), row.get("validCount"), row.get("missingCount"),
                row.get("missingRate"),
            ]
            for row in report.get("variables", [])
        ],
    )
    append_sheet(
        workbook,
        "缺失模式",
        [["缺失变量", "行数", "比例"]]
        + [
            [
                "、".join(missing_pattern_labels(row)) or "完整",
                row.get("count"),
                row.get("proportion"),
            ]
            for row in report.get("patterns", [])
        ],
    )
    mcar = report.get("littleMcar", {})
    append_sheet(
        workbook,
        "缺失机制诊断",
        [
            ["字段", "值"],
            ["Little MCAR 可用", mcar.get("available")],
            ["不可用原因", mcar.get("reason")],
            ["χ²", mcar.get("statistic")],
            ["df", mcar.get("degreesOfFreedom")],
            ["p", mcar.get("pValue")],
            ["检验变量", "、".join(mcar.get("variableLabels", []))],
            ["有效N", mcar.get("n")],
            ["缺失模式数", mcar.get("patternCount")],
            ["EM收敛", mcar.get("emConverged")],
            ["EM迭代", mcar.get("emIterations")],
            ["方法", mcar.get("method")],
            ["解释边界", report.get("guidance")],
        ],
    )
