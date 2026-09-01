from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.api.schemas import EmpiricalAnalysisRequest, LongitudinalPowerInput
from app.settings import get_settings


def _panel_request(model_type: str) -> dict[str, object]:
    return {
        "longitudinal_panel": {
            "model_type": model_type,
            "subject_variable_id": "subject_id",
            "waves": [
                {
                    "label": f"T{index}",
                    "time_value": index - 1,
                    "x_variable_id": f"x{index}",
                    "y_variable_id": f"y{index}",
                }
                for index in range(1, 4)
            ],
        }
    }


def test_longitudinal_power_contract_rejects_clpm() -> None:
    request = _panel_request("clpm")
    panel = request["longitudinal_panel"]
    assert isinstance(panel, dict)
    panel["power_analysis"] = {"sample_sizes": [100], "replications": 20}
    with pytest.raises(ValueError, match="针对三时点及以上 RI-CLPM"):
        EmpiricalAnalysisRequest.model_validate(request)


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"sample_sizes": [100, 100]}, "不得重复"),
        ({"sample_sizes": [200, 100]}, "升序"),
        ({"sample_sizes": [49]}, "50–10000"),
        (
            {
                "sample_sizes": [100],
                "reliability": 1,
                "estimate_measurement_error": True,
            },
            "信度必须小于 1",
        ),
        (
            {"sample_sizes": list(range(100, 220, 10)), "replications": 500},
            "最多运行 5000",
        ),
    ],
)
def test_longitudinal_power_contract_rejects_invalid_designs(
    patch: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        LongitudinalPowerInput.model_validate(patch)


def test_ri_clpm_monte_carlo_power_returns_directional_evidence() -> None:
    settings = get_settings()
    root = settings.project_root
    spec = {
        "modelType": "ri_clpm",
        "waves": [{"label": "T1"}, {"label": "T2"}, {"label": "T3"}],
        "estimator": "MLR",
        "constrainAcrossTime": False,
        "powerAnalysis": {
            "sampleSizes": [80],
            "replications": 20,
            "targetPower": 0.8,
            "alpha": 0.05,
            "autoregressiveX": 0.4,
            "autoregressiveY": 0.4,
            "crossLaggedXToY": 0.15,
            "crossLaggedYToX": 0.1,
            "icc": 0.4,
            "randomInterceptCorrelation": 0.3,
            "withinCorrelation": 0.2,
            "reliability": 0.8,
            "estimateMeasurementError": False,
            "seed": 20260714,
        },
    }
    r_script = """
    suppressPackageStartupMessages(library(jsonlite))
    source(commandArgs(trailingOnly = TRUE)[1])
    input <- fromJSON(commandArgs(trailingOnly = TRUE)[2], simplifyVector = FALSE)
    result <- longitudinal_power_analysis(input)
    write_json(result, commandArgs(trailingOnly = TRUE)[3], auto_unbox = TRUE, null = "null")
    """
    with tempfile.TemporaryDirectory(prefix="rp-panel-power-test-") as temporary:
        work = Path(temporary)
        script_path = work / "run.R"
        spec_path = work / "spec.json"
        output_path = work / "output.json"
        script_path.write_text(r_script, encoding="utf-8")
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(script_path),
                str(root / "engine/R/lib/longitudinal_power.R"),
                str(spec_path),
                str(output_path),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else None
        )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    assert result["provenance"]["engine"] == "R powRICLPM"
    assert {row["direction"] for row in result["results"]} == {"x_to_y", "y_to_x"}
    assert all(0 <= row["power"] <= 1 for row in result["results"])
    assert isinstance(result["estimationProblems"], list)
