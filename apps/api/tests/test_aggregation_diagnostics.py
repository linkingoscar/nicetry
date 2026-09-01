from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.settings import get_settings


def test_aggregation_helper_scales_rwg_null_variance_and_returns_stable_failure() -> None:
    settings = get_settings()
    root = settings.project_root
    script = """
    args <- commandArgs(trailingOnly = TRUE)
    script_dir <- args[[1]]
    source(file.path(script_dir, "lib", "runtime.R"))
    source(file.path(script_dir, "lib", "aggregation_diagnostics.R"))
    source(file.path(script_dir, "lib", "multilevel_aggregation.R"))

    clustered <- data.frame(
      score = c(2.0, 2.5, 3.0, 3.5, 4.0, 4.5),
      team = c("a", "a", "a", "b", "b", "b")
    )
    valid <- calc_aggregation_diagnostics(
      clustered, "score", "Scale", "team", 1, 5, 4, "mean"
    )
    invalid <- calc_aggregation_diagnostics(
      transform(clustered, team = "a"),
      "score", "Scale", "team", 1, 5, 4, "mean"
    )
    advanced <- calc_multilevel_aggregation(
      clustered, "score", "team", 1, 5, 4, "mean"
    )
    cat(jsonlite::toJSON(
      list(valid = valid, invalid = invalid, advanced = advanced),
      auto_unbox = TRUE,
      digits = 15,
      null = "null"
    ))
    """

    with tempfile.TemporaryDirectory() as temporary:
        script_path = Path(temporary) / "aggregation-test.R"
        script_path.write_text(script, encoding="utf-8")
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        environment["LC_ALL"] = "English_United States.utf8"
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(script_path),
                str(root / "engine" / "R"),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["valid"]["available"] is True
    assert result["valid"]["rwg"]["expectedScoreVariance"] == pytest.approx(
        ((5**2 - 1) / 12) / 4,
        abs=1e-12,
    )
    assert result["advanced"]["scale"]["expectedScoreVariance"] == pytest.approx(
        result["valid"]["rwg"]["expectedScoreVariance"], abs=1e-12
    )
    assert result["advanced"]["meanRwg"] == pytest.approx(
        result["valid"]["rwg"]["mean"], abs=1e-12
    )
    assert "aggregationJustified" not in result["advanced"]
    assert result["invalid"] == {
        "id": "score",
        "label": "Scale",
        "available": False,
        "reasonCode": "AGGREGATION_INSUFFICIENT_CLUSTERS",
        "reason": "至少需要两个 cluster，且需存在 cluster 内重复观测。",
    }
