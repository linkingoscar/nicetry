from __future__ import annotations

import csv

import numpy as np
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.settings import get_settings

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def _numpy_reference() -> tuple[float, float, float]:
    settings = get_settings()
    with settings.demo_data_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    x = np.array([float(row["var_autonomy"]) for row in rows])
    m = np.array([float(row["var_engagement"]) for row in rows])
    y = np.array([float(row["var_performance"]) for row in rows])

    a = np.linalg.lstsq(np.column_stack([np.ones(len(x)), x]), m, rcond=None)[0][1]
    y_coefficients = np.linalg.lstsq(np.column_stack([np.ones(len(x)), x, m]), y, rcond=None)[0]
    direct = y_coefficients[1]
    b = y_coefficients[2]
    return float(a), float(b), float(direct)


def test_health_reports_private_r_runtime() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["rAvailable"] is True
    assert isinstance(body["rExecutable"], bool)
    assert isinstance(body["diskFreeBytes"], int)
    assert body["diskFreeBytes"] > 0
    assert isinstance(body["diskFreePercent"], float)
    assert 0 <= body["diskFreePercent"] <= 100


def test_method_demo_data_downloads() -> None:
    longitudinal = client.get("/api/v1/demo/data/longitudinal")
    diary = client.get("/api/v1/demo/data/diary")
    esm = client.get("/api/v1/demo/data/esm")

    assert longitudinal.status_code == 200
    assert longitudinal.text.startswith("subject_id,age,group,x1,y1")
    assert diary.status_code == 200
    assert diary.text.startswith("person_id,day,age,intervention")
    assert esm.status_code == 200
    assert esm.text.startswith("person_id,occasion,emotion,ai_trust")


def test_demo_datasets_are_research_scale_and_have_expected_signal() -> None:
    settings = get_settings()
    with settings.demo_data_path.open("r", encoding="utf-8", newline="") as handle:
        mediation_rows = list(csv.DictReader(handle))
    with (
        settings.project_root / "samples" / "data" / "questionnaire-demo.csv"
    ).open("r", encoding="utf-8", newline="") as handle:
        questionnaire_rows = list(csv.DictReader(handle))

    assert len(mediation_rows) == 260
    assert len(questionnaire_rows) == 260
    assert abs(
        sum(row["group"] == "A" for row in questionnaire_rows)
        - sum(row["group"] == "B" for row in questionnaire_rows)
    ) <= 1

    mediation = np.array(
        [
            [
                float(row["var_autonomy"]),
                float(row["var_engagement"]),
                float(row["var_performance"]),
            ]
            for row in mediation_rows
        ]
    )
    assert np.corrcoef(mediation[:, 0], mediation[:, 1])[0, 1] > 0.45
    assert np.corrcoef(mediation[:, 1], mediation[:, 2])[0, 1] > 0.45

    item_values = [
        float(value)
        for row in questionnaire_rows
        for name, value in row.items()
        if "_" in name and name != "respondent_id" and value
    ]
    missing_items = sum(
        not value
        for row in questionnaire_rows
        for name, value in row.items()
        if "_" in name and name != "respondent_id"
    )
    assert all(1 <= value <= 5 and value.is_integer() for value in item_values)
    assert missing_items / (260 * 9) < 0.02


def test_demo_mediation_matches_independent_numpy_ols() -> None:
    demo = client.get("/api/v1/demo").json()
    response = client.post(
        "/api/v1/analyses/mediation",
        json={"dataset_id": demo["datasetId"], "model_spec": demo["modelSpec"]},
    )

    assert response.status_code == 200, response.text
    result = response.json()
    effects = {effect["label"]: effect for effect in result["effects"]}
    reference_a, reference_b, reference_direct = _numpy_reference()

    assert effects["a"]["estimate"] == pytest.approx(reference_a, abs=1e-8)
    assert effects["b"]["estimate"] == pytest.approx(reference_b, abs=1e-8)
    assert effects["c_prime"]["estimate"] == pytest.approx(reference_direct, abs=1e-8)
    assert effects["a_x_b"]["estimate"] == pytest.approx(reference_a * reference_b, abs=1e-8)
    assert result["sampleFlow"]["original"] == 260
    assert result["sampleFlow"]["selected"] == 260
    assert result["sampleFlow"]["included"] == 260
    assert result["sampleFlow"]["excluded"] == 0
    assert result["sampleFlow"]["missingRows"] == 0
    assert result["sampleFlow"]["finalN"] == 260
    assert result["sampleFlow"]["missingMethod"] == "complete_cases_per_model"
    interval = effects["a_x_b"]["confidenceInterval"]
    assert interval["lower"] < effects["a_x_b"]["estimate"] < interval["upper"]
    assert interval["replicates"] == 5000
    assert result["warnings"][0]["code"] == "CROSS_SECTIONAL_MEDIATION"


def test_load_demo_project() -> None:
    response = client.post("/api/v1/demo/load")
    assert response.status_code == 201, response.text
    payload = response.json()
    assert "dataset" in payload
    assert "measurement" in payload
    assert "modelSpec" in payload

    project_id = payload["dataset"]["projectId"]
    current = client.get(f"/api/v1/projects/{project_id}/study-context")
    context_response = client.put(
        f"/api/v1/projects/{project_id}/study-context",
        json={
            "expectedRevision": current.json()["revision"] if current.status_code == 200 else None,
            "context": {
                "schemaVersion": "1.0.0",
                "timeStructure": "cross_sectional",
                "dependenceStructure": "independent",
                "design": "observational",
            },
        },
    )
    assert context_response.status_code == 200, context_response.text
    resolved = client.get(
        f"/api/v1/datasets/{payload['dataset']['id']}/resolved-analysis-context"
    ).json()
    payload["modelSpec"].update(
        {
            "contextHash": resolved["contextHash"],
            "datasetSha256": resolved["dataset"]["sha256"],
            "sampleVersionId": resolved["sample"]["id"],
            "sampleHash": resolved["sample"]["hash"],
            "structureVersionId": resolved["structure"]["id"] if resolved.get("structure") else None,
            "structureHash": resolved["structure"]["hash"] if resolved.get("structure") else None,
            "measurementVersionId": resolved["measurement"]["id"] if resolved.get("measurement") else None,
            "measurementHash": resolved["measurement"]["hash"] if resolved.get("measurement") else None,
        }
    )

    # 1. Freeze model
    freeze_response = client.post(
        f"/api/v1/datasets/{payload['dataset']['id']}/models/{payload['modelSpec']['modelId']}/freeze",
        json={
            "model_spec": payload["modelSpec"],
            "override_reason": "演示项目自动忽略横截面警告。",
        },
    )
    assert freeze_response.status_code == 200, freeze_response.text
    frozen = freeze_response.json()

    # 2. Trigger analysis
    run_response = client.post(
        f"/api/v1/datasets/{payload['dataset']['id']}/models/{payload['modelSpec']['modelId']}/versions/{frozen['version']}/analysis"
    )
    assert run_response.status_code == 202, run_response.text
    run_id = run_response.json()["id"]

    # 3. Await analysis
    import time

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        state_response = client.get(f"/api/v1/analyses/{run_id}")
        assert state_response.status_code == 200, state_response.text
        state = state_response.json()
        if state["status"] in {"succeeded", "failed", "cancelled"}:
            assert state["status"] == "succeeded", state
            assert state["result"] is None

            res_response = client.get(f"/api/v1/analyses/{run_id}/result")
            assert res_response.status_code == 200, res_response.text
            result = res_response.json()
            assert "effects" in result
            assert "academicInterpretation" in result
            assert "apaTables" in result
            assert len(result["equations"]) > 0
            break
        time.sleep(0.25)
    else:
        from conftest import _test_state_root

        stdout_path = (
            _test_state_root / "projects" / "default" / "runs" / run_id / "work" / "stdout.log"
        )
        stderr_path = (
            _test_state_root / "projects" / "default" / "runs" / run_id / "work" / "stderr.log"
        )
        stdout_text = (
            stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else "NO STDOUT LOG"
        )
        stderr_text = (
            stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else "NO STDERR LOG"
        )
        print(f"STATE: {state}")
        print(f"STDOUT:\n{stdout_text}")
        print(f"STDERR:\n{stderr_text}")
        pytest.fail("Analysis timed out")


@pytest.mark.parametrize(
    ("time_structure", "filename"),
    [
        ("panel", "longitudinal-panel-demo.csv"),
        ("intensive_longitudinal", "daily-diary-demo.csv"),
    ],
)
def test_load_demo_project_matches_selected_time_structure(
    time_structure: str,
    filename: str,
) -> None:
    response = client.post(
        "/api/v1/demo/load",
        json={"timeStructure": time_structure},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["dataset"]["originalFile"]["name"] == filename
    assert payload["dataset"]["dictionary"]["status"] == "confirmed"
    assert payload["measurement"]["datasetVersionId"] == payload["dataset"]["id"]
    assert payload["modelSpec"]["design"]["timeStructure"] == time_structure
