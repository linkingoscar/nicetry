from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from app.services import empirical_export_sections as sections
from app.services.empirical_export_support import append_sheet as _append_sheet
from app.services.empirical_longitudinal_export import append_longitudinal_method_sections
from app.services.empirical_options_validator import EmpiricalAnalysisError
from app.settings import Settings


def empirical_report_path(
    dataset_id: str, measurement_version: int | None, report_id: str, settings: Settings
) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", dataset_id):
        raise EmpiricalAnalysisError("数据集 ID 无效")
    if not report_id.startswith("empirical_") or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789_" for character in report_id
    ):
        raise EmpiricalAnalysisError("实证报告 ID 无效")
    if measurement_version is not None and (isinstance(measurement_version, bool) or measurement_version < 1):
        raise EmpiricalAnalysisError("测量版本必须是正整数或未指定")
    dataset_root = (
        settings.state_root
        / "projects"
        / "default"
        / "datasets"
        / dataset_id
    )
    scope = dataset_root / "measurement" / f"v{measurement_version}" if measurement_version is not None else dataset_root
    return scope / "empirical" / report_id / "report.json"


def export_empirical_workbook(
    dataset_id: str,
    measurement_version: int | None,
    report_id: str,
    settings: Settings,
) -> Path:
    report_path = empirical_report_path(dataset_id, measurement_version, report_id, settings)
    if not report_path.exists():
        raise EmpiricalAnalysisError(f"实证报告不存在: {report_id}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    workbook = Workbook()
    workbook.remove(workbook.active)
    _append_sheet(
        workbook,
        "描述统计",
        [["变量", "N", "缺失", "均值", "标准差", "最小值", "最大值", "偏度", "峰度", "极端值数"]]
        + [
            [
                row["label"],
                row["n"],
                row["missing"],
                row["mean"],
                row["sd"],
                row["minimum"],
                row["maximum"],
                row["skewness"],
                row["kurtosis"],
                row["outlierCount"],
            ]
            for row in report["descriptives"]
        ],
    )
    _append_sheet(
        workbook,
        "频数分布",
        [["变量", "水平", "频数", "比例"]]
        + [
            [row["label"], level["level"], level["count"], level["proportion"]]
            for row in report["frequencies"]
            for level in row["levels"]
        ],
    )
    sections.append_correlation_sections(workbook, report, _append_sheet)
    sections.append_missing_data_sections(
        workbook, report.get("missingDataReport"), _append_sheet
    )
    sections.append_measurement_invariance_section(
        workbook, report.get("measurementInvariance"), _append_sheet
    )
    sections.append_response_surface_sections(
        workbook, report.get("responseSurface"), _append_sheet
    )
    factorability = report["factorability"]
    common_method = report["commonMethodBias"]
    _append_sheet(
        workbook,
        "方法诊断",
        [["诊断", "统计量", "df/计数", "p", "方法说明"]]
        + [
            [
                "KMO",
                factorability.get("kmo"),
                factorability.get("completeCases"),
                None,
                "Kaiser-Meyer-Olkin",
            ],
            [
                "Bartlett球形检验",
                factorability.get("bartlett", {}).get("statistic"),
                factorability.get("bartlett", {}).get("degreesOfFreedom"),
                factorability.get("bartlett", {}).get("pValue"),
                "Bartlett test of sphericity",
            ],
            [
                "Harman第一因子解释率(%)",
                common_method.get("firstFactorVariancePercent"),
                common_method.get("eigenvaluesAboveOne"),
                None,
                common_method.get("method"),
            ],
        ],
    )
    sections.append_measurement_method_section(workbook, report, _append_sheet)
    _append_sheet(
        workbook,
        "信效度",
        [["构念", "α", "ω", "CR", "AVE", "sqrt(AVE)", "区分效度状态", "载荷来源"]]
        + [
            [
                row["label"],
                row["alpha"],
                row["omega"],
                row["compositeReliability"],
                row["averageVarianceExtracted"],
                row["sqrtAve"],
                row.get("discriminantValidityStatus", "not_evaluable"),
                row.get("loadingSource"),
            ]
            for row in report["validity"]["constructs"]
        ],
    )
    validity = report["validity"]
    construct_labels = validity["constructLabels"]
    for sheet_name, matrix in (
        ("Fornell-Larcker", validity.get("fornellLarcker")),
        ("HTMT", validity.get("htmt")),
        ("HTMT CI下限", validity.get("htmtCiLower")),
        ("HTMT CI上限", validity.get("htmtCiUpper")),
    ):
        if matrix:
            rows = [["构念"] + construct_labels]
            rows.extend([construct_labels[index]] + row for index, row in enumerate(matrix))
            if sheet_name == "Fornell-Larcker":
                rows.append(["相关来源", validity.get("fornellCorrelationSource")])
            _append_sheet(workbook, sheet_name, rows)
    _append_sheet(
        workbook,
        "EFA载荷",
        [["题项"] + report["efa"]["factorLabels"] + ["共同度"]]
        + [
            [row["label"]] + row["loadings"] + [row["communality"]]
            for row in report["efa"]["loadings"]
        ],
    )
    efa = report["efa"]
    if efa.get("factorCorrelations"):
        _append_sheet(
            workbook,
            "EFA因子相关",
            [["因子"] + efa["factorLabels"]]
            + [
                [efa["factorLabels"][index]] + row
                for index, row in enumerate(efa["factorCorrelations"])
            ],
        )
    if efa.get("structureMatrix"):
        _append_sheet(
            workbook,
            "EFA结构矩阵",
            [["题项"] + efa["factorLabels"]]
            + [
                [efa["loadings"][index]["label"]] + row
                for index, row in enumerate(efa["structureMatrix"])
            ],
        )
    cfa = report.get("cfa", {})
    if cfa.get("available"):
        _append_sheet(
            workbook,
            "CFA拟合",
            [["指标", "数值"]]
            + [
                ["收敛", cfa.get("converged")],
                ["完整案例N", cfa.get("completeCases")],
                ["Chi-Square", cfa.get("chiSquare")],
                ["df", cfa.get("degreesOfFreedom")],
                ["p", cfa.get("pValue")],
                ["CFI", cfa.get("cfi")],
                ["TLI", cfa.get("tli")],
                ["RMSEA", cfa.get("rmsea")],
                ["RMSEA 90% CI下限", cfa.get("rmseaCiLower")],
                ["RMSEA 90% CI上限", cfa.get("rmseaCiUpper")],
                ["SRMR", cfa.get("srmr")],
                ["估计器", cfa.get("estimator")],
            ],
        )
        item_labels = {row["itemId"]: row["label"] for row in efa.get("loadings", [])}
        _append_sheet(
            workbook,
            "CFA标准化载荷",
            [["题项ID", "题项", "标准化载荷"]]
            + [
                [item_id, item_labels.get(item_id, item_id), loading]
                for item_id, loading in zip(
                    cfa.get("itemIds", []), cfa.get("standardizedLoadings", []), strict=False
                )
            ],
        )
    if report.get("aggregationDiagnostics"):
        aggregation = report["aggregationDiagnostics"]
        _append_sheet(
            workbook,
            "聚合诊断",
            [
                [
                    "cluster 变量",
                    "构念",
                    "可计算",
                    "有效N",
                    "cluster数",
                    "最小规模",
                    "最大规模",
                    "有效平均规模",
                    "ICC(1)",
                    "ICC(2)",
                    "设计效应",
                    "平均rwg(j)",
                    "中位rwg(j)",
                    "rwg≥.70比例",
                    "不可用原因",
                ]
            ]
            + [
                [
                    aggregation.get("groupLabel"),
                    row.get("label"),
                    row.get("available"),
                    row.get("observations"),
                    row.get("clusterCount"),
                    row.get("minimumClusterSize"),
                    row.get("maximumClusterSize"),
                    row.get("averageClusterSize"),
                    row.get("icc1"),
                    row.get("icc2"),
                    row.get("designEffect"),
                    row.get("rwg", {}).get("mean"),
                    row.get("rwg", {}).get("median"),
                    row.get("rwg", {}).get("proportionAtLeastPoint70"),
                    row.get("reason"),
                ]
                for row in aggregation.get("constructs", [])
            ],
        )
    if report.get("groupComparison"):
        group_rows = report["groupComparison"]["results"]
        group_confidence_label = sections.confidence_label(
            (report.get("options") or {}).get("confidenceLevel")
        )
        _append_sheet(
            workbook,
            "组间差异",
            [["变量", "检验", "统计量", "df1", "df2", "原始p", "调整p", "family", "family size", "adjustment", "效应量", f"{group_confidence_label}下限", f"{group_confidence_label}上限", "omega squared", "效应量类型"]]
            + [
                [
                    row["label"],
                    row["test"],
                    row["statistic"],
                    row.get("df1"),
                    row.get("df2"),
                    row.get("pValueRaw"), row.get("pValueAdjusted", row.get("pValue")),
                    row.get("multiplicityFamilyId"), row.get("multiplicityFamilySize"), row.get("pAdjustMethod"),
                    row["effectSize"],
                    row.get("effectSizeCiLower"),
                    row.get("effectSizeCiUpper"),
                    row.get("omegaSquared"),
                    row["effectSizeType"],
                ]
                for row in group_rows
            ],
        )
        _append_sheet(
            workbook,
            "组别描述",
            [["变量", "组别", "N", "均值", "标准差"]]
            + [
                [row["label"], group["level"], group["n"], group["mean"], group["sd"]]
                for row in group_rows
                for group in row.get("groups", [])
            ],
        )
        robust_rows: list[list[Any]] = [["变量", "方法", "统计量", "df1", "df2", "原始p", "调整p", "family"]]
        for row in group_rows:
            brown = row.get("assumptionTests", {}).get("brownForsythe")
            if brown:
                robust_rows.append(
                    [
                        row["label"],
                        "Brown-Forsythe方差稳健性检验",
                        brown.get("statistic"),
                        brown.get("df1"),
                        brown.get("df2"),
                        brown.get("pValueRaw"), brown.get("pValueAdjusted", brown.get("pValue")),
                        brown.get("multiplicityFamilyId"),
                    ]
                )
            robust = row.get("robustTest")
            if robust:
                robust_rows.append(
                    [
                        row["label"],
                        robust.get("method"),
                        robust.get("statistic"),
                        robust.get("df1"),
                        robust.get("df2"),
                        robust.get("pValueRaw"), robust.get("pValueAdjusted", robust.get("pValue")),
                        robust.get("multiplicityFamilyId"),
                    ]
                )
        if len(robust_rows) > 1:
            _append_sheet(workbook, "稳健组间检验", robust_rows)

        posthoc_rows: list[list[Any]] = [
            ["变量", "方法", "比较", "差值", "SE", "df", "CI下限", "CI上限", "校正p"]
        ]
        for row in group_rows:
            for comparison in row.get("pairwiseTukey", []):
                posthoc_rows.append(
                    [
                        row["label"],
                        "Tukey HSD",
                        comparison.get("comparison"),
                        comparison.get("difference"),
                        None,
                        None,
                        comparison.get("lower"),
                        comparison.get("upper"),
                        comparison.get("pValue"),
                    ]
                )
            for comparison in row.get("pairwiseBonferroni", []):
                posthoc_rows.append(
                    [
                        row["label"],
                        "Bonferroni",
                        comparison.get("comparison"),
                        None,
                        None,
                        None,
                        None,
                        None,
                        comparison.get("pValue"),
                    ]
                )
            for comparison in row.get("pairwiseGamesHowell", []):
                posthoc_rows.append(
                    [
                        row["label"],
                        "Games-Howell",
                        comparison.get("comparison"),
                        comparison.get("difference"),
                        comparison.get("standardError"),
                        comparison.get("degreesOfFreedom"),
                        comparison.get("lower"),
                        comparison.get("upper"),
                        comparison.get("pValue"),
                    ]
                )
        if len(posthoc_rows) > 1:
            _append_sheet(workbook, "事后比较", posthoc_rows)
    if report.get("hierarchicalRegression"):
        regression = report["hierarchicalRegression"]
        _append_sheet(
            workbook,
            "分层回归区块",
            [["区块", "公式", "N", "R²", "调整R²", "ΔR²", "F-change", "df1", "df2", "p-change"]]
            + [
                [
                    block["block"],
                    block["formula"],
                    regression["n"],
                    block["rSquared"],
                    block["adjustedRSquared"],
                    regression["change"].get("deltaRSquared") if block["block"] == 2 else None,
                    regression["change"].get("statistic") if block["block"] == 2 else None,
                    regression["change"].get("df1") if block["block"] == 2 else None,
                    regression["change"].get("df2") if block["block"] == 2 else None,
                    regression["change"].get("pValue") if block["block"] == 2 else None,
                ]
                for block in regression["blocks"]
            ],
        )
        _append_sheet(
            workbook,
            "分层回归",
            [
                [
                    "区块",
                    "变量",
                    "B",
                    "SE",
                    "t",
                    "p",
                    "标准化β",
                    "partial f²",
                    "CI下限",
                    "CI上限",
                    "VIF",
                ]
            ]
            + [
                [
                    block["block"],
                    coefficient["label"],
                    coefficient["estimate"],
                    coefficient["standardError"],
                    coefficient["statistic"],
                    coefficient["pValue"],
                    coefficient.get("standardizedEstimate"),
                    coefficient.get("cohenF2"),
                    coefficient["lower"],
                    coefficient["upper"],
                    coefficient.get("vif"),
                ]
                for block in regression["blocks"]
                for coefficient in block["coefficients"]
            ],
        )
        sections.append_regression_robustness_sections(workbook, regression, _append_sheet)
        sections.append_relative_importance_section(
            workbook, regression.get("relativeImportance"), _append_sheet
        )
    append_longitudinal_method_sections(workbook, report, _append_sheet)
    _append_sheet(
        workbook,
        "方法与来源",
        [["区块", "字段", "值"],
         ["结果身份", "reportId", report_id],
         ["结果身份", "datasetId", dataset_id],
         ["结果身份", "measurementVersion", measurement_version],
         ["结果身份", "measurementVersionId", report.get("measurementVersionId")]]
        + [
            [
                "分析选项",
                key,
                json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value,
            ]
            for key, value in report.get("options", {}).items()
        ]
        + [
            [
                "来源",
                key,
                json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value,
            ]
            for key, value in report["provenance"].items()
        ]
        + [
            ["警告", warning.get("code"), warning.get("message")]
            for warning in report.get("warnings", [])
        ],
    )
    from app.services.empirical_procedure_reporting import scope_procedure_workbook

    scope_procedure_workbook(workbook, report)
    target = report_path.parent / f"{report_id}-论文表格.xlsx"
    temporary = target.with_suffix(".xlsx.tmp")
    workbook.save(temporary)
    os.replace(temporary, target)
    return target
