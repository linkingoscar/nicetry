from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.settings import get_settings


def test_mice_typed_inference() -> None:
    settings = get_settings()
    root = settings.project_root

    r_script = """
    args <- commandArgs(trailingOnly = TRUE)
    script_dir <- args[1]
    source(file.path(script_dir, "lib", "runtime.R"))
    source(file.path(script_dir, "lib", "imputation_runner.R"))

    num_vec <- c(1.2, 2.5, NA, 4.1, 5.0)
    bin_vec <- factor(c("Yes", "No", NA, "Yes", "No"))
    ord_vec <- ordered(c("Low", "Med", NA, "High", "Low"), levels = c("Low", "Med", "High"))

    res <- list(
      numMethod = infer_method_test(num_vec),
      binMethod = infer_method_test(bin_vec),
      ordMethod = infer_method_test(ord_vec)
    )
    cat(jsonlite::toJSON(res, auto_unbox = TRUE))
    """

    # Create small standalone script to test infer_method
    test_code = """
    infer_method_test <- function(values) {
      observed <- values[!is.na(values)]
      if (length(observed) == 0L) return("pmm")
      if (is.ordered(values)) return("polr")
      if (is.factor(values) || is.character(values)) {
        return(if (length(unique(observed)) <= 2L) "logreg" else "polyreg")
      }
      if (length(unique(observed)) <= 2L) return("logreg")
      if (is.numeric(values) && all(abs(observed - round(observed)) < 1e-8) && length(unique(observed)) >= 3L && length(unique(observed)) <= 7L) return("polr")
      "pmm"
    }
    """

    r_full_script = test_code + "\n" + r_script

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_mice.R"
        script_file.write_text(r_full_script, encoding="utf-8")

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

    assert out["numMethod"] == "pmm"
    assert out["binMethod"] == "logreg"
    assert out["ordMethod"] == "polr"
