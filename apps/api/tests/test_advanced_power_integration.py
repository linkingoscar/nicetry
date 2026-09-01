from __future__ import annotations

import json
import time
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from starlette.testclient import TestClient

from app.contracts import validate_contract
from app.main import app
from app.settings import get_settings

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def _request(spec: dict, dataset_id: str | None = None) -> dict:
    return {"datasetId": dataset_id, "spec": spec}


def _common(family: str, analysis_id: str) -> dict:
    return {
        "schemaVersion": "0.1.0",
        "analysisId": analysis_id,
        "name": analysis_id,
        "family": family,
        "confidenceLevel": 0.95,
        "seed": 20260714,
    }


def test_power_runner_returns_a_schema_valid_back_checked_result() -> None:
    spec = {
        **_common("power_analysis", "analysis_power_reserved"),
        "designFamily": "regression",
        "method": "analytic",
        "solveFor": "sample_size",
        "alpha": 0.05,
        "targetPower": 0.8,
        "effectSize": {"metric": "cohens_f2", "value": 0.15},
        "groups": 1,
        "predictors": 3,
        "simulations": 5000,
    }
    response = client.post("/api/v1/advanced-analyses", json=_request(spec))
    assert response.status_code == 202, response.text
    run_id = response.json()["id"]

    timeout = 10
    started = time.time()
    while True:
        status_response = client.get(f"/api/v1/advanced-analyses/{run_id}")
        assert status_response.status_code == 200
        status = status_response.json()["status"]
        if status in {"succeeded", "failed", "cancelled"}:
            break
        if time.time() - started > timeout:
            raise TimeoutError("Test timed out waiting for advanced job")
        time.sleep(0.5)

    assert status == "succeeded"
    result_response = client.get(f"/api/v1/advanced-analyses/{run_id}/result")
    assert result_response.status_code == 200
    result = result_response.json()

    validate_contract(result, get_settings().advanced_result_schema_path)
    assert result["run"]["family"] == "power_analysis"
    assert result["familyResult"]["solveFor"] == "sample_size"
    assert result["familyResult"]["solvedValue"] == 77
    assert result["familyResult"]["achievedPower"] >= 0.8

    exported = client.get(f"/api/v1/advanced-analyses/{run_id}/export")
    assert exported.status_code == 200, exported.text
    with ZipFile(BytesIO(exported.content)) as archive:
        names = set(archive.namelist())
        assert "README.md" in names
        assert "specification/advanced-spec.json" in names
        assert "result/advanced-result.json" in names
        assert "paper/report.md" in names
        assert "paper/tables.json" in names
        assert "reproduction/run_advanced_analysis.R" in names
        assert "data/analysis-data.parquet" not in names

    include_data = client.get(f"/api/v1/advanced-analyses/{run_id}/export?include_data=true")
    assert include_data.status_code == 409
    assert "没有数据版本" in include_data.text


def test_power_monte_carlo_runner_returns_a_schema_valid_result() -> None:
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "advanced"
        / "power"
        / "regression-monte-carlo.json"
    )
    spec = json.loads(fixture.read_text(encoding="utf-8"))
    response = client.post("/api/v1/advanced-analyses", json=_request(spec))
    assert response.status_code == 202, response.text
    run_id = response.json()["id"]

    started = time.time()
    while True:
        status_response = client.get(f"/api/v1/advanced-analyses/{run_id}")
        assert status_response.status_code == 200
        status = status_response.json()["status"]
        if status in {"succeeded", "failed", "cancelled"}:
            break
        if time.time() - started > 30:
            raise TimeoutError("Monte Carlo test timed out waiting for advanced job")
        time.sleep(0.5)

    assert status == "succeeded"
    result_response = client.get(f"/api/v1/advanced-analyses/{run_id}/result")
    assert result_response.status_code == 200
    result = result_response.json()
    validate_contract(result, get_settings().advanced_result_schema_path)
    family_result = result["familyResult"]
    assert family_result["method"] == "monte_carlo"
    assert family_result["simulationCount"] == 1000
    assert family_result["validSimulations"] == 1000
    assert family_result["failureCount"] == 0
    assert family_result["monteCarloStandardError"] >= 0
