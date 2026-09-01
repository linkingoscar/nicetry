from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.settings import get_settings


def test_process_johnson_neyman_and_simple_slopes() -> None:
    settings = get_settings()
    root = settings.project_root

    r_script = """
    args <- commandArgs(trailingOnly = TRUE)
    script_dir <- args[1]
    source(file.path(script_dir, "lib", "runtime.R"))
    source(file.path(script_dir, "lib", "inference_covariance.R"))
    source(file.path(script_dir, "lib", "analysis_regression.R"))

    set.seed(20260714)
    n <- 100
    x <- rnorm(n)
    w <- rnorm(n)
    xw <- x * w
    y <- 0.4 * x + 0.3 * w + 0.25 * xw + rnorm(n)
    df <- data.frame(x = x, w = w, xw = xw, y = y)

    fit <- lm(y ~ x + w + xw, data = df)
    b <- coef(fit)
    v <- vcov(fit)

    b1 <- b["x"]
    b3 <- b["xw"]
    var_b1 <- v["x", "x"]
    var_b3 <- v["xw", "xw"]
    cov_b1_b3 <- v["x", "xw"]
    df_res <- df.residual(fit)

    jn_res <- calc_johnson_neyman(b1, b3, var_b1, var_b3, cov_b1_b3, df_res, min(w), max(w))
    cat(jsonlite::toJSON(jn_res, auto_unbox = TRUE, digits = 8))
    """

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_jn.R"
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
        jn_out = json.loads(completed.stdout)

    assert jn_out["available"] is True
    assert "tCritical" in jn_out
    assert "grid" in jn_out
    assert len(jn_out["grid"]["simpleSlopes"]) == 50
    assert len(jn_out["grid"]["wValues"]) == 50
