from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.settings import get_settings


def test_factorial_ancova_and_planned_contrasts() -> None:
    settings = get_settings()
    root = settings.project_root

    r_script = """
    args <- commandArgs(trailingOnly = TRUE)
    script_dir <- args[1]
    source(file.path(script_dir, "lib", "runtime.R"))
    source(file.path(script_dir, "lib", "factorial_ancova.R"))
    source(file.path(script_dir, "lib", "experiment_posthoc.R"))

    set.seed(20260714)
    n <- 60
    f1 <- factor(sample(c("A1", "A2"), n, replace = TRUE))
    f2 <- factor(sample(c("B1", "B2", "B3"), n, replace = TRUE))
    cov <- rnorm(n)
    y <- 2.0 * (f1 == "A2") + 1.5 * (f2 == "B2") + 0.8 * cov + rnorm(n)
    df <- data.frame(y = y, f1 = f1, f2 = f2, cov = cov)

    fit_res <- fit_factorial_ancova(df, "y", c("f1", "f2"), covariates = "cov", sum_of_squares = "III")
    contrast_res <- run_planned_contrasts(df, "y", "f1", c(1, -1))
    gh_res <- fit_games_howell(df, "y", "f1")
    homo_res <- test_homogeneity_of_slopes(df, "y", "f1", "cov")

    res <- list(
      ancova = fit_res,
      contrast = contrast_res,
      gamesHowell = gh_res,
      homogeneity = homo_res
    )
    cat(jsonlite::toJSON(res, auto_unbox = TRUE, digits = 8))
    """

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_ancova.R"
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

    # Validate ANCOVA & SS Table
    ancova = output["ancova"]
    assert ancova["available"] is True
    assert "anovaTable" in ancova
    assert len(ancova["anovaTable"]) >= 3
    first_term = ancova["anovaTable"][0]
    assert "partialEtaSquared" in first_term
    assert "partialOmegaSquared" in first_term
    assert "estimatedMarginalMeans" in ancova

    # Validate Planned Contrasts
    contrast = output["contrast"]
    assert contrast["estimate"] is not None
    assert "tStatistic" in contrast
    assert "pValue" in contrast

    # Validate Games-Howell
    gh = output["gamesHowell"]
    assert len(gh) >= 1
    assert gh[0]["adjustment"] == "games_howell"

    # Validate Homogeneity of Slopes
    homo = output["homogeneity"]
    assert homo["covariate"] == "cov"
    assert homo["groupVariable"] == "f1"
    assert "fStatistic" in homo
    assert "pValue" in homo
    assert "df1" in homo
    assert "df2" in homo
    assert isinstance(homo["slopesHomogeneous"], bool)


def test_homogeneity_of_slopes_violation() -> None:
    settings = get_settings()
    root = settings.project_root

    r_script = """
    args <- commandArgs(trailingOnly = TRUE)
    script_dir <- args[1]
    source(file.path(script_dir, "lib", "runtime.R"))
    source(file.path(script_dir, "lib", "factorial_ancova.R"))

    set.seed(20260714)
    n <- 120
    f1 <- factor(sample(c("A1", "A2"), n, replace = TRUE))
    cov <- rnorm(n)
    # Strong interaction term breaking parallel slopes
    y <- 0.5 * cov + 4.0 * (f1 == "A2") * cov + rnorm(n)
    df <- data.frame(y = y, f1 = f1, cov = cov)

    homo_res <- test_homogeneity_of_slopes(df, "y", "f1", "cov")
    cat(jsonlite::toJSON(homo_res, auto_unbox = TRUE, digits = 8))
    """

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_ancova_violation.R"
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

    assert output["slopesHomogeneous"] is False
    assert "违背 ANCOVA 斜率平行假设" in output["warning"]
    assert output["pValue"] < 0.05
