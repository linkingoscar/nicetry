from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.settings import get_settings


def test_repeated_measures_anova_and_sphericity() -> None:
    settings = get_settings()
    root = settings.project_root

    r_script = """
    args <- commandArgs(trailingOnly = TRUE)
    script_dir <- args[1]
    source(file.path(script_dir, "lib", "runtime.R"))
    source(file.path(script_dir, "lib", "repeated_mixed.R"))

    set.seed(20260714)
    n <- 50
    t1 <- rnorm(n, mean = 5.0, sd = 1.0)
    t2 <- t1 + rnorm(n, mean = 0.5, sd = 0.5)
    t3 <- t2 + rnorm(n, mean = 0.8, sd = 0.5)
    df <- data.frame(t1 = t1, t2 = t2, t3 = t3)

    rm_res <- fit_repeated_measures_anova(df, c("t1", "t2", "t3"))
    cat(jsonlite::toJSON(rm_res, auto_unbox = TRUE, digits = 8))
    """

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_rm.R"
        script_file.write_text(r_script, encoding="utf-8")

        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [str(settings.rscript_path), "--vanilla", str(script_file), str(root / "engine/R")],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        rm_out = json.loads(completed.stdout)

    # Validate RM-ANOVA & Sphericity
    assert rm_out["available"] is True
    assert rm_out["sampleSize"] == 50
    assert rm_out["repeatedConditionsCount"] == 3

    assert "sphericity" in rm_out
    sph = rm_out["sphericity"]
    assert sph["sphericityApplicable"] is True
    assert "mauchlyW" in sph
    assert "greenhouseGeisserEpsilon" in sph
    assert "huynhFeldtEpsilon" in sph

    assert "anovaTable" in rm_out
    anova = rm_out["anovaTable"]
    assert "uncorrected" in anova
    assert "greenhouseGeisser" in anova
    assert "huynhFeldt" in anova
    assert anova["greenhouseGeisser"]["df1"] is not None

    assert "estimatedMarginalMeans" in rm_out
    assert len(rm_out["estimatedMarginalMeans"]) == 3
    first_emm = rm_out["estimatedMarginalMeans"][0]
    assert "mean" in first_emm
    assert "ciLower" in first_emm
