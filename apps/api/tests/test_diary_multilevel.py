from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest
from openpyxl import Workbook

from app.api.schemas import DiaryMultilevelInput, DiaryPowerInput, EmpiricalAnalysisRequest
from app.services.empirical_export import _append_sheet
from app.services.empirical_longitudinal_export import append_longitudinal_method_sections
from app.settings import get_settings


def _diary_spec(
    *,
    analysis_type: str = "lmm",
    residual_structure: str = "independent",
    mediation_type: str = "1-1-1",
) -> dict[str, Any]:
    return {
        "analysisType": analysis_type,
        "subjectVariableId": "person_id",
        "timeVariableId": "day",
        "outcomeVariableId": "daily_engagement",
        "predictorVariableId": "daily_stress",
        "mediatorVariableId": "daily_recovery" if analysis_type == "mediation" else None,
        "level2CovariateIds": ["intervention"],
        "controlVariableIds": [],
        "randomSlope": True,
        "residualStructure": residual_structure,
        "centering": "person_mean" if mediation_type == "1-1-1" else "none",
        "mediationType": mediation_type,
        "temporalEffect": "contemporaneous",
        "lagOrder": 1,
        "expectedTimeInterval": 1,
        "timeIntervalTolerance": 0,
        "includeLinearTime": True,
        "includeQuadraticTime": False,
        "timeOriginStrategy": "sample_mean",
        "customTimeOrigin": None,
        "level2ModeratorVariableId": None,
        "expectedObservationsPerPerson": 10,
        "minimumComplianceRate": 0.8,
        "excludeLowCompliance": False,
        "responseLatencyVariableId": None,
        "minimumResponseLatency": None,
        "maximumResponseLatency": None,
        "excludeOutOfWindow": False,
        "reliabilityConstructs": [],
        "missingStrategy": "complete_cases",
        "imputationCount": 5,
        "imputationIterations": 5,
    }


def _run_diary_slice(spec: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    root = settings.project_root
    r_script = """
    suppressPackageStartupMessages(library(jsonlite))
    source(commandArgs(trailingOnly = TRUE)[1])
    source(commandArgs(trailingOnly = TRUE)[2])
    source(commandArgs(trailingOnly = TRUE)[3])
    source(commandArgs(trailingOnly = TRUE)[4])
    input <- fromJSON(commandArgs(trailingOnly = TRUE)[5], simplifyVector = FALSE)
    data <- read.csv(commandArgs(trailingOnly = TRUE)[6], check.names = FALSE)
    if (identical(input$missingStrategy, "multilevel_mi")) {
      data$daily_stress[seq(5, nrow(data), by = 17)] <- NA
      data$daily_engagement[seq(9, nrow(data), by = 19)] <- NA
    }
    result <- fit_diary_multilevel(data, input, function(id) id)
    write_json(result, commandArgs(trailingOnly = TRUE)[7], auto_unbox = TRUE, null = "null")
    """
    with tempfile.TemporaryDirectory(prefix="rp-diary-test-") as temporary:
        work = Path(temporary)
        script_path = work / "run.R"
        spec_path = work / "spec.json"
        output_path = work / "output.json"
        script_path.write_text(r_script, encoding="utf-8")
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(script_path),
                str(root / "engine/R/lib/longitudinal_panel.R"),
                str(root / "engine/R/lib/diary_esm_evidence.R"),
                str(root / "engine/R/lib/diary_missing.R"),
                str(root / "engine/R/lib/diary_multilevel.R"),
                str(spec_path),
                str(root / "samples/data/daily-diary-demo.csv"),
                str(output_path),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=90,
        )
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else None
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    return result


def test_diary_contract_requires_distinct_roles() -> None:
    with pytest.raises(ValueError, match="必须不同"):
        EmpiricalAnalysisRequest.model_validate(
            {
                "diary_multilevel": {
                    "subject_variable_id": "person_id",
                    "time_variable_id": "day",
                    "outcome_variable_id": "daily_engagement",
                    "predictor_variable_id": "daily_engagement",
                }
            }
        )


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"person_counts": [20, 20]}, "候选人数不得重复"),
        ({"observations_per_person": [5, 5]}, "候选测量次数不得重复"),
        ({"person_counts": [40, 20]}, "候选人数必须升序"),
        ({"observations_per_person": [7, 3]}, "候选测量次数必须升序"),
        ({"person_counts": [19]}, "20–5000"),
        ({"observations_per_person": [2]}, "至少需要三个"),
        (
            {
                "person_counts": list(range(20, 180, 20)),
                "observations_per_person": list(range(3, 11)),
                "replications": 100,
            },
            "最多运行 5000",
        ),
    ],
)
def test_diary_power_contract_rejects_invalid_designs(
    patch: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        DiaryPowerInput.model_validate(patch)


def _diary_contract_payload() -> dict[str, object]:
    return {
        "subject_variable_id": "person",
        "time_variable_id": "day",
        "outcome_variable_id": "y",
        "predictor_variable_id": "x",
    }


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"analysis_type": "mediation"}, "必须指定中介"),
        (
            {"analysis_type": "mediation", "mediator_variable_id": "x"},
            "中介变量不能",
        ),
        (
            {
                "analysis_type": "mediation",
                "mediator_variable_id": "m",
                "temporal_effect": "both",
            },
            "不能在同一模型混合",
        ),
        ({"mediation_type": "2-1-1"}, "不能进行 person-mean"),
        (
            {"level2_covariate_ids": ["z"], "control_variable_ids": ["z"]},
            "协变量不得重复",
        ),
        ({"control_variable_ids": ["x"]}, "协变量与核心角色重复"),
        ({"level2_moderator_variable_id": "y"}, "跨层调节变量不能"),
        (
            {
                "level2_moderator_variable_id": "z",
                "level2_covariate_ids": ["z"],
            },
            "不应同时作为普通协变量",
        ),
        ({"exclude_low_compliance": True, "minimum_compliance_rate": 0.8}, "预期观测次数"),
        (
            {
                "exclude_low_compliance": True,
                "expected_observations_per_person": 10,
            },
            "最低依从率",
        ),
        (
            {"minimum_response_latency": 10, "maximum_response_latency": 5},
            "下限必须小于上限",
        ),
        ({"exclude_out_of_window": True}, "必须指定响应延迟"),
        (
            {
                "analysis_type": "mediation",
                "mediator_variable_id": "m",
                "missing_strategy": "multilevel_mi",
            },
            "二层多重插补",
        ),
        (
            {
                "analysis_type": "mediation",
                "mediator_variable_id": "m",
                "power_analysis": {"person_counts": [20], "observations_per_person": [5]},
            },
            "功效分析针对二层线性混合模型",
        ),
        (
            {
                "reliability_constructs": [
                    {"label": "a", "item_ids": ["i1", "i2"]},
                    {"label": "b", "item_ids": ["i2", "i3"]},
                ]
            },
            "不能重复使用题项",
        ),
    ],
)
def test_diary_contract_rejects_invalid_method_combinations(
    patch: dict[str, object],
    message: str,
) -> None:
    payload = _diary_contract_payload()
    payload.update(patch)
    with pytest.raises(ValueError, match=message):
        DiaryMultilevelInput.model_validate(payload)


@pytest.mark.parametrize("temporal_effect", ["contemporaneous", "lagged"])
def test_diary_monte_carlo_power_returns_person_occasion_grid(
    temporal_effect: str,
) -> None:
    settings = get_settings()
    root = settings.project_root
    spec = _diary_spec()
    spec["randomSlope"] = False
    spec["temporalEffect"] = temporal_effect
    spec["powerAnalysis"] = {
        "personCounts": [20],
        "observationsPerPerson": [5],
        "replications": 20,
        "targetPower": 0.8,
        "alpha": 0.05,
        "withinEffect": 0.3,
        "betweenEffect": 0.2,
        "randomInterceptSd": 0.5,
        "randomSlopeSd": 0.1,
        "residualSd": 1.0,
        "predictorBetweenSd": 0.7,
        "predictorWithinSd": 1.0,
        "residualAr1": 0.2,
        "seed": 20260714,
    }
    r_script = """
    suppressPackageStartupMessages(library(jsonlite))
    source(commandArgs(trailingOnly = TRUE)[1])
    input <- fromJSON(commandArgs(trailingOnly = TRUE)[2], simplifyVector = FALSE)
    result <- diary_power_analysis(input)
    write_json(result, commandArgs(trailingOnly = TRUE)[3], auto_unbox = TRUE, null = "null")
    """
    with tempfile.TemporaryDirectory(prefix="rp-diary-power-test-") as temporary:
        work = Path(temporary)
        script_path = work / "run.R"
        spec_path = work / "spec.json"
        output_path = work / "output.json"
        script_path.write_text(r_script, encoding="utf-8")
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(script_path),
                str(root / "engine/R/lib/diary_power.R"),
                str(spec_path),
                str(output_path),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=90,
        )
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else None
        )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    assert result["provenance"]["engine"] == "R lme4 + lmerTest Monte Carlo"
    assert temporal_effect in result["targetParameter"]
    assert len(result["results"]) == 1
    assert result["results"][0]["personCount"] == 20
    assert result["results"][0]["observationsPerPerson"] == 5
    assert 0 <= result["results"][0]["power"] <= 1


def test_diary_random_slope_lmm_decomposes_within_and_between_effects() -> None:
    result = _run_diary_slice(_diary_spec())
    assert result["analysisType"] == "lmm"
    assert result["sampleSize"] == 800
    assert result["personCount"] == 80
    assert result["withinPredictorId"] == "daily_stress__within"
    assert result["betweenPredictorId"] == "daily_stress__between"
    assert result["fixedEffects"]
    assert result["residualStructure"] == "independent"


def test_diary_lmm_supports_ar1_residual_structure() -> None:
    result = _run_diary_slice(_diary_spec(residual_structure="ar1"))
    assert result["analysisType"] == "lmm"
    assert result["residualStructure"] == "ar1"
    assert result["ar1"] is not None
    assert -1 < result["ar1"] < 1


def test_diary_quadratic_time_reports_joint_test_and_turning_point() -> None:
    spec = _diary_spec()
    spec["includeQuadraticTime"] = True
    spec["timeOriginStrategy"] = "first_observed"
    result = _run_diary_slice(spec)
    assert result["timeTrendTest"]["degreesOfFreedom"] == 2
    assert result["timeTrendTest"]["originValue"] == 1
    assert result["timeTrendTest"]["quadraticCoefficient"] is not None


def test_diary_lagged_lmm_respects_person_boundaries_and_time_interval() -> None:
    spec = _diary_spec()
    spec["temporalEffect"] = "lagged"
    result = _run_diary_slice(spec)
    assert result["temporalEffect"] == "lagged"
    assert result["laggedPredictorId"] == "daily_stress__within__lag1"
    assert result["sampleSize"] == 720
    assert any(effect["term"] == "daily_stress__within__lag1" for effect in result["fixedEffects"])


def test_diary_cross_level_moderation_quality_and_multilevel_reliability() -> None:
    spec = _diary_spec()
    spec["level2CovariateIds"] = []
    spec["level2ModeratorVariableId"] = "intervention"
    spec["reliabilityConstructs"] = [
        {"label": "日压力", "itemIds": ["stress_i1", "stress_i2"]},
        {"label": "日投入", "itemIds": ["engagement_i1", "engagement_i2"]},
    ]
    result = _run_diary_slice(spec)
    assert result["dataQuality"]["overallComplianceRate"] == pytest.approx(1.0)
    assert result["crossLevelInteractionIds"]
    assert len(result["multilevelReliability"]) == 2
    assert all(
        reliability["withinAlpha"] is not None and reliability["betweenAlpha"] is not None
        for reliability in result["multilevelReliability"]
    )


def test_diary_automatic_robustness_matrix_compares_random_and_residual_structures() -> None:
    spec = _diary_spec()
    spec["runRobustnessChecks"] = True
    result = _run_diary_slice(spec)
    assert {row["scenario"] for row in result["robustnessChecks"]} == {
        "主模型",
        "切换随机斜率结构",
        "切换残差相关结构",
    }


def test_diary_multilevel_multiple_imputation_pools_fixed_effects() -> None:
    spec = _diary_spec()
    spec["missingStrategy"] = "multilevel_mi"
    spec["runRobustnessChecks"] = False
    result = _run_diary_slice(spec)
    assert result["missingData"]["strategy"] == "multilevel_mi"
    assert result["missingData"]["imputationCount"] == 5
    assert result["missingData"]["loggedEventCount"] >= 0
    assert all(0 <= effect["fractionMissingInformation"] <= 1 for effect in result["fixedEffects"])


def test_diary_multilevel_mediation_separates_within_and_between_indirect_effects() -> None:
    result = _run_diary_slice(_diary_spec(analysis_type="mediation"))
    assert result["analysisType"] == "mediation"
    assert result["mediationType"] == "1-1-1"
    effect_ids = {effect["id"] for effect in result["indirectEffects"]}
    assert effect_ids == {"indirect_within", "indirect_between"}
    assert result["paths"]


def test_diary_2_1_1_mediation_uses_person_level_predictor() -> None:
    spec = _diary_spec(analysis_type="mediation", mediation_type="2-1-1")
    spec["predictorVariableId"] = "intervention"
    spec["level2CovariateIds"] = ["age"]
    result = _run_diary_slice(spec)
    assert result["mediationType"] == "2-1-1"
    assert {effect["id"] for effect in result["indirectEffects"]} == {"indirect_between"}


    workbook = Workbook()
    active_sheet = workbook.active
    if active_sheet is not None:
        workbook.remove(active_sheet)
    report = {
        "longitudinalPanel": {
            "modelLabel": "RI-CLPM",
            "sampleSize": 180,
            "waveCount": 3,
            "fitIndices": {},
            "paths": [{"pathType": "cross_lagged", "direction": "X→Y"}],
            "waveSampleFlow": [{"label": "T1", "observed": 180}],
            "measurementInvariance": {
                "models": [{"level": "configural", "fitIndices": {}}],
                "comparisons": [{"from": "configural", "to": "metric"}],
            },
            "competingModels": [{"modelLabel": "潜变量 RI-CLPM", "fitIndices": {}}],
            "powerAnalysis": {
                "method": "Monte Carlo RI-CLPM power analysis",
                "targetPower": 0.8,
                "alpha": 0.05,
                "replications": 500,
                "seed": 1,
                "recommendedSampleSize": 300,
                "validForPlanning": True,
                "assumptions": {"icc": 0.4},
                "results": [
                    {
                        "sampleSize": 300,
                        "directionLabel": "X→Y",
                        "power": 0.82,
                    }
                ],
            },
        },
        "diaryMultilevel": {
            "modelLabel": "1-1-1 多层中介",
            "analysisType": "mediation",
            "sampleSize": 800,
            "personCount": 80,
            "centeringProtocol": {"level1Predictor": {}, "time": {}},
            "timeTrendTest": {"terms": []},
            "indirectEffects": [{"id": "indirect_within", "estimate": -0.1}],
            "powerAnalysis": {
                "method": "Monte Carlo multilevel power analysis",
                "targetParameter": "within-person effect",
                "targetPower": 0.8,
                "alpha": 0.05,
                "replications": 500,
                "seed": 1,
                "validForPlanning": True,
                "assumptions": {"withinEffect": 0.15},
                "recommendation": {
                    "personCount": 80,
                    "observationsPerPerson": 10,
                },
                "results": [
                    {
                        "personCount": 80,
                        "observationsPerPerson": 10,
                        "power": 0.84,
                    }
                ],
            },
        },
    }

    append_longitudinal_method_sections(workbook, report, _append_sheet)

    assert {
        "纵向模型拟合",
        "纵向路径",
        "纵向样本流",
        "纵向测量等值性",
        "纵向等值性比较",
        "纵向竞争模型",
        "纵向功效模拟",
        "纵向功效设计依据",
        "多层模型摘要",
        "多层中介",
        "ESM中心化协议",
        "ESM时间趋势",
        "ESM功效模拟",
        "ESM功效设计依据",
    } <= set(workbook.sheetnames)
