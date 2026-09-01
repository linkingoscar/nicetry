from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest
from openpyxl import Workbook

from app.api.schemas import DiaryMultilevelInput
from app.services.empirical_advanced_method_export import (
    append_diary_advanced_model_sheets,
)
from app.services.empirical_export import _append_sheet
from app.settings import get_settings


def _contract() -> dict[str, Any]:
    return {
        "subject_variable_id": "person",
        "time_variable_id": "occasion",
        "outcome_variable_id": "y",
        "predictor_variable_id": "x",
    }


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"analysis_type": "lmm", "outcome_family": "binomial"}, "LMM 仅适用于"),
        ({"analysis_type": "glmm"}, "GLMM 必须选择"),
        ({"cluster_structure": "cross_classified"}, "必须指定第二个"),
        (
            {
                "analysis_type": "glmm",
                "outcome_family": "poisson",
                "residual_structure": "ar1",
            },
            "不支持 nlme AR",
        ),
        ({"analysis_type": "bayesian_dsem"}, "必须提供链数"),
        (
            {
                "analysis_type": "glmm",
                "outcome_family": "binomial",
                "count_model": "zero_inflated",
            },
            "仅适用于 Poisson",
        ),
        (
            {
                "analysis_type": "glmm",
                "outcome_family": "poisson",
                "zero_process_predictors": "shared",
            },
            "仅在零膨胀或 Hurdle",
        ),
    ],
)
def test_advanced_diary_contract_rejects_invalid_combinations(
    patch: dict[str, Any],
    message: str,
) -> None:
    payload = _contract()
    payload.update(patch)
    with pytest.raises(ValueError, match=message):
        DiaryMultilevelInput.model_validate(payload)


def _run_r_model(spec: dict[str, Any], generator: str, timeout: int = 90) -> dict[str, Any]:
    settings = get_settings()
    root = settings.project_root
    r_script = f"""
    suppressPackageStartupMessages(library(jsonlite))
    for (path in commandArgs(trailingOnly = TRUE)[1:8]) source(path)
    spec <- fromJSON(commandArgs(trailingOnly = TRUE)[9], simplifyVector = FALSE)
    {generator}
    result <- fit_diary_multilevel(data, spec, function(id) id)
    write_json(result, commandArgs(trailingOnly = TRUE)[10], auto_unbox = TRUE, null = "null")
    """
    with tempfile.TemporaryDirectory(prefix="rp-diary-advanced-") as temporary:
        work = Path(temporary)
        script = work / "run.R"
        specification = work / "spec.json"
        output = work / "result.json"
        script.write_text(r_script, encoding="utf-8")
        specification.write_text(json.dumps(spec), encoding="utf-8")
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(script),
                str(root / "engine/R/lib/longitudinal_panel.R"),
                str(root / "engine/R/lib/diary_esm_evidence.R"),
                str(root / "engine/R/lib/diary_missing.R"),
                str(root / "engine/R/lib/diary_power.R"),
                str(root / "engine/R/lib/diary_glmm.R"),
                str(root / "engine/R/lib/diary_bayesian_diagnostics.R"),
                str(root / "engine/R/lib/diary_bayesian_dsem.R"),
                str(root / "engine/R/lib/diary_multilevel.R"),
                str(specification),
                str(output),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        result = json.loads(output.read_text(encoding="utf-8")) if output.exists() else None
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    return result


def _base_r_spec() -> dict[str, Any]:
    return {
        "subjectVariableId": "person",
        "timeVariableId": "occasion",
        "outcomeVariableId": "purchase",
        "predictorVariableId": "x",
        "mediatorVariableId": None,
        "level2CovariateIds": [],
        "controlVariableIds": [],
        "randomSlope": False,
        "residualStructure": "independent",
        "outcomeFamily": "binomial",
        "countModel": "standard",
        "zeroProcessPredictors": "intercept_only",
        "distributionDiagnosticSimulations": 100,
        "distributionDiagnosticSeed": 20260729,
        "clusterStructure": "cross_classified",
        "crossClassVariableId": "scenario",
        "exposureVariableId": None,
        "centering": "person_mean",
        "mediationType": "1-1-1",
        "temporalEffect": "contemporaneous",
        "lagOrder": 1,
        "expectedTimeInterval": 1,
        "timeIntervalTolerance": 0,
        "includeLinearTime": True,
        "includeQuadraticTime": False,
        "timeOriginStrategy": "first_observed",
        "customTimeOrigin": None,
        "level2ModeratorVariableId": None,
        "expectedObservationsPerPerson": 12,
        "minimumComplianceRate": 0,
        "excludeLowCompliance": False,
        "responseLatencyVariableId": None,
        "excludeOutOfWindow": False,
        "reliabilityConstructs": [],
        "missingStrategy": "complete_cases",
        "runRobustnessChecks": False,
        "powerAnalysis": None,
        "dsem": None,
    }


def test_cross_classified_binomial_glmm_reports_odds_ratios() -> None:
    spec = _base_r_spec()
    spec["analysisType"] = "glmm"
    generator = """
    set.seed(20260728)
    data <- expand.grid(person = paste0("P", 1:40), occasion = 1:12)
    data <- data[order(data$person, data$occasion), ]
    data$scenario <- paste0("S", (as.integer(factor(data$person)) + data$occasion) %% 5 + 1)
    person_effect <- rnorm(40, 0, 0.45)
    scenario_effect <- rnorm(5, 0, 0.3)
    data$x <- rnorm(nrow(data)) + person_effect[as.integer(factor(data$person))]
    eta <- -0.4 + 0.55 * data$x +
      person_effect[as.integer(factor(data$person))] +
      scenario_effect[as.integer(factor(data$scenario))]
    data$purchase <- rbinom(nrow(data), 1, plogis(eta))
    """
    result = _run_r_model(spec, generator)
    assert result["analysisType"] == "glmm"
    assert result["outcomeFamily"] == "binomial"
    assert result["clusterStructure"] == "cross_classified"
    assert result["crossClassCount"] == 5
    assert all(effect["exponentiatedEstimate"] is not None for effect in result["fixedEffects"])


def test_cross_classified_gaussian_model_estimates_person_and_scenario_variance() -> None:
    spec = _base_r_spec()
    spec.update(
        {
            "analysisType": "lmm",
            "outcomeFamily": "gaussian",
            "outcomeVariableId": "y",
        }
    )
    generator = """
    set.seed(20260731)
    data <- expand.grid(person = paste0("P", 1:35), occasion = 1:12)
    data <- data[order(data$person, data$occasion), ]
    data$scenario <- paste0("S", (as.integer(factor(data$person)) + data$occasion) %% 6 + 1)
    person_effect <- rnorm(35, 0, 0.5)
    scenario_effect <- rnorm(6, 0, 0.4)
    data$x <- rnorm(nrow(data))
    data$y <- 0.45 * data$x +
      person_effect[as.integer(factor(data$person))] +
      scenario_effect[as.integer(factor(data$scenario))] +
      rnorm(nrow(data), 0, 0.6)
    """
    result = _run_r_model(spec, generator)
    groups = {component["group"] for component in result["varianceComponents"]}
    assert result["modelLabel"] == "交叉分类线性混合模型"
    assert {"person", "scenario"} <= groups
    assert result["crossClassCount"] == 6


@pytest.mark.serial
@pytest.mark.parametrize("family", ["poisson", "negative_binomial"])
def test_count_glmm_reports_distribution_diagnostics(family: str) -> None:
    spec = _base_r_spec()
    spec.update(
        {
            "analysisType": "glmm",
            "outcomeFamily": family,
            "clusterStructure": "nested",
            "crossClassVariableId": None,
            "outcomeVariableId": "clicks",
        }
    )
    generator = """
    set.seed(20260729)
    data <- expand.grid(person = paste0("P", 1:35), occasion = 1:12)
    data <- data[order(data$person, data$occasion), ]
    person_effect <- rnorm(35, 0, 0.35)
    data$x <- rnorm(nrow(data))
    rate <- exp(0.25 + 0.3 * data$x + person_effect[as.integer(factor(data$person))])
    data$clicks <- if (identical(spec$outcomeFamily, "poisson")) {
      rpois(nrow(data), rate)
    } else {
      rnbinom(nrow(data), mu = rate, size = 2)
    }
    """
    result = _run_r_model(spec, generator)
    assert result["outcomeFamily"] == family
    assert result["distributionDiagnostics"]["pearsonDispersion"] is not None
    assert result["effectScale"] == "incidence rate ratio"


@pytest.mark.serial
@pytest.mark.parametrize(
    ("count_model", "family"),
    [("zero_inflated", "poisson"), ("hurdle", "negative_binomial")],
)
def test_explicit_zero_process_models_report_both_processes_and_comparator(
    count_model: str,
    family: str,
) -> None:
    spec = _base_r_spec()
    spec.update(
        {
            "analysisType": "glmm",
            "outcomeFamily": family,
            "countModel": count_model,
            "clusterStructure": "nested",
            "crossClassVariableId": None,
            "outcomeVariableId": "clicks",
        }
    )
    generator = """
    set.seed(20260802)
    data <- expand.grid(person = paste0("P", 1:45), occasion = 1:16)
    data <- data[order(data$person, data$occasion), ]
    person_effect <- rnorm(45, 0, 0.3)
    data$x <- rnorm(nrow(data))
    rate <- exp(0.2 + 0.25 * data$x + person_effect[as.integer(factor(data$person))])
    structural_zero <- rbinom(nrow(data), 1, 0.32) == 1
    if (identical(spec$countModel, "hurdle")) {
      positive <- 1 + rnbinom(nrow(data), mu = rate, size = 2)
      data$clicks <- ifelse(structural_zero, 0, positive)
    } else {
      count <- rpois(nrow(data), rate)
      data$clicks <- ifelse(structural_zero, 0, count)
    }
    """
    result = _run_r_model(spec, generator)
    assert result["countModel"] == count_model
    assert result["zeroProcessEffects"]
    assert {row["model"] for row in result["countModelComparison"]} == {
        count_model,
        "standard",
    }
    diagnostics = result["distributionDiagnostics"]
    assert diagnostics["simulationCount"] == 100
    assert diagnostics["zeroInflationPValue"] is not None
    assert result["provenance"]["automaticModelSwitching"] is False


def test_bayesian_dsem_returns_bidirectional_posteriors_and_mcmc_diagnostics() -> None:
    spec = _base_r_spec()
    spec.update(
        {
            "analysisType": "bayesian_dsem",
            "outcomeVariableId": "y",
            "outcomeFamily": "gaussian",
            "clusterStructure": "nested",
            "crossClassVariableId": None,
            "temporalEffect": "lagged",
            "expectedObservationsPerPerson": 22,
            "includeLinearTime": False,
            "dsem": {
                "chains": 2,
                "iterations": 500,
                "warmup": 250,
                "thin": 1,
                "priorMeanSd": 1,
                "priorScale": 1,
                "randomDynamicSlopes": True,
                "seed": 20260730,
            },
        }
    )
    generator = """
    set.seed(20260730)
    rows <- list()
    for (person_index in 1:12) {
      x <- y <- numeric(22)
      x[1] <- rnorm(1)
      y[1] <- rnorm(1)
      for (occasion in 2:22) {
        x[occasion] <- 0.35 * x[occasion - 1] + 0.12 * y[occasion - 1] + rnorm(1, 0, 0.6)
        y[occasion] <- 0.4 * y[occasion - 1] + 0.2 * x[occasion - 1] + rnorm(1, 0, 0.6)
      }
      rows[[person_index]] <- data.frame(
        person = paste0("P", person_index),
        occasion = 1:22,
        scenario = "S1",
        x = x + rnorm(1, 0, 0.5),
        y = y + rnorm(1, 0, 0.5)
      )
    }
    data <- do.call(rbind, rows)
    """
    result = _run_r_model(spec, generator, timeout=120)
    effects = {effect["id"]: effect for effect in result["posteriorEffects"]}
    effect_ids = set(effects)
    assert {"y_own_lag", "y_cross_lag", "x_own_lag", "x_cross_lag"} <= effect_ids
    # Parameter-recovery evidence for the deterministic synthetic VAR(1)
    # generator. These bounds are intentionally broad enough for a short
    # two-chain CI test while still catching sign swaps or a broken lag design.
    expected = {
        "y_own_lag": 0.40,
        "y_cross_lag": 0.20,
        "x_own_lag": 0.35,
        "x_cross_lag": 0.12,
    }
    for effect_id, population_value in expected.items():
        estimate = effects[effect_id]["estimate"]
        assert estimate is not None
        assert estimate > 0
        assert abs(estimate - population_value) < 0.25
    assert result["mcmcDiagnostics"]["chains"] == 2
    assert result["mcmcDiagnostics"]["retainedPerChain"] == 250
    assert isinstance(result["validForInterpretation"], bool)
    assert result["provenance"]["commercialSoftwareRequired"] is False
    assert "rank-normalized" in result["mcmcDiagnostics"]["diagnosticMethod"]
    assert result["mcmcDiagnostics"]["minimumBulkEffectiveSampleSize"] is not None
    assert result["mcmcDiagnostics"]["minimumTailEffectiveSampleSize"] is not None
    assert len(result["posteriorDraws"]) == 4
    assert result["posteriorPredictive"]["checks"]
    assert result["priorPredictive"]["checks"]
    assert len(result["priorSensitivity"]["scenarios"]) == 2


def test_advanced_diary_evidence_exports_to_dedicated_sheets() -> None:
    workbook = Workbook()
    active_sheet = workbook.active
    if active_sheet is not None:
        workbook.remove(active_sheet)
    append_diary_advanced_model_sheets(
        workbook,
        {
            "outcomeFamily": "poisson",
            "countModel": "zero_inflated",
            "methodNotice": "零过程与计数过程分别解释。",
            "zeroProcessEffects": [{"label": "截距", "estimate": -0.5}],
            "countModelComparison": [{"model": "zero_inflated", "aic": 120}],
            "distributionDiagnostics": {
                "pearsonDispersion": 1.1,
                "simulationCount": 250,
            },
        },
        _append_sheet,
    )
    append_diary_advanced_model_sheets(
        workbook,
        {
            "posteriorEffects": [{"id": "y_cross_lag", "estimate": 0.2}],
            "methodNotice": "观测变量动态关联，不作因果声明。",
            "mcmcDiagnostics": {"stationarity": {}, "diagnosticMethod": "rank-normalized"},
            "posteriorPredictive": {
                "checks": [{"equation": "Y", "statistic": "mean"}],
            },
            "priorPredictive": {
                "checks": [{"equation": "Y", "statistic": "mean"}],
            },
            "priorSensitivity": {
                "scenarios": [
                    {
                        "scenario": "wider",
                        "effects": [{"id": "y_cross_lag"}],
                    }
                ]
            },
            "posteriorDraws": [
                {
                    "id": "y_cross_lag",
                    "label": "X→Y",
                    "chains": [
                        {
                            "chain": 1,
                            "iterations": [1, 2, 3],
                            "values": [0.1, 0.2, 0.3],
                        },
                        {
                            "chain": 2,
                            "iterations": [1, 2, 3],
                            "values": [0.15, 0.22, 0.28],
                        },
                    ],
                }
            ],
        },
        _append_sheet,
    )
    assert {
        "ESM-GLMM分布诊断",
        "ESM-GLMM零过程",
        "ESM-GLMM模型比较",
        "模型身份与解释边界",
        "Bayesian-DSEM后验",
        "Bayesian-DSEM诊断",
        "Bayesian-DSEM预测检验",
        "Bayesian-DSEM先验敏感性",
        "Bayesian-DSEM绘图数据",
        "Bayesian-DSEM附录图",
    } <= set(workbook.sheetnames)
