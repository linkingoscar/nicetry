from __future__ import annotations

from typing import Any

from openpyxl import Workbook

from app.services.empirical_advanced_method_export import (
    append_diary_advanced_model_sheets,
    append_diary_protocol_sheets,
    append_lcm_sr_growth_sheet,
    append_longitudinal_cmb_sheets,
)
from app.services.empirical_export_sections import AppendSheet
from app.services.empirical_power_export import append_power_method_sections


def append_longitudinal_method_sections(
    workbook: Workbook,
    report: dict[str, Any],
    append_sheet: AppendSheet,
) -> None:
    panel = report.get("longitudinalPanel")
    if panel:
        fit = panel.get("fitIndices", {})
        append_sheet(
            workbook,
            "纵向模型拟合",
            [
                [
                    "模型",
                    "N",
                    "波次",
                    "估计器",
                    "缺失",
                    "跨时约束",
                    "χ²",
                    "df",
                    "p",
                    "CFI",
                    "TLI",
                    "RMSEA",
                    "SRMR",
                    "AIC",
                    "BIC",
                    "可解释",
                ]
            ]
            + [
                [
                    panel.get("modelLabel"),
                    panel.get("sampleSize"),
                    panel.get("waveCount"),
                    panel.get("estimator"),
                    panel.get("missingMethod"),
                    panel.get("constrainedAcrossTime"),
                    fit.get("chiSquare"),
                    fit.get("degreesOfFreedom"),
                    fit.get("pValue"),
                    fit.get("cfi"),
                    fit.get("tli"),
                    fit.get("rmsea"),
                    fit.get("srmr"),
                    fit.get("aic"),
                    fit.get("bic"),
                    panel.get("validForInterpretation"),
                ]
            ],
        )
        append_sheet(
            workbook,
            "纵向路径",
            [
                [
                    "类型",
                    "方向",
                    "起始波次",
                    "目标波次",
                    "B",
                    "标准化β",
                    "SE",
                    "z",
                    "p",
                    "CI下限",
                    "CI上限",
                ]
            ]
            + [
                [
                    row.get("pathType"),
                    row.get("direction"),
                    row.get("fromWave"),
                    row.get("toWave"),
                    row.get("estimate"),
                    row.get("standardizedEstimate"),
                    row.get("standardError"),
                    row.get("statistic"),
                    row.get("pValue"),
                    row.get("lower"),
                    row.get("upper"),
                ]
                for row in panel.get("paths", [])
            ],
        )
        append_sheet(
            workbook,
            "纵向样本流",
            [["波次", "时间值", "有效", "上期保留", "流失", "重新进入"]]
            + [
                [
                    row.get("label"),
                    row.get("timeValue"),
                    row.get("observed"),
                    row.get("retainedFromPrevious"),
                    row.get("attritionFromPrevious"),
                    row.get("reenteredFromPrevious"),
                ]
                for row in panel.get("waveSampleFlow", [])
            ],
        )
        invariance = panel.get("measurementInvariance")
        if invariance:
            append_sheet(
                workbook,
                "纵向测量等值性",
                [
                    [
                        "层级",
                        "标签",
                        "N",
                        "收敛",
                        "χ²",
                        "df",
                        "p",
                        "CFI",
                        "TLI",
                        "RMSEA",
                        "SRMR",
                        "AIC",
                        "BIC",
                    ]
                ]
                + [
                    [
                        row.get("level"),
                        row.get("label"),
                        row.get("sampleSize"),
                        row.get("converged"),
                        row.get("fitIndices", {}).get("chiSquare"),
                        row.get("fitIndices", {}).get("degreesOfFreedom"),
                        row.get("fitIndices", {}).get("pValue"),
                        row.get("fitIndices", {}).get("cfi"),
                        row.get("fitIndices", {}).get("tli"),
                        row.get("fitIndices", {}).get("rmsea"),
                        row.get("fitIndices", {}).get("srmr"),
                        row.get("fitIndices", {}).get("aic"),
                        row.get("fitIndices", {}).get("bic"),
                    ]
                    for row in invariance.get("models", [])
                ],
            )
            append_sheet(
                workbook,
                "纵向等值性比较",
                [
                    [
                        "起始层级",
                        "目标层级",
                        "ΔCFI",
                        "ΔRMSEA",
                        "ΔSRMR",
                        "Δχ²",
                        "Δdf",
                        "p",
                        "实用标准通过",
                        "判据",
                    ]
                ]
                + [
                    [
                        row.get("from"),
                        row.get("to"),
                        row.get("deltaCfi"),
                        row.get("deltaRmsea"),
                        row.get("deltaSrmr"),
                        row.get("chiSquareDifference"),
                        row.get("degreesOfFreedomDifference"),
                        row.get("pValue"),
                        row.get("passesPracticalCriteria"),
                        row.get("criteria"),
                    ]
                    for row in invariance.get("comparisons", [])
                ],
            )
        if panel.get("competingModels"):
            append_sheet(
                workbook,
                "纵向竞争模型",
                [["模型", "收敛", "CFI", "TLI", "RMSEA", "SRMR", "AIC", "BIC"]]
                + [
                    [
                        row.get("modelLabel"),
                        row.get("converged"),
                        row.get("fitIndices", {}).get("cfi"),
                        row.get("fitIndices", {}).get("tli"),
                        row.get("fitIndices", {}).get("rmsea"),
                        row.get("fitIndices", {}).get("srmr"),
                        row.get("fitIndices", {}).get("aic"),
                        row.get("fitIndices", {}).get("bic"),
                    ]
                    for row in panel.get("competingModels", [])
                ],
            )
        append_lcm_sr_growth_sheet(workbook, panel, append_sheet)
        append_longitudinal_cmb_sheets(workbook, panel, append_sheet)
        if panel.get("robustnessChecks"):
            append_sheet(
                workbook,
                "纵向稳健性矩阵",
                [
                    [
                        "情景",
                        "模型",
                        "N",
                        "估计器",
                        "缺失",
                        "跨时约束",
                        "CFI",
                        "RMSEA",
                        "SRMR",
                        "AIC",
                        "BIC",
                        "可解释",
                    ]
                ]
                + [
                    [
                        row.get("scenario"),
                        row.get("modelType"),
                        row.get("sampleSize"),
                        row.get("estimator"),
                        row.get("missingMethod"),
                        row.get("constrainedAcrossTime"),
                        row.get("fitIndices", {}).get("cfi"),
                        row.get("fitIndices", {}).get("rmsea"),
                        row.get("fitIndices", {}).get("srmr"),
                        row.get("fitIndices", {}).get("aic"),
                        row.get("fitIndices", {}).get("bic"),
                        row.get("validForInterpretation"),
                    ]
                    for row in panel.get("robustnessChecks", [])
                ],
            )
        append_power_method_sections(workbook, panel, None, append_sheet)

    diary = report.get("diaryMultilevel")
    if not diary:
        return
    append_sheet(
        workbook,
        "多层模型摘要",
        [
            [
                "模型",
                "分析类型",
                "观测数",
                "被试数",
                "中心化",
                "时间效应",
                "滞后阶数",
                "缺失策略",
                "插补数",
                "残差结构",
                "AR1",
                "ICC",
                "边际R²",
                "条件R²",
                "奇异拟合",
                "可解释",
            ]
        ]
        + [
            [
                diary.get("modelLabel"),
                diary.get("analysisType"),
                diary.get("sampleSize"),
                diary.get("personCount"),
                diary.get("centering"),
                diary.get("temporalEffect"),
                diary.get("lagOrder"),
                diary.get("missingData", {}).get("strategy", "complete_cases"),
                diary.get("missingData", {}).get("imputationCount"),
                diary.get("residualStructure"),
                diary.get("ar1"),
                diary.get("icc"),
                diary.get("marginalRSquared"),
                diary.get("conditionalRSquared"),
                diary.get("singular"),
                diary.get("validForInterpretation"),
            ]
        ],
    )
    if diary.get("fixedEffects"):
        append_sheet(
            workbook,
            "多层固定效应",
            [[
                "变量",
                "B",
                "SE",
                "df",
                "t/z",
                "p",
                "CI下限",
                "CI上限",
                "OR/IRR",
                "OR/IRR下限",
                "OR/IRR上限",
                "FMI",
            ]]
            + [
                [
                    row.get("label"),
                    row.get("estimate"),
                    row.get("standardError"),
                    row.get("degreesOfFreedom"),
                    row.get("statistic"),
                    row.get("pValue"),
                    row.get("lower"),
                    row.get("upper"),
                    row.get("exponentiatedEstimate"),
                    row.get("exponentiatedLower"),
                    row.get("exponentiatedUpper"),
                    row.get("fractionMissingInformation"),
                ]
                for row in diary.get("fixedEffects", [])
            ],
        )
    append_diary_protocol_sheets(workbook, diary, append_sheet)
    append_diary_advanced_model_sheets(workbook, diary, append_sheet)
    if diary.get("indirectEffects"):
        append_sheet(
            workbook,
            "多层中介",
            [["效应", "估计", "SE", "z", "p", "CI下限", "CI上限"]]
            + [
                [
                    row.get("id"),
                    row.get("estimate"),
                    row.get("standardError"),
                    row.get("statistic"),
                    row.get("pValue"),
                    row.get("lower"),
                    row.get("upper"),
                ]
                for row in diary.get("indirectEffects", [])
            ],
        )
    quality = diary.get("dataQuality")
    if quality:
        compliance = quality.get("personCompliance", {})
        latency = quality.get("responseLatency") or {}
        append_sheet(
            workbook,
            "ESM数据质量",
            [
                [
                    "被试数",
                    "提示记录",
                    "预期次数/人",
                    "总体依从率",
                    "个人依从率最小值",
                    "中位数",
                    "最大值",
                    "低于阈值人数",
                    "响应延迟均值",
                    "中位数",
                    "P95",
                    "窗口外记录",
                ]
            ]
            + [
                [
                    quality.get("personCount"),
                    quality.get("observedPromptRows"),
                    quality.get("expectedObservationsPerPerson"),
                    quality.get("overallComplianceRate"),
                    compliance.get("minimum"),
                    compliance.get("median"),
                    compliance.get("maximum"),
                    compliance.get("belowThresholdCount"),
                    latency.get("mean"),
                    latency.get("median"),
                    latency.get("p95"),
                    latency.get("outsideWindowCount"),
                ]
            ],
        )
    if diary.get("multilevelReliability"):
        append_sheet(
            workbook,
            "ESM多层信度",
            [["构念", "题项数", "观测数", "被试数", "Within α", "Between α", "题项平均ICC", "方法"]]
            + [
                [
                    row.get("label"),
                    len(row.get("itemIds", [])),
                    row.get("observationCount"),
                    row.get("personCount"),
                    row.get("withinAlpha"),
                    row.get("betweenAlpha"),
                    row.get("meanItemIcc"),
                    row.get("method"),
                ]
                for row in diary.get("multilevelReliability", [])
            ],
        )
    if diary.get("robustnessChecks"):
        append_sheet(
            workbook,
            "ESM稳健性矩阵",
            [
                [
                    "情景",
                    "模型",
                    "观测数",
                    "被试数",
                    "时间效应",
                    "残差结构",
                    "随机斜率",
                    "可解释",
                ]
            ]
            + [
                [
                    row.get("scenario"),
                    row.get("modelLabel"),
                    row.get("sampleSize"),
                    row.get("personCount"),
                    row.get("temporalEffect"),
                    row.get("residualStructure"),
                    row.get("randomSlope"),
                    row.get("validForInterpretation"),
                ]
                for row in diary.get("robustnessChecks", [])
            ],
        )
    append_power_method_sections(workbook, None, diary, append_sheet)
