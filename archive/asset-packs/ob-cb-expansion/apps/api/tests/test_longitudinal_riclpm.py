from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.settings import get_settings


def test_riclpm_longitudinal_fitting() -> None:
    settings = get_settings()
    root = settings.project_root

    r_script = """
    args <- commandArgs(trailingOnly = TRUE)
    script_dir <- args[1]
    source(file.path(script_dir, "lib", "runtime.R"))
    source(file.path(script_dir, "lib", "longitudinal_advanced.R"))

    set.seed(20260714)
    n <- 100
    x1 <- rnorm(n); y1 <- rnorm(n)
    x2 <- 0.4 * x1 + 0.2 * y1 + rnorm(n)
    y2 <- 0.4 * y1 + 0.3 * x1 + rnorm(n)
    x3 <- 0.4 * x2 + 0.2 * y2 + rnorm(n)
    y3 <- 0.4 * y2 + 0.3 * x2 + rnorm(n)

    df <- data.frame(x1 = x1, x2 = x2, x3 = x3, y1 = y1, y2 = y2, y3 = y3)
    res <- fit_riclpm_model(df, c("x1", "x2", "x3"), c("y1", "y2", "y3"))
    cat(jsonlite::toJSON(res, auto_unbox = TRUE, digits = 8))
    """

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_riclpm.R"
        script_file.write_text(r_script, encoding="utf-8")

        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [str(settings.rscript_path), "--vanilla", str(script_file), str(root / "engine/R")],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=40,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        out = json.loads(completed.stdout)

    assert out["available"] is True
    assert out["modelType"] == "RI-CLPM"
    assert out["sampleSize"] == 100
    assert out["numWaves"] == 3
    assert "fitIndices" in out
    assert "crossLaggedEffects" in out
    assert len(out["crossLaggedEffects"]) == 4
