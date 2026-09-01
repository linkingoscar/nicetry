from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from _longitudinal_panel_helpers import (
    _latent_panel_request,
    _panel_contract_payload,
    _panel_request,
)

from app.api.schemas import (
    EmpiricalAnalysisRequest,
    LongitudinalPanelInput,
)
from app.settings import get_settings


def test_ri_clpm_contract_requires_three_waves() -> None:
    request = _panel_request()
    panel = request["longitudinal_panel"]
    assert isinstance(panel, dict)
    panel["waves"] = panel["waves"][:2]  # type: ignore[index]
    with pytest.raises(ValueError, match="至少需要三个时间点"):
        EmpiricalAnalysisRequest.model_validate(request)


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        (
            {
                "waves": [
                    {"label": "T1", "time_value": 0, "x_variable_id": "x1", "y_variable_id": "y1"},
                    {"label": "T1", "time_value": 1, "x_variable_id": "x2", "y_variable_id": "y2"},
                    {"label": "T3", "time_value": 2, "x_variable_id": "x3", "y_variable_id": "y3"},
                ]
            },
            "标签不得重复",
        ),
        (
            {
                "waves": [
                    {"label": "T1", "time_value": 0, "x_variable_id": "x1", "y_variable_id": "y1"},
                    {"label": "T2", "time_value": 0, "x_variable_id": "x2", "y_variable_id": "y2"},
                    {"label": "T3", "time_value": 2, "x_variable_id": "x3", "y_variable_id": "y3"},
                ]
            },
            "时间值不得重复",
        ),
        (
            {
                "waves": [
                    {"label": "T1", "time_value": 0, "x_variable_id": "x1", "y_variable_id": "y1"},
                    {"label": "T2", "time_value": 2, "x_variable_id": "x2", "y_variable_id": "y2"},
                    {"label": "T3", "time_value": 1, "x_variable_id": "x3", "y_variable_id": "y3"},
                ]
            },
            "升序",
        ),
        (
            {
                "waves": [
                    {"label": "T1", "time_value": 0, "x_variable_id": "x1"},
                    {"label": "T2", "time_value": 1, "x_variable_id": "x2", "y_variable_id": "y2"},
                    {"label": "T3", "time_value": 2, "x_variable_id": "x3", "y_variable_id": "y3"},
                ]
            },
            "每个波次指定 X/Y",
        ),
        (
            {
                "waves": [
                    {"label": "T1", "time_value": 0, "x_variable_id": "x1", "y_variable_id": "y1"},
                    {"label": "T2", "time_value": 1, "x_variable_id": "x1", "y_variable_id": "y2"},
                    {"label": "T3", "time_value": 2, "x_variable_id": "x3", "y_variable_id": "y3"},
                ]
            },
            "映射到不同",
        ),
        ({"estimator": "WLSMV"}, "仅支持连续变量"),
        ({"invariance_level": "metric"}, "仅适用于题项级"),
        (
            {"estimator": "WLSMV", "power_analysis": {"sample_sizes": [100]}},
            "功效模拟使用连续 ML/MLR",
        ),
    ],
)
def test_observed_panel_contract_rejects_invalid_specifications(
    patch: dict[str, object],
    message: str,
) -> None:
    payload = _panel_contract_payload()
    payload.update(patch)
    with pytest.raises(ValueError, match=message):
        LongitudinalPanelInput.model_validate(payload)


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        (
            {
                "waves": [
                    {
                        "label": "T1",
                        "time_value": 0,
                        "x_item_ids": ["x1"],
                        "y_item_ids": ["y1", "y2"],
                    },
                    {
                        "label": "T2",
                        "time_value": 1,
                        "x_item_ids": ["x2"],
                        "y_item_ids": ["y3", "y4"],
                    },
                    {
                        "label": "T3",
                        "time_value": 2,
                        "x_item_ids": ["x3"],
                        "y_item_ids": ["y5", "y6"],
                    },
                ]
            },
            "至少需要两个题项",
        ),
        (
            {
                "waves": [
                    {
                        "label": "T1",
                        "time_value": 0,
                        "x_item_ids": ["x1", "x2"],
                        "y_item_ids": ["y1", "y2"],
                    },
                    {
                        "label": "T2",
                        "time_value": 1,
                        "x_item_ids": ["x3", "x4", "x5"],
                        "y_item_ids": ["y3", "y4"],
                    },
                    {
                        "label": "T3",
                        "time_value": 2,
                        "x_item_ids": ["x6", "x7"],
                        "y_item_ids": ["y5", "y6"],
                    },
                ]
            },
            "相同数量",
        ),
        (
            {
                "waves": [
                    {
                        "label": "T1",
                        "time_value": 0,
                        "x_item_ids": ["x1", "x2"],
                        "y_item_ids": ["y1", "y2"],
                    },
                    {
                        "label": "T2",
                        "time_value": 1,
                        "x_item_ids": ["x1", "x4"],
                        "y_item_ids": ["y3", "y4"],
                    },
                    {
                        "label": "T3",
                        "time_value": 2,
                        "x_item_ids": ["x5", "x6"],
                        "y_item_ids": ["y5", "y6"],
                    },
                ]
            },
            "不同的数据列",
        ),
        ({"indicator_scale": "ordinal"}, "必须使用 WLSMV"),
        ({"estimator": "WLSMV"}, "不支持 FIML"),
        ({"partial_invariance_positions": ["x:99"]}, "部分等值位置无效"),
    ],
)
def test_latent_panel_contract_rejects_invalid_specifications(
    patch: dict[str, object],
    message: str,
) -> None:
    request = _latent_panel_request("ri_clpm")
    payload = request["longitudinal_panel"]
    assert isinstance(payload, dict)
    payload.update(patch)
    with pytest.raises(ValueError, match=message):
        LongitudinalPanelInput.model_validate(payload)


@pytest.mark.parametrize("model_type", ["clpm", "ri_clpm"])
def test_longitudinal_panel_r_slice_returns_paths_and_diagnostics(model_type: str) -> None:
    settings = get_settings()
    root = settings.project_root
    request = EmpiricalAnalysisRequest.model_validate(_panel_request(model_type))
    assert request.longitudinal_panel is not None
    panel = request.longitudinal_panel
    spec = {
        "modelType": panel.model_type,
        "subjectVariableId": panel.subject_variable_id,
        "waves": [
            {
                "label": wave.label,
                "timeValue": wave.time_value,
                "xVariableId": wave.x_variable_id,
                "yVariableId": wave.y_variable_id,
            }
            for wave in panel.waves
        ],
        "estimator": panel.estimator,
        "missing": panel.missing,
        "constrainAcrossTime": panel.constrain_across_time,
        "compareCompetingModels": model_type == "ri_clpm",
        "runRobustnessChecks": model_type == "clpm",
    }
    r_script = """
    suppressPackageStartupMessages(library(jsonlite))
    source(commandArgs(trailingOnly = TRUE)[1])
    input <- fromJSON(commandArgs(trailingOnly = TRUE)[2], simplifyVector = FALSE)
    data <- read.csv(commandArgs(trailingOnly = TRUE)[3], check.names = FALSE)
    result <- fit_longitudinal_panel(data, input, function(id) id)
    write_json(result, commandArgs(trailingOnly = TRUE)[4], auto_unbox = TRUE, null = "null")
    """
    with tempfile.TemporaryDirectory(prefix="rp-panel-test-") as temporary:
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
                str(root / "engine/R/lib/longitudinal_panel.R"),
                str(spec_path),
                str(root / "samples/data/longitudinal-panel-demo.csv"),
                str(output_path),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else None
        )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    assert result["modelType"] == model_type
    assert result["sampleSize"] == 240
    assert len(result["waveSampleFlow"]) == 3
    assert len([path for path in result["paths"] if path["pathType"] == "cross_lagged"]) == 4
    assert isinstance(result["diagnostics"], list)
    assert isinstance(result["validForInterpretation"], bool)
    if model_type == "ri_clpm":
        assert {model["modelType"] for model in result["competingModels"]} == {
            "clpm",
            "ri_clpm",
        }
    else:
        assert len(result["robustnessChecks"]) >= 2


@pytest.mark.parametrize("model_type", ["clpm", "ri_clpm"])
def test_latent_longitudinal_panel_runs_invariance_and_competing_models(
    model_type: str,
) -> None:
    settings = get_settings()
    root = settings.project_root
    request = EmpiricalAnalysisRequest.model_validate(_latent_panel_request(model_type))
    assert request.longitudinal_panel is not None
    panel = request.longitudinal_panel
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
        "indicatorScale": panel.indicator_scale,
        "invarianceLevel": panel.invariance_level,
        "partialInvariancePositions": panel.partial_invariance_positions,
        "compareCompetingModels": panel.compare_competing_models,
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
    with tempfile.TemporaryDirectory(prefix="rp-latent-panel-test-") as temporary:
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
                str(root / "engine/R/lib/longitudinal_lcm_sr.R"),
                str(root / "engine/R/lib/longitudinal_latent.R"),
                str(root / "engine/R/lib/longitudinal_panel.R"),
                str(spec_path),
                str(root / "samples/data/longitudinal-panel-demo.csv"),
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
    assert result["measurementMode"] == "latent_items"
    assert result["sampleSize"] == 240
    assert len(result["measurementInvariance"]["models"]) == 4
    assert len(result["measurementInvariance"]["comparisons"]) == 3
    assert result["measurementInvariance"]["selectedLevel"] in {
        "metric",
        "scalar",
        "strict",
    }
    assert {model["modelType"] for model in result["competingModels"]} == {
        "clpm",
        "ri_clpm",
    }
    assert len([path for path in result["paths"] if path["pathType"] == "cross_lagged"]) == 4


def test_ordinal_latent_panel_uses_wlsmv_threshold_invariance() -> None:
    settings = get_settings()
    root = settings.project_root
    request = _latent_panel_request("clpm")
    panel_request = request["longitudinal_panel"]
    assert isinstance(panel_request, dict)
    panel_request.update(
        {
            "indicator_scale": "ordinal",
            "estimator": "WLSMV",
            "missing": "complete_cases",
            "invariance_level": "scalar",
            "compare_competing_models": False,
            "run_robustness_checks": False,
        }
    )
    panel = EmpiricalAnalysisRequest.model_validate(request).longitudinal_panel
    assert panel is not None
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
    item_ids <- unique(unlist(lapply(input$waves, function(wave) {
      c(unlist(wave$xItemIds), unlist(wave$yItemIds))
    })))
    for (id in item_ids) {
      ranks <- rank(data[[id]], ties.method = "average", na.last = "keep")
      data[[id]] <- pmax(1L, pmin(5L, ceiling(5 * ranks / sum(!is.na(ranks)))))
    }
    result <- fit_longitudinal_panel(data, input, function(id) id)
    write_json(result, commandArgs(trailingOnly = TRUE)[6], auto_unbox = TRUE, null = "null")
    """
    with tempfile.TemporaryDirectory(prefix="rp-ordinal-panel-test-") as temporary:
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
                str(root / "engine/R/lib/longitudinal_lcm_sr.R"),
                str(root / "engine/R/lib/longitudinal_latent.R"),
                str(root / "engine/R/lib/longitudinal_panel.R"),
                str(spec_path),
                str(root / "samples/data/longitudinal-panel-demo.csv"),
                str(output_path),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else None
        )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    invariance = result["measurementInvariance"]
    assert invariance["indicatorScale"] == "ordinal"
    assert [row["level"] for row in invariance["models"]] == [
        "configural",
        "metric",
        "scalar",
    ]
    assert invariance["selectedLevel"] in {"metric", "scalar"}
