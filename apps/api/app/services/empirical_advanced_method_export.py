from __future__ import annotations

from typing import Any

from openpyxl import Workbook

from app.services.empirical_bayesian_figure_export import append_dsem_plot_sheets
from app.services.empirical_export_sections import AppendSheet


def append_lcm_sr_growth_sheet(
    workbook: Workbook,
    panel: dict[str, Any],
    append_sheet: AppendSheet,
) -> None:
    growth = panel.get("growthModel")
    if not growth:
        return
    append_sheet(
        workbook,
        "LCM-SR生长成分",
        [
            [
                "轨迹形式",
                "时间原点",
                "时间载荷",
                "成分",
                "参数",
                "相关成分",
                "估计",
                "标准化估计",
                "SE",
                "p",
                "CI下限",
                "CI上限",
            ]
        ]
        + [
            [
                growth.get("growthShape"),
                growth.get("timeOrigin"),
                ", ".join(str(value) for value in growth.get("timeLoadings", [])),
                row.get("lhs"),
                row.get("operator"),
                row.get("rhs"),
                row.get("estimate"),
                row.get("standardizedEstimate"),
                row.get("standardError"),
                row.get("pValue"),
                row.get("lower"),
                row.get("upper"),
            ]
            for row in growth.get("components", [])
        ],
    )


def append_longitudinal_cmb_sheets(
    workbook: Workbook,
    panel: dict[str, Any],
    append_sheet: AppendSheet,
) -> None:
    cmb = panel.get("cmbSensitivity")
    if not cmb:
        return
    identification = cmb.get("identification") or {}
    append_sheet(
        workbook,
        "纵向CMB识别诊断",
        [
            [
                "可估计",
                "可解释",
                "方法",
                "正交",
                "标记题项",
                "题项数",
                "平均标准化方法方差",
                "收敛",
                "后估计检查",
                "负方差数",
                "潜变量协方差最小特征值",
                "信息矩阵最小特征值比",
                "信息矩阵满秩",
                "推断改变路径数",
            ],
            [
                cmb.get("available"),
                cmb.get("validForInterpretation"),
                cmb.get("method"),
                cmb.get("orthogonalToSubstantiveFactors"),
                cmb.get("markerItemId"),
                cmb.get("indicatorCount"),
                cmb.get("averageStandardizedVarianceShare"),
                identification.get("converged"),
                identification.get("postCheckPassed"),
                identification.get("negativeVarianceCount"),
                identification.get("latentCovarianceMinimumEigenvalue"),
                identification.get("informationMinimumEigenvalueRatio"),
                identification.get("informationFullRank"),
                cmb.get("changedInferenceCount"),
            ],
        ],
    )
    if cmb.get("pathChanges"):
        append_sheet(
            workbook,
            "纵向CMB路径敏感性",
            [
                [
                    "路径",
                    "类型",
                    "方向",
                    "起始波次",
                    "结果波次",
                    "基准B",
                    "ULMC B",
                    "绝对变化",
                    "相对变化",
                    "基准p",
                    "ULMC p",
                    "符号改变",
                    "推断改变",
                ]
            ]
            + [
                [
                    row.get("id"),
                    row.get("pathType"),
                    row.get("direction"),
                    row.get("fromWave"),
                    row.get("toWave"),
                    row.get("baselineEstimate"),
                    row.get("adjustedEstimate"),
                    row.get("absoluteChange"),
                    row.get("relativeChange"),
                    row.get("baselinePValue"),
                    row.get("adjustedPValue"),
                    row.get("signChanged"),
                    row.get("inferenceChanged"),
                ]
                for row in cmb.get("pathChanges", [])
            ],
        )


def append_diary_protocol_sheets(
    workbook: Workbook,
    diary: dict[str, Any],
    append_sheet: AppendSheet,
) -> None:
    centering = diary.get("centeringProtocol")
    if centering:
        level1 = centering.get("level1Predictor", {})
        level2 = centering.get("level2Moderator") or {}
        time = centering.get("time", {})
        append_sheet(
            workbook,
            "ESM中心化协议",
            [
                [
                    "Level-1策略",
                    "组内公式",
                    "被试间公式",
                    "个人均值重入",
                    "被试间权重",
                    "Level-1参照",
                    "Level-2策略",
                    "Level-2公式",
                    "Level-2参照",
                    "时间原点策略",
                    "时间原点",
                    "解释",
                ],
                [
                    level1.get("strategy"),
                    level1.get("level1Formula"),
                    level1.get("level2Formula"),
                    level1.get("personMeanReintroduced"),
                    level1.get("grandMeanWeighting"),
                    level1.get("level1Reference"),
                    level2.get("strategy"),
                    level2.get("formula"),
                    level2.get("reference"),
                    time.get("originStrategy"),
                    time.get("originValue"),
                    centering.get("interpretation"),
                ],
            ],
        )
    trend = diary.get("timeTrendTest")
    if not trend:
        return
    append_sheet(
        workbook,
        "ESM时间趋势",
        [
            [
                "检验",
                "项",
                "χ²",
                "df",
                "p",
                "原点策略",
                "原点",
                "原点处线性斜率",
                "二次项",
                "转折点",
                "转折点在样本范围",
            ],
            [
                trend.get("method"),
                ", ".join(trend.get("terms", [])),
                trend.get("statistic"),
                trend.get("degreesOfFreedom"),
                trend.get("pValue"),
                trend.get("originStrategy"),
                trend.get("originValue"),
                trend.get("linearSlopeAtOrigin"),
                trend.get("quadraticCoefficient"),
                trend.get("turningPoint"),
                trend.get("turningPointInObservedRange"),
            ],
        ],
    )


def append_diary_advanced_model_sheets(
    workbook: Workbook,
    diary: dict[str, Any],
    append_sheet: AppendSheet,
) -> None:
    distribution = diary.get("distributionDiagnostics")
    if distribution:
        append_sheet(
            workbook,
            "ESM-GLMM分布诊断",
            [
                [
                    "结局族",
                    "计数模型",
                    "链接函数",
                    "效应尺度",
                    "聚类结构",
                    "交叉分类单元数",
                    "Pearson离散比",
                    "观测零比例",
                    "预期零比例",
                    "零比例差",
                    "模拟次数",
                    "模拟离散比",
                    "过度离散模拟p",
                    "过多零值模拟p",
                    "诊断方法",
                    "可解释",
                ],
                [
                    diary.get("outcomeFamily"),
                    diary.get("countModel"),
                    diary.get("linkFunction"),
                    diary.get("effectScale"),
                    diary.get("clusterStructure"),
                    diary.get("crossClassCount"),
                    distribution.get("pearsonDispersion"),
                    distribution.get("observedZeroRate"),
                    distribution.get("expectedZeroRate"),
                    distribution.get("zeroRateDifference"),
                    distribution.get("simulationCount"),
                    distribution.get("dispersionRatio"),
                    distribution.get("dispersionPValue"),
                    distribution.get("zeroInflationPValue"),
                    distribution.get("diagnosticMethod"),
                    diary.get("validForInterpretation"),
                ],
            ],
        )
        if diary.get("zeroProcessEffects"):
            append_sheet(
                workbook,
                "ESM-GLMM零过程",
                [["变量", "log-odds", "SE", "z", "p", "CI下限", "CI上限", "OR", "OR下限", "OR上限"]]
                + [
                    [
                        row.get("label"),
                        row.get("estimate"),
                        row.get("standardError"),
                        row.get("statistic"),
                        row.get("pValue"),
                        row.get("lower"),
                        row.get("upper"),
                        row.get("exponentiatedEstimate"),
                        row.get("exponentiatedLower"),
                        row.get("exponentiatedUpper"),
                    ]
                    for row in diary.get("zeroProcessEffects", [])
                ],
            )
        if diary.get("countModelComparison"):
            append_sheet(
                workbook,
                "ESM-GLMM模型比较",
                [["模型ID", "模型", "AIC", "BIC", "logLik", "参数数", "收敛"]]
                + [
                    [
                        row.get("model"),
                        row.get("label"),
                        row.get("aic"),
                        row.get("bic"),
                        row.get("logLikelihood"),
                        row.get("parameterCount"),
                        row.get("converged"),
                    ]
                    for row in diary.get("countModelComparison", [])
                ],
            )
    if diary.get("methodNotice"):
        provenance = diary.get("provenance") or {}
        append_sheet(
            workbook,
            "模型身份与解释边界",
            [
                ["项目", "内容"],
                ["模型身份", diary.get("modelLabel")],
                ["适用范围与识别边界", diary.get("methodNotice")],
                ["估计引擎", provenance.get("engine")],
                ["估计方法", provenance.get("estimator")],
                ["自动模型切换", provenance.get("automaticModelSwitching")],
                ["方法引用", provenance.get("reference")],
            ],
        )
    posterior = diary.get("posteriorEffects")
    if not posterior:
        return
    append_sheet(
        workbook,
        "Bayesian-DSEM后验",
        [
            [
                "参数",
                "标签",
                "后验均值",
                "后验SD",
                "CrI下限",
                "CrI上限",
                "Pr(θ>0)",
                "R-hat",
                "ESS",
                "bulk ESS",
                "tail ESS",
                "MCSE(mean)",
            ]
        ]
        + [
            [
                row.get("id"),
                row.get("label"),
                row.get("estimate"),
                row.get("posteriorSd"),
                row.get("lower"),
                row.get("upper"),
                row.get("probabilityPositive"),
                row.get("rHat"),
                row.get("effectiveSampleSize"),
                row.get("bulkEffectiveSampleSize"),
                row.get("tailEffectiveSampleSize"),
                row.get("mcseMean"),
            ]
            for row in posterior
        ],
    )
    mcmc = diary.get("mcmcDiagnostics") or {}
    predictive = diary.get("posteriorPredictive") or {}
    append_sheet(
        workbook,
        "Bayesian-DSEM诊断",
        [
            [
                "链数",
                "每链迭代",
                "每链Warmup",
                "Thin",
                "每链保留",
                "最大R-hat",
                "最小ESS",
                "最小bulk ESS",
                "最小tail ESS",
                "ESS门槛",
                "诊断方法",
                "Y自回归平稳",
                "X自回归平稳",
                "Y Bayesian R²",
                "X Bayesian R²",
                "可解释",
            ],
            [
                mcmc.get("chains"),
                mcmc.get("iterationsPerChain"),
                mcmc.get("warmupPerChain"),
                mcmc.get("thin"),
                mcmc.get("retainedPerChain"),
                mcmc.get("maximumRHat"),
                mcmc.get("minimumEffectiveSampleSize"),
                mcmc.get("minimumBulkEffectiveSampleSize"),
                mcmc.get("minimumTailEffectiveSampleSize"),
                mcmc.get("effectiveSampleSizeThreshold"),
                mcmc.get("diagnosticMethod"),
                (mcmc.get("stationarity") or {}).get(
                    "yAutoregressiveWithinUnitInterval"
                ),
                (mcmc.get("stationarity") or {}).get(
                    "xAutoregressiveWithinUnitInterval"
                ),
                predictive.get("yBayesianRSquared"),
                predictive.get("xBayesianRSquared"),
                diary.get("validForInterpretation"),
            ],
        ],
    )
    posterior_predictive = (diary.get("posteriorPredictive") or {}).get("checks", [])
    prior_predictive = (diary.get("priorPredictive") or {}).get("checks", [])
    if posterior_predictive or prior_predictive:
        append_sheet(
            workbook,
            "Bayesian-DSEM预测检验",
            [["类型", "方程", "统计量", "观测", "复制中位数", "复制下限", "复制上限", "Bayesian p", "观测在区间内"]]
            + [
                [
                    "posterior",
                    row.get("equation"),
                    row.get("statistic"),
                    row.get("observed"),
                    row.get("replicatedMedian"),
                    row.get("replicatedLower"),
                    row.get("replicatedUpper"),
                    row.get("bayesianPValue"),
                    None,
                ]
                for row in posterior_predictive
            ]
            + [
                [
                    "prior",
                    row.get("equation"),
                    row.get("statistic"),
                    row.get("observed"),
                    row.get("replicatedMedian"),
                    row.get("replicatedLower"),
                    row.get("replicatedUpper"),
                    None,
                    row.get("observedWithinInterval"),
                ]
                for row in prior_predictive
            ],
        )
    sensitivity = diary.get("priorSensitivity") or {}
    if sensitivity.get("scenarios"):
        append_sheet(
            workbook,
            "Bayesian-DSEM先验敏感性",
            [["情景", "固定效应先验SD", "重加权ESS", "参数", "估计", "CI下限", "CI上限", "相对基准变化", "推断变化"]]
            + [
                [
                    scenario.get("scenario"),
                    scenario.get("priorMeanSd"),
                    scenario.get("reweightingEffectiveSampleSize"),
                    effect.get("id"),
                    effect.get("estimate"),
                    effect.get("lower"),
                    effect.get("upper"),
                    effect.get("absoluteChange"),
                    effect.get("inferenceChanged"),
                ]
                for scenario in sensitivity.get("scenarios", [])
                for effect in scenario.get("effects", [])
            ],
        )
    append_dsem_plot_sheets(workbook, diary.get("posteriorDraws", []))
