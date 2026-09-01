from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from app.settings import get_settings

_BOOTSTRAP_SCRIPT = r"""
bootstrap_config <- list(method = "percentile")
replicates <- 100L
alpha <- 0.05
source("engine/R/lib/bootstrap.R")
set.seed(1)
values <- c(rep(NA_real_, 4L), rnorm(96))
res <- bootstrap_ci(values, 0.0)
stopifnot(isTRUE(res$invalidReplicationCount == 4L))
stopifnot(isTRUE(length(res$values) == 96L))
clean <- c(rnorm(100))
res_clean <- bootstrap_ci(clean, 0.0)
stopifnot(isTRUE(res_clean$invalidReplicationCount == 0L))
cat("bootstrap_integrity_ok\n")
"""

_HTMT_SCRIPT = r"""
suppressPackageStartupMessages(library(jsonlite))
source("engine/R/lib/resource_budget.R")
source("engine/R/lib/parallel.R")
source("engine/R/lib/validity.R")
set.seed(7)
frame <- as.data.frame(matrix(rnorm(400), ncol = 8))
constructs <- list(
  list(constructId = "a", itemIds = c("V1", "V2", "V3", "V4")),
  list(constructId = "b", itemIds = c("V5", "V6", "V7", "V8"))
)
result <- htmt_bootstrap(frame, constructs, reps = 40, seed = 42)
stopifnot(isTRUE(result$invalidReplicationCount >= 0L))
stopifnot(isTRUE(result$affectedPairs >= 0L))
stopifnot(identical(result$replicates, 40L))
stopifnot(identical(dim(result$lower), c(2L, 2L)))
cat("htmt_integrity_ok\n")
"""


def _run_r_script(settings, script: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["R_LIBS_USER"] = str(settings.r_library_path)
    environment["LC_ALL"] = "English_United States.utf8"
    return subprocess.run(
        [str(settings.rscript_path), "--vanilla", str(script)],
        cwd=settings.project_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )


def test_bootstrap_ci_reports_dropped_replications(tmp_path: Path) -> None:
    settings = get_settings()
    if not settings.rscript_path.is_file():
        pytest.skip("Rscript 不存在，跳过 R 数值完整性检查")
    script = tmp_path / "verify-bootstrap-drop.R"
    script.write_text(_BOOTSTRAP_SCRIPT, encoding="utf-8")
    result = _run_r_script(settings, script)
    assert result.returncode == 0, result.stderr
    assert "bootstrap_integrity_ok" in result.stdout


def test_htmt_bootstrap_reports_dropped_replications(tmp_path: Path) -> None:
    settings = get_settings()
    if not settings.rscript_path.is_file():
        pytest.skip("Rscript 不存在，跳过 R 数值完整性检查")
    script = tmp_path / "verify-htmt-drop.R"
    script.write_text(_HTMT_SCRIPT, encoding="utf-8")
    result = _run_r_script(settings, script)
    assert result.returncode == 0, result.stderr
    assert "htmt_integrity_ok" in result.stdout
