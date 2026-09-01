from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.settings import get_settings


def test_rubin_pooling_and_d1_wald_test() -> None:
    settings = get_settings()
    root = settings.project_root

    r_script = """
    args <- commandArgs(trailingOnly = TRUE)
    script_dir <- args[1]
    source(file.path(script_dir, "lib", "runtime.R"))
    source(file.path(script_dir, "lib", "mi_rubin.R"))

    ests <- c(0.45, 0.52, 0.48, 0.50, 0.47)
    ses <- c(0.10, 0.11, 0.09, 0.10, 0.10)
    pool_res <- pool_rubin_estimates(ests, ses)

    v1 <- matrix(c(0.01, 0.002, 0.002, 0.02), 2, 2)
    v2 <- matrix(c(0.011, 0.002, 0.002, 0.021), 2, 2)
    e1 <- c(0.5, 1.2)
    e2 <- c(0.48, 1.15)
    d1_res <- test_d1_d3_multivariate(list(e1, e2), list(v1, v2))

    res <- list(
      pool = pool_res,
      d1 = d1_res
    )
    cat(jsonlite::toJSON(res, auto_unbox = TRUE, digits = 8))
    """

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_rubin.R"
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

    pool = out["pool"]
    assert pool["m"] == 5
    assert pool["pooledEstimate"] is not None
    assert "withinVariance" in pool
    assert "betweenVariance" in pool
    assert "FMI" in pool

    d1 = out["d1"]
    assert d1["available"] is True
    assert d1["df1"] == 2
    assert "d1Statistic" in d1
