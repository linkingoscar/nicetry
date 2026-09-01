from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.settings import get_settings


@pytest.mark.unit
@pytest.mark.r_numeric
def test_power_precision_ci_width_solver() -> None:
    """Verify analytical N-solver for target CI width precision analysis."""
    settings = get_settings()
    root = settings.project_root

    spec = {
        "family": "power_analysis",
        "designFamily": "t_test",
        "method": "analytic",
        "solveFor": "ci_width",
        "targetCIWidth": 0.4,
        "confidenceLevel": 0.95,
        "sd": 1.0,
        "groups": 1,
        "alpha": 0.05,
        "targetPower": 0.80,
        "predictors": 1,
        "simulations": 1000,
    }

    payload = json.dumps({"spec": spec})
    r_code = f"""
    source('{root.as_posix()}/engine/R/lib/runtime.R')
    source('{root.as_posix()}/engine/R/lib/power_analytic.R')
    source('{root.as_posix()}/engine/R/lib/power_t_test.R')
    spec <- jsonlite::fromJSON('{payload}')$spec
    family <- "power_analysis"
    res <- run_power()
    cat(jsonlite::toJSON(res, auto_unbox = TRUE))
    """

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_prec.R"
        script_file.write_text(r_code, encoding="utf-8")

        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        process = subprocess.run(
            [str(settings.rscript_path), "--vanilla", str(script_file)],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

    res = json.loads(process.stdout)
    assert res["familyResult"]["solveFor"] == "ci_width"
    # For CI width = 0.4, sd = 1.0, 95% CI (margin = 0.2), z ~ 1.96, required N ~ ceiling((1.96 / 0.2)^2) = 97~100
    solved_n = res["familyResult"]["solvedValue"]
    assert 95 <= solved_n <= 105
    assert len(res["estimates"]) == 2
    assert res["estimates"][0]["id"] == "required_sample_size"


@pytest.mark.unit
@pytest.mark.r_numeric
def test_power_sensitivity_mdes_solver() -> None:
    """Verify Minimum Detectable Effect Size (MDES) sensitivity power analysis."""
    settings = get_settings()
    root = settings.project_root

    spec = {
        "family": "power_analysis",
        "designFamily": "t_test",
        "method": "analytic",
        "solveFor": "sensitivity",
        "alpha": 0.05,
        "targetPower": 0.80,
        "sampleSize": 100,
        "effectSizeMetric": "cohens_d",
        "groups": 2,
        "predictors": 1,
        "simulations": 1000,
    }

    payload = json.dumps({"spec": spec})
    r_code = f"""
    source('{root.as_posix()}/engine/R/lib/runtime.R')
    source('{root.as_posix()}/engine/R/lib/power_analytic.R')
    source('{root.as_posix()}/engine/R/lib/power_t_test.R')
    spec <- jsonlite::fromJSON('{payload}')$spec
    family <- "power_analysis"
    res <- run_power()
    cat(jsonlite::toJSON(res, auto_unbox = TRUE))
    """

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        script_file = work / "test_sens.R"
        script_file.write_text(r_code, encoding="utf-8")

        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        process = subprocess.run(
            [str(settings.rscript_path), "--vanilla", str(script_file)],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

    res = json.loads(process.stdout)
    # For total N=100 (50 per group), alpha=0.05, power=0.80, minimum detectable Cohen's d ~ 0.566
    mdes = res["familyResult"]["solvedValue"]
    assert 0.50 <= mdes <= 0.65
    assert len(res["apaReports"]) >= 2
    assert (
        "sensitivity" in res["apaReports"][0].lower()
        or "detectable" in res["apaReports"][1].lower()
    )
