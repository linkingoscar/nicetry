from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.settings import get_settings

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def _await_empirical_report(response):
    assert response.status_code == 202, response.text
    run_id = response.json()["id"]
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        state_response = client.get(f"/api/v1/analyses/{run_id}")
        assert state_response.status_code == 200, state_response.text
        state = state_response.json()
        if state["status"] in {"succeeded", "failed", "cancelled"}:
            assert state["status"] == "succeeded", state
            result_response = client.get(f"/api/v1/analyses/{run_id}/result")
            assert result_response.status_code == 200, result_response.text
            return result_response.json()
        time.sleep(0.05)
    raise AssertionError(f"实证任务 {run_id} 未在 60 秒内完成")


def test_cfa_vs_lavaan_cross_validation() -> None:
    settings = get_settings()

    # 1. Load HolzingerSwineford1939 dataset from lavaan using Rscript
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "hs1939.csv"
        output_json_path = Path(tmpdir) / "lavaan_output.json"
        r_script_path = Path(tmpdir) / "build_lavaan_reference.R"
        r_script = """
        library(lavaan)
        library(jsonlite)
        args <- commandArgs(trailingOnly = TRUE)
        write.csv(HolzingerSwineford1939, args[[1]], row.names = FALSE)
        model <- 'Visual =~ x1 + x2 + x3; Textual =~ x4 + x5 + x6; Speed =~ x7 + x8 + x9'
        fit <- cfa(model, data = HolzingerSwineford1939, estimator = 'ML')
        measures <- fitMeasures(fit)
        std_loadings <- standardizedSolution(fit)
        std_loadings <- std_loadings[std_loadings$op == '=~', ]
        out_list <- list(
          chiSquare = as.numeric(measures['chisq']),
          df = as.integer(measures['df']),
          pValue = as.numeric(measures['pvalue']),
          cfi = as.numeric(measures['cfi']),
          tli = as.numeric(measures['tli']),
          rmsea = as.numeric(measures['rmsea']),
          rmseaLower = as.numeric(measures['rmsea.ci.lower']),
          rmseaUpper = as.numeric(measures['rmsea.ci.upper']),
          srmr = as.numeric(measures['srmr']),
          loadings = lapply(seq_len(nrow(std_loadings)), function(i) list(
            indicator = std_loadings$rhs[i], std_all = std_loadings$est.std[i]
          ))
        )
        write_json(out_list, args[[2]], auto_unbox = TRUE, digits = 15)
        """
        r_script_path.write_text(r_script, encoding="utf-8")

        env = os.environ.copy()
        env["R_LIBS_USER"] = settings.r_library_path.as_posix()
        env["LC_ALL"] = "English_United States.utf8"
        subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(r_script_path),
                str(csv_path),
                str(output_json_path),
            ],
            cwd=str(settings.project_root),
            env=env,
            check=True,
            capture_output=True,
        )

        assert csv_path.exists()
        assert output_json_path.exists()
        lavaan_metrics = json.loads(output_json_path.read_text(encoding="utf-8"))

        # 2. Import dataset into ResearchPath
        with open(csv_path, "rb") as f:
            imported = client.post(
                "/api/v1/datasets/import",
                files={"file": ("hs1939.csv", f, "text/csv")},
            )
        assert imported.status_code == 201, imported.text
        dataset = imported.json()

        # 3. Confirm dictionary variables (x1-x9 are likert/continuous)
        updates = [
            {
                "id": variable["id"],
                "confirmed_type": "likert"
                if variable["originalName"] in [f"x{i}" for i in range(1, 10)]
                else "id"
                if variable["originalName"] == "id"
                else "continuous",
            }
            for variable in dataset["variables"]
        ]

        confirmed = client.put(
            f"/api/v1/datasets/{dataset['id']}/dictionary",
            json={"variables": updates},
        )
        assert confirmed.status_code == 200, confirmed.text
        dataset = confirmed.json()

        # 4. Define measurement constructs (visual, textual, speed)
        var_by_name = {v["originalName"]: v["id"] for v in dataset["variables"]}
        constructs = [
            {
                "id": "construct_visual",
                "name": "Visual",
                "item_ids": [var_by_name["x1"], var_by_name["x2"], var_by_name["x3"]],
                "reverse_item_ids": [],
                "theoretical_minimum": 0,
                "theoretical_maximum": 20,
                "aggregation": "mean",
                "minimum_valid_proportion": 0.8,
            },
            {
                "id": "construct_textual",
                "name": "Textual",
                "item_ids": [var_by_name["x4"], var_by_name["x5"], var_by_name["x6"]],
                "reverse_item_ids": [],
                "theoretical_minimum": 0,
                "theoretical_maximum": 20,
                "aggregation": "mean",
                "minimum_valid_proportion": 0.8,
            },
            {
                "id": "construct_speed",
                "name": "Speed",
                "item_ids": [var_by_name["x7"], var_by_name["x8"], var_by_name["x9"]],
                "reverse_item_ids": [],
                "theoretical_minimum": 0,
                "theoretical_maximum": 20,
                "aggregation": "mean",
                "minimum_valid_proportion": 0.8,
            },
        ]

        measured = client.put(
            f"/api/v1/datasets/{dataset['id']}/measurement",
            json={"constructs": constructs},
        )
        assert measured.status_code == 200, measured.text
        measurement = measured.json()

        # 5. Run empirical analysis to get handwritten CFA results
        empirical_response = client.post(
            f"/api/v1/datasets/{dataset['id']}/measurements/{measurement['version']}/empirical-analysis",
            json={
                "factor_count": 3,
                "predictor_variable_ids": [
                    measurement["derivedDataset"]["scoreVariables"][0]["id"],
                    measurement["derivedDataset"]["scoreVariables"][1]["id"],
                    measurement["derivedDataset"]["scoreVariables"][2]["id"],
                ],
            },
        )
        empirical_report = _await_empirical_report(empirical_response)

        cfa_results = empirical_report["cfa"]
        assert cfa_results["available"] is True

        # 6. Assert equivalence of fit indices within 1e-5 tolerance
        tol = 1e-5
        fit_hand = cfa_results
        fit_lav = lavaan_metrics

        assert fit_hand["chiSquare"] == pytest.approx(fit_lav["chiSquare"], abs=tol)
        assert fit_hand["degreesOfFreedom"] == fit_lav["df"]
        assert fit_hand["pValue"] == pytest.approx(fit_lav["pValue"], abs=tol)
        assert fit_hand["cfi"] == pytest.approx(fit_lav["cfi"], abs=tol)
        assert fit_hand["tli"] == pytest.approx(fit_lav["tli"], abs=tol)
        assert fit_hand["rmsea"] == pytest.approx(fit_lav["rmsea"], abs=tol)
        assert fit_hand["rmseaCiLower"] == pytest.approx(fit_lav["rmseaLower"], abs=tol)
        assert fit_hand["rmseaCiUpper"] == pytest.approx(fit_lav["rmseaUpper"], abs=tol)
        assert fit_hand["srmr"] == pytest.approx(fit_lav["srmr"], abs=tol)

        # 7. Assert equivalence of factor loadings
        loadings_hand = dict(zip(cfa_results["itemIds"], cfa_results["standardizedLoadings"]))
        loadings_lav = {
            var_by_name[loading["indicator"]]: loading["std_all"] for loading in fit_lav["loadings"]
        }

        for key, val_lav in loadings_lav.items():
            val_hand = loadings_hand[key]
            assert val_hand == pytest.approx(val_lav, abs=tol)

        print("CFA and lavaan cross-validation passed successfully with errors <= 10^-5!")
