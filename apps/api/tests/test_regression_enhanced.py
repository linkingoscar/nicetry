from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.settings import get_settings


def test_regression_hc3_and_logistic_and_partial_cor() -> None:
    settings = get_settings()
    root = settings.project_root

    # Test correlation CI & partial correlation via R helper
    r_script = """
    args <- commandArgs(trailingOnly = TRUE)
    script_dir <- args[1]
    source(file.path(script_dir, "lib", "runtime.R"))
    source(file.path(script_dir, "lib", "validity.R"))
    source(file.path(script_dir, "lib", "inference_covariance.R"))
    source(file.path(script_dir, "lib", "marginal_effects.R"))
    source(file.path(script_dir, "lib", "regression_reporting.R"))

    set.seed(20260714)
    n <- 100
    x <- rnorm(n)
    z <- rnorm(n)
    y <- 0.5 * x + 0.3 * z + rnorm(n)
    y_bin <- as.numeric(y > 0)
    treatment <- rep(c(0, 1), length.out = n)
    group <- factor(rep(c("A", "B", "C", "A"), length.out = n), levels = c("A", "B", "C"))
    df <- data.frame(x = x, y = y, z = z, y_bin = y_bin, treatment = treatment, group = group)

    cor_res <- calc_correlation_matrix_with_ci(df[, c("x", "y", "z")])
    part_res <- calc_partial_correlation(df, "x", "y", "z")

    fit_lm <- lm(y ~ x + z, data = df)
    hc3_info <- researchpath_hc3_covariance(fit_lm)
    coef_hc3 <- coefficient_rows(fit_lm, function(k) k, robust_se = "HC3", confidence_level = 0.90, robust_covariance = hc3_info$covariance)
    sandwich_reference <- sandwich::vcovHC(fit_lm, type = "HC3")
    high_leverage_fit <- lm(c(1, 2, 8) ~ c(0, 0, 1))
    high_leverage_hc3 <- researchpath_hc3_covariance(high_leverage_fit)

    fit_log <- fit_binary_logistic_with_ame(df, y_bin ~ x + treatment + group, function(k) k, confidence_level = 0.90)
    fit_interaction <- fit_binary_logistic_with_ame(df, y_bin ~ x + z + x:z, function(k) k, confidence_level = 0.90)
    fit_factor_interaction <- fit_binary_logistic_with_ame(df, y_bin ~ x * group, function(k) k, confidence_level = 0.90)

    res <- list(
      cor = cor_res,
      part = part_res,
      hc3 = coef_hc3,
      hc3MaxDifference = max(abs(hc3_info$covariance - sandwich_reference)),
      hc3Execution = hc3_info,
      highLeverageHc3 = high_leverage_hc3,
      logistic = fit_log,
      logisticInteraction = fit_interaction,
      logisticFactorInteraction = fit_factor_interaction
    )
    cat(jsonlite::toJSON(res, auto_unbox = TRUE, digits = 8, na = "null"))
    """

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_reg.R"
        script_file.write_text(r_script, encoding="utf-8")

        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [str(settings.rscript_path), "--vanilla", str(script_file), str(root / "engine/R")],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        output = json.loads(completed.stdout)

    # Validate correlation CIs
    assert "ciLower" in output["cor"]
    assert "ciUpper" in output["cor"]

    # Validate partial correlation
    assert output["part"]["available"] is True
    assert "estimate" in output["part"]
    assert "ciLower" in output["part"]

    # Validate HC3 robust standard errors
    assert len(output["hc3"]) == 3
    for coef in output["hc3"]:
        assert "standardError" in coef
        assert "pValue" in coef
        assert coef["upper"] - coef["lower"] > 0
    assert output["hc3MaxDifference"] < 1e-10
    assert output["hc3Execution"]["executedStandardErrorMethod"] == "HC3"
    assert output["hc3Execution"]["executedMethod"] == "HC3"
    assert output["hc3Execution"]["available"] is True
    assert output["hc3Execution"]["fallbackApplied"] is False
    assert output["highLeverageHc3"]["fallbackApplied"] is False
    assert output["highLeverageHc3"]["executedMethod"] == "not_run"
    assert output["highLeverageHc3"]["available"] is False
    assert "LEVERAGE" in output["highLeverageHc3"]["fallbackReason"]

    # Validate binary logistic regression & AME
    log = output["logistic"]
    assert log["available"] is True
    assert "mcfaddenRSquared" in log
    assert len(log["coefficients"]) == 5
    x_coef = next(c for c in log["coefficients"] if c["term"] == "x")
    assert "oddsRatio" in x_coef
    assert "averageMarginalEffect" in x_coef
    assert x_coef["marginalEffectType"] == "continuous_derivative"
    assert x_coef["confidenceLevel"] == 0.9
    treatment_coef = next(c for c in log["coefficients"] if c["term"] == "treatment")
    assert treatment_coef["marginalEffectType"] == "discrete"
    assert treatment_coef["marginalEffectReferenceLevel"] == "0"
    assert treatment_coef["marginalEffectContrastLevel"] == "1"
    group_coefficients = [c for c in log["coefficients"] if c["term"] in {"groupB", "groupC"}]
    assert len(group_coefficients) == 2
    assert all(c["marginalEffectType"] == "categorical_contrast" for c in group_coefficients)
    assert {c["marginalEffectReferenceLevel"] for c in group_coefficients} == {"A"}
    assert {c["marginalEffectContrastLevel"] for c in group_coefficients} == {"B", "C"}

    interaction = next(c for c in output["logisticInteraction"]["coefficients"] if c["term"] == "x:z")
    assert interaction["averageMarginalEffect"] is None
    assert interaction["marginalEffectType"] == "not_applicable_interaction_term"
    assert interaction["marginalEffectReason"] == "Use conditional effect or probe output for interaction interpretation."
    factor_interactions = [
        c for c in output["logisticFactorInteraction"]["coefficients"] if ":" in c["term"]
    ]
    assert len(factor_interactions) == 2
    assert all(c["averageMarginalEffect"] is None for c in factor_interactions)
    assert all(c["marginalEffectType"] == "not_applicable_interaction_term" for c in factor_interactions)
