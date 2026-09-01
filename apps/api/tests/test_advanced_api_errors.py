from __future__ import annotations

from io import BytesIO

from starlette.testclient import TestClient

from app.main import app
from app.services.advanced_jobs import AdvancedQueueFullError
from app.services.advanced_runner import AdvancedExecutionError

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def _power_spec() -> dict[str, object]:
    return {
        "schemaVersion": "0.1.0",
        "analysisId": "power_error_paths",
        "name": "Power error paths",
        "family": "power_analysis",
        "confidenceLevel": 0.95,
        "seed": 20260729,
        "designFamily": "regression",
        "method": "analytic",
        "solveFor": "sample_size",
        "alpha": 0.05,
        "targetPower": 0.8,
        "effectSize": {"metric": "cohens_f2", "value": 0.15},
        "predictors": 3,
        "groups": 1,
        "simulations": 5000,
    }


def _dataset() -> tuple[str, dict[str, str]]:
    response = client.post(
        "/api/v1/datasets/import",
        files={
            "file": (
                "advanced-errors.csv",
                BytesIO(b"x,y,z\n1,2,2\n2,,4\n3,5,6\n4,7,8\n5,9,10\n"),
                "text/csv",
            )
        },
    )
    assert response.status_code == 201
    payload = response.json()
    variables = {
        variable["originalName"]: variable["id"] for variable in payload["variables"]
    }
    return payload["id"], variables


def test_unknown_advanced_jobs_return_not_found_for_all_read_and_mutation_routes() -> None:
    for method, path in (
        ("get", "/api/v1/advanced-analyses/advanced_missing"),
        ("get", "/api/v1/advanced-analyses/advanced_missing/result"),
        ("get", "/api/v1/advanced-analyses/advanced_missing/export"),
        ("delete", "/api/v1/advanced-analyses/advanced_missing"),
    ):
        response = getattr(client, method)(path)
        assert response.status_code == 404


def test_start_rejects_missing_dataset_and_non_executable_slice() -> None:
    missing_dataset_spec = {
        "schemaVersion": "0.1.0",
        "analysisId": "mi_missing_dataset",
        "name": "MI missing dataset",
        "family": "multiple_imputation",
        "datasetVersionId": "dataset_missing",
        "confidenceLevel": 0.95,
        "seed": 20260729,
        "method": "mice_fcs",
        "imputations": 5,
        "iterations": 5,
        "variables": [{"variableId": "variable_x", "method": "pmm"}],
        "pooling": "none",
    }
    response = client.post(
        "/api/v1/advanced-analyses",
        json={"datasetId": "dataset_missing", "spec": missing_dataset_spec},
    )
    assert response.status_code == 404

    dataset_id, variable = _dataset()
    unsupported_slice = {
        **missing_dataset_spec,
        "analysisId": "mi_passive_not_restored",
        "datasetVersionId": dataset_id,
        "variables": [
            {
                "variableId": variable["y"],
                "method": "pmm",
                "predictorIds": [variable["x"]],
            }
        ],
        "passiveRules": [
            {
                "targetVariableId": variable["z"],
                "expression": f"{variable['x']} * {variable['y']}",
            }
        ],
    }
    response = client.post(
        "/api/v1/advanced-analyses",
        json={"datasetId": dataset_id, "spec": unsupported_slice},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ANALYSIS_CONTEXT_REQUIRED"


def test_advanced_route_translates_queue_execution_and_result_state_errors(
    monkeypatch,
) -> None:
    manager = app.state.services.advanced_job_manager

    def queue_full(_spec):
        raise AdvancedQueueFullError("queue full")

    monkeypatch.setattr(manager, "start", queue_full)
    queued = client.post(
        "/api/v1/advanced-analyses",
        json={"datasetId": None, "spec": _power_spec()},
    )
    assert queued.status_code == 429

    def execution_error(_spec):
        raise AdvancedExecutionError(
            "INVALID_POWER_CONFIGURATION",
            "invalid power configuration",
            "field=effectSize",
        )

    monkeypatch.setattr(manager, "start", execution_error)
    invalid = client.post(
        "/api/v1/advanced-analyses",
        json={"datasetId": None, "spec": _power_spec()},
    )
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "INVALID_POWER_CONFIGURATION"

    def result_unavailable(_run_id):
        raise ValueError("result unavailable")

    monkeypatch.setattr(manager, "get_result", result_unavailable)
    result = client.get("/api/v1/advanced-analyses/advanced_pending/result")
    assert result.status_code == 409
