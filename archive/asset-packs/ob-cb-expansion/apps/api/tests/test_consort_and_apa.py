from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.settings import get_settings


def test_consort_flow_and_apa_report() -> None:
    settings = get_settings()
    root = settings.project_root

    r_script = """
    args <- commandArgs(trailingOnly = TRUE)
    script_dir <- args[1]
    source(file.path(script_dir, "lib", "runtime.R"))
    source(file.path(script_dir, "lib", "factorial_ancova.R"))
    source(file.path(script_dir, "lib", "experiment_protocol.R"))

    set.seed(20260714)
    n <- 50
    g <- factor(rep(c("T1", "T2"), each = 25))
    y <- rnorm(50, mean = 10, sd = 2)
    df <- data.frame(y = y, g = g)
    df$y[c(3, 7)] <- NA

    consort_res <- generate_consort_flow_data(df, "y", "g")
    ancova_res <- fit_factorial_ancova(df, "y", "g")

    res <- list(
      consort = consort_res,
      ancova = ancova_res
    )
    cat(jsonlite::toJSON(res, auto_unbox = TRUE, digits = 8))
    """

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_ca.R"
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
        out = json.loads(completed.stdout)

    consort = out["consort"]
    assert consort["available"] is True
    assert consort["enrollment"]["screened"] == 50
    assert consort["enrollment"]["excluded"] == 2
    assert consort["enrollment"]["randomized"] == 48

    ancova = out["ancova"]
    assert "plotReadyData" in ancova
    assert len(ancova["plotReadyData"]) == 2
    assert "apaReport" in ancova
    assert "ANOVA" in ancova["apaReport"]
