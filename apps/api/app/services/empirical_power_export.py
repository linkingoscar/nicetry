from __future__ import annotations

import json
from typing import Any

from openpyxl import Workbook

from app.services.empirical_export_sections import AppendSheet


def append_power_method_sections(
    workbook: Workbook,
    panel: dict[str, Any] | None,
    diary: dict[str, Any] | None,
    append_sheet: AppendSheet,
) -> None:
    longitudinal = panel.get("powerAnalysis") if panel else None
    if longitudinal:
        append_sheet(
            workbook,
            "纵向功效模拟",
            [
                [
                    "N",
                    "方向",
                    "波次",
                    "真值",
                    "平均估计",
                    "偏差",
                    "经验SE",
                    "平均模型SE",
                    "MSE",
                    "覆盖率",
                    "覆盖率MCSE",
                    "功效",
                    "功效MCSE",
                ]
            ]
            + [
                [
                    row.get("sampleSize"),
                    row.get("directionLabel"),
                    row.get("timePoints"),
                    row.get("populationValue"),
                    row.get("averageEstimate"),
                    row.get("bias"),
                    row.get("empiricalStandardError"),
                    row.get("averageStandardError"),
                    row.get("mse"),
                    row.get("coverage"),
                    row.get("coverageMcse"),
                    row.get("power"),
                    row.get("powerMcse"),
                ]
                for row in longitudinal.get("results", [])
            ],
        )
        append_sheet(
            workbook,
            "纵向功效设计依据",
            [["字段", "冻结值"]]
            + [
                ["方法", longitudinal.get("method")],
                ["目标功效", longitudinal.get("targetPower")],
                ["显著性水平", longitudinal.get("alpha")],
                ["模拟次数", longitudinal.get("replications")],
                ["随机种子", longitudinal.get("seed")],
                ["推荐样本量", longitudinal.get("recommendedSampleSize")],
                ["可用于规划", longitudinal.get("validForPlanning")],
                *[[key, value] for key, value in longitudinal.get("assumptions", {}).items()],
                [
                    "估计问题",
                    json.dumps(
                        longitudinal.get("estimationProblems", []),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                ],
                [
                    "警告",
                    json.dumps(
                        longitudinal.get("warnings", []),
                        ensure_ascii=False,
                    ),
                ],
                [
                    "执行来源",
                    json.dumps(
                        longitudinal.get("provenance", {}),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                ],
            ],
        )

    multilevel = diary.get("powerAnalysis") if diary else None
    if not multilevel:
        return
    append_sheet(
        workbook,
        "ESM功效模拟",
        [
            [
                "人数",
                "每人次数",
                "总观测",
                "成功模拟",
                "失败模拟",
                "奇异拟合",
                "收敛率",
                "平均估计",
                "偏差",
                "经验SE",
                "平均模型SE",
                "覆盖率",
                "覆盖率MCSE",
                "条件功效",
                "保守功效",
                "功效MCSE",
            ]
        ]
        + [
            [
                row.get("personCount"),
                row.get("observationsPerPerson"),
                row.get("totalObservations"),
                row.get("convergedReplications"),
                row.get("failedReplications"),
                row.get("singularReplications"),
                row.get("convergenceRate"),
                row.get("averageEstimate"),
                row.get("bias"),
                row.get("empiricalStandardError"),
                row.get("averageStandardError"),
                row.get("coverage"),
                row.get("coverageMcse"),
                row.get("powerConditionalOnConvergence"),
                row.get("power"),
                row.get("powerMcse"),
            ]
            for row in multilevel.get("results", [])
        ],
    )
    recommendation = multilevel.get("recommendation") or {}
    append_sheet(
        workbook,
        "ESM功效设计依据",
        [["字段", "冻结值"]]
        + [
            ["方法", multilevel.get("method")],
            ["目标参数", multilevel.get("targetParameter")],
            ["目标功效", multilevel.get("targetPower")],
            ["显著性水平", multilevel.get("alpha")],
            ["模拟次数", multilevel.get("replications")],
            ["随机种子", multilevel.get("seed")],
            ["推荐人数", recommendation.get("personCount")],
            ["推荐每人次数", recommendation.get("observationsPerPerson")],
            ["可用于规划", multilevel.get("validForPlanning")],
            ["失败拟合分母规则", multilevel.get("failureRule")],
            *[[key, value] for key, value in multilevel.get("assumptions", {}).items()],
            [
                "执行来源",
                json.dumps(
                    multilevel.get("provenance", {}),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            ],
        ],
    )
