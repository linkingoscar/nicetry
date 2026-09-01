from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.settings import get_settings


def test_cmb_ulmc_model_comparison() -> None:
    settings = get_settings()
    root = settings.project_root

    r_script = """
    args <- commandArgs(trailingOnly = TRUE)
    script_dir <- args[1]
    source(file.path(script_dir, "lib", "runtime.R"))
    source(file.path(script_dir, "lib", "cmb.R"))

    set.seed(20260714)
    n <- 60
    f1 <- rnorm(n)
    f2 <- rnorm(n)
    m <- rnorm(n) # common method factor

    x1 <- 0.7 * f1 + 0.3 * m + rnorm(n, sd = 0.5)
    x2 <- 0.8 * f1 + 0.3 * m + rnorm(n, sd = 0.5)
    y1 <- 0.7 * f2 + 0.3 * m + rnorm(n, sd = 0.5)
    y2 <- 0.8 * f2 + 0.3 * m + rnorm(n, sd = 0.5)

    df <- data.frame(x1 = x1, x2 = x2, y1 = y1, y2 = y2)
    constructs <- list(
      list(id = "F1", itemIds = list("x1", "x2")),
      list(id = "F2", itemIds = list("y1", "y2"))
    )

    ulmc_res <- fit_ulmc_cmb_model(df, constructs)
    cat(jsonlite::toJSON(ulmc_res, auto_unbox = TRUE, digits = 8))
    """

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_ulmc.R"
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
            errors="replace",
            timeout=30,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        out = json.loads(completed.stdout)

    assert out["available"] is True
    assert out["method"] == "Unmeasured_Latent_Method_Factor_ULMC"
    assert "baselineModel" in out
    assert "ulmcModel" in out
    assert "modelComparison" in out
    comp = out["modelComparison"]
    assert "deltaChisq" in comp
    assert "deltaCfi" in comp
