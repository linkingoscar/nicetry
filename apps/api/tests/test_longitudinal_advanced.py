from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

from app.api.schemas import LongitudinalPanelInput
from app.settings import get_settings


def _lcm_request(wave_count: int = 5) -> dict[str, Any]:
    return {
        "model_type": "lcm_sr",
        "measurement_mode": "latent_items",
        "subject_variable_id": "subject_id",
        "waves": [
            {
                "label": f"T{wave}",
                "time_value": wave - 1,
                "x_item_ids": [f"x_t{wave}_i{item}" for item in range(1, 4)],
                "y_item_ids": [f"y_t{wave}_i{item}" for item in range(1, 4)],
            }
            for wave in range(1, wave_count + 1)
        ],
        "estimator": "MLR",
        "missing": "fiml",
        "growth_shape": "linear",
        "invariance_level": "metric",
        "compare_competing_models": False,
        "run_robustness_checks": False,
    }


def test_lcm_sr_contract_requires_latent_five_wave_design() -> None:
    with pytest.raises(ValueError, match="至少需要五个"):
        LongitudinalPanelInput.model_validate(_lcm_request(4))
    observed = _lcm_request()
    observed["measurement_mode"] = "observed_scores"
    with pytest.raises(ValueError, match="题项级潜变量"):
        LongitudinalPanelInput.model_validate(observed)


def test_quadratic_growth_is_reserved_for_lcm_sr() -> None:
    request = _lcm_request()
    request["model_type"] = "ri_clpm"
    request["growth_shape"] = "quadratic"
    with pytest.raises(ValueError, match="仅适用于 LCM-SR"):
        LongitudinalPanelInput.model_validate(request)


def test_longitudinal_ulmc_contract_enforces_measurement_gates() -> None:
    request = _lcm_request()
    request["model_type"] = "ri_clpm"
    request["cmb_sensitivity"] = "global_ulmc"
    request["invariance_level"] = "metric"
    with pytest.raises(ValueError, match="标量或严格"):
        LongitudinalPanelInput.model_validate(request)


def test_lcm_sr_returns_growth_and_structured_residual_evidence() -> None:
    settings = get_settings()
    root = settings.project_root
    panel = LongitudinalPanelInput.model_validate(_lcm_request())
    spec = {
        "modelType": panel.model_type,
        "measurementMode": panel.measurement_mode,
        "subjectVariableId": panel.subject_variable_id,
        "waves": [
            {
                "label": wave.label,
                "timeValue": wave.time_value,
                "xItemIds": wave.x_item_ids,
                "yItemIds": wave.y_item_ids,
            }
            for wave in panel.waves
        ],
        "estimator": panel.estimator,
        "missing": panel.missing,
        "constrainAcrossTime": panel.constrain_across_time,
        "growthShape": panel.growth_shape,
        "indicatorScale": panel.indicator_scale,
        "invarianceLevel": panel.invariance_level,
        "partialInvariancePositions": [],
        "compareCompetingModels": False,
        "runRobustnessChecks": False,
    }
    r_script = """
    suppressPackageStartupMessages(library(jsonlite))
    source(commandArgs(trailingOnly = TRUE)[1])
    source(commandArgs(trailingOnly = TRUE)[2])
    source(commandArgs(trailingOnly = TRUE)[3])
    input <- fromJSON(commandArgs(trailingOnly = TRUE)[4], simplifyVector = FALSE)
    data <- read.csv(commandArgs(trailingOnly = TRUE)[5], check.names = FALSE)
    result <- fit_longitudinal_panel(data, input, function(id) id)
    write_json(result, commandArgs(trailingOnly = TRUE)[6], auto_unbox = TRUE, null = "null")
    """
    with tempfile.TemporaryDirectory(prefix="rp-lcm-sr-test-") as temporary:
        work = Path(temporary)
        script = work / "run.R"
        specification = work / "spec.json"
        output = work / "result.json"
        script.write_text(r_script, encoding="utf-8")
        specification.write_text(json.dumps(spec), encoding="utf-8")
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(script),
                str(root / "engine/R/lib/longitudinal_lcm_sr.R"),
                str(root / "engine/R/lib/longitudinal_latent.R"),
                str(root / "engine/R/lib/longitudinal_panel.R"),
                str(specification),
                str(root / "samples/data/longitudinal-panel-demo.csv"),
                str(output),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        result = json.loads(output.read_text(encoding="utf-8")) if output.exists() else None

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    assert result["modelType"] == "lcm_sr"
    assert result["waveCount"] == 5
    assert result["growthModel"]["growthShape"] == "linear"
    assert result["growthModel"]["timeLoadings"] == [0, 1, 2, 3, 4]
    assert result["growthModel"]["components"]
    assert isinstance(result["growthModel"]["identification"]["valid"], bool)
    assert len([path for path in result["paths"] if path["pathType"] == "cross_lagged"]) == 8


def test_longitudinal_ulmc_returns_identification_and_path_sensitivity() -> None:
    settings = get_settings()
    root = settings.project_root
    request = _lcm_request(3)
    request.update(
        {
            "model_type": "ri_clpm",
            "growth_shape": "linear",
            "invariance_level": "scalar",
            "partial_invariance_positions": [
                "x:1",
                "x:2",
                "x:3",
                "y:1",
                "y:2",
                "y:3",
            ],
            "cmb_sensitivity": "global_ulmc",
        }
    )
    panel = LongitudinalPanelInput.model_validate(request)
    spec = {
        "modelType": panel.model_type,
        "measurementMode": panel.measurement_mode,
        "subjectVariableId": panel.subject_variable_id,
        "waves": [
            {
                "label": wave.label,
                "timeValue": wave.time_value,
                "xItemIds": wave.x_item_ids,
                "yItemIds": wave.y_item_ids,
            }
            for wave in panel.waves
        ],
        "estimator": panel.estimator,
        "missing": panel.missing,
        "constrainAcrossTime": False,
        "growthShape": "linear",
        "indicatorScale": "continuous",
        "invarianceLevel": "scalar",
        "partialInvariancePositions": panel.partial_invariance_positions,
        "cmbSensitivity": "global_ulmc",
        "compareCompetingModels": False,
        "runRobustnessChecks": False,
    }
    r_script = """
    suppressPackageStartupMessages(library(jsonlite))
    source(commandArgs(trailingOnly = TRUE)[1])
    source(commandArgs(trailingOnly = TRUE)[2])
    source(commandArgs(trailingOnly = TRUE)[3])
    input <- fromJSON(commandArgs(trailingOnly = TRUE)[4], simplifyVector = FALSE)
    data <- read.csv(commandArgs(trailingOnly = TRUE)[5], check.names = FALSE)
    result <- fit_longitudinal_panel(data, input, function(id) id)
    write_json(result, commandArgs(trailingOnly = TRUE)[6], auto_unbox = TRUE, null = "null")
    """
    with tempfile.TemporaryDirectory(prefix="rp-ulmc-test-") as temporary:
        work = Path(temporary)
        script = work / "run.R"
        specification = work / "spec.json"
        output = work / "result.json"
        script.write_text(r_script, encoding="utf-8")
        specification.write_text(json.dumps(spec), encoding="utf-8")
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(script),
                str(root / "engine/R/lib/longitudinal_cmb.R"),
                str(root / "engine/R/lib/longitudinal_latent.R"),
                str(root / "engine/R/lib/longitudinal_panel.R"),
                str(specification),
                str(root / "samples/data/longitudinal-panel-demo.csv"),
                str(output),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        result = json.loads(output.read_text(encoding="utf-8")) if output.exists() else None

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    cmb = result["cmbSensitivity"]
    assert cmb["requested"] is True
    assert cmb["available"] is True
    assert isinstance(cmb["validForInterpretation"], bool)
    assert isinstance(cmb["identification"]["informationFullRank"], bool)
    assert cmb["methodLoadings"]
    assert cmb["pathChanges"]
