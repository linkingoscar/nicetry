from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.settings import get_settings


def test_tost_and_multiplicity_correction() -> None:
    settings = get_settings()
    root = settings.project_root

    r_script = """
    args <- commandArgs(trailingOnly = TRUE)
    script_dir <- args[1]
    source(file.path(script_dir, "lib", "runtime.R"))
    source(file.path(script_dir, "lib", "tost_multiplicity.R"))

    set.seed(20260714)
    n <- 40
    g <- factor(rep(c("A", "B"), each = 20))
    y <- c(rnorm(20, mean = 5, sd = 1), rnorm(20, mean = 5.1, sd = 1))
    df <- data.frame(y = y, g = g)

    tost_res <- run_tost_equivalence(df, "y", "g", low_eqbound = -0.5, high_eqbound = 0.5)
    mult_res <- apply_multiplicity_correction(c(0.01, 0.04, 0.08, 0.15), method = "holm")

    res <- list(
      tost = tost_res,
      multiplicity = mult_res
    )
    cat(jsonlite::toJSON(res, auto_unbox = TRUE, digits = 8))
    """

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_tm.R"
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

    tost = out["tost"]
    assert tost["available"] is True
    assert "pTOST" in tost
    assert "equivalent" in tost

    mult = out["multiplicity"]
    assert mult["available"] is True
    assert mult["method"] == "holm"
    assert len(mult["pValues"]) == 4
    first_p = mult["pValues"][0]
    assert "adjustedPValue" in first_p
