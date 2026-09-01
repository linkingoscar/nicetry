from __future__ import annotations

import re
from io import BytesIO

import pandas as pd
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.measurement import MeasurementError, _validate_omega_work_budget
from app.settings import get_settings

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def test_omega_item_deletion_budget_rejects_pathological_construct() -> None:
    _validate_omega_work_budget(10)
    with pytest.raises(MeasurementError, match="工作单元"):
        _validate_omega_work_budget(100)


def _confirmed_scale_dataset() -> dict:
    payload = ("respondent_id,q1,q2,q3\n1,1,5,1\n2,2,4,2\n3,3,,3\n4,4,2,4\n5,5,1,\n").encode(
        "utf-8"
    )
    response = client.post(
        "/api/v1/datasets/import",
        files={"file": ("measurement.csv", BytesIO(payload), "text/csv")},
    )
    assert response.status_code == 201, response.text
    dataset = response.json()
    updates = [
        {
            "id": variable["id"],
            "confirmed_type": "id" if variable["originalName"] == "respondent_id" else "likert",
        }
        for variable in dataset["variables"]
    ]
    confirmed = client.put(
        f"/api/v1/datasets/{dataset['id']}/dictionary",
        json={"variables": updates},
    )
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()


def _measurement_request(dataset: dict, minimum_valid_proportion: float = 0.8) -> dict:
    item_ids = {variable["originalName"]: variable["id"] for variable in dataset["variables"]}
    return {
        "constructs": [
            {
                "id": "construct_wellbeing",
                "name": "幸福感",
                "item_ids": [item_ids["q1"], item_ids["q2"], item_ids["q3"]],
                "reverse_item_ids": [item_ids["q2"]],
                "theoretical_minimum": 1,
                "theoretical_maximum": 5,
                "aggregation": "mean",
                "minimum_valid_proportion": minimum_valid_proportion,
            }
        ]
    }


def test_measurement_scores_reverse_items_and_persists_derived_version() -> None:
    dataset = _confirmed_scale_dataset()
    settings = get_settings()
    normalized_path = settings.state_root / dataset["storage"]["normalized"]
    source_before = pd.read_parquet(normalized_path)

    response = client.put(
        f"/api/v1/datasets/{dataset['id']}/measurement",
        json=_measurement_request(dataset),
    )

    assert response.status_code == 200, response.text
    measurement = response.json()
    assert measurement["version"] == 1
    assert measurement["status"] == "ready_for_model_canvas"
    assert measurement["constructs"][0]["minimumValidItems"] == 3
    assert re.fullmatch(r"[a-f0-9]{64}", measurement["derivedDataset"]["sha256"])
    scores = [row["scale_wellbeing"] for row in measurement["transformationPreview"]]
    assert scores == [1.0, 2.0, None, 4.0, None]

    report = measurement["reports"][0]
    assert report["completeCaseCount"] == 3
    assert report["alpha"] == pytest.approx(1.0)
    assert report["omega"] == pytest.approx(1.0, abs=1e-5)
    assert report["scoreDistribution"]["validCount"] == 3
    assert report["itemAnalysis"][1]["reversed"] is True
    assert report["itemAnalysis"][1]["correctedItemTotalCorrelation"] == pytest.approx(1.0)

    derived_path = settings.state_root / measurement["derivedDataset"]["storage"]
    derived = pd.read_parquet(derived_path)
    assert derived["scale_wellbeing"].tolist()[:2] == [1.0, 2.0]
    pd.testing.assert_frame_equal(pd.read_parquet(normalized_path), source_before)

    latest = client.get(f"/api/v1/datasets/{dataset['id']}/measurement")
    assert latest.status_code == 200
    assert latest.json()["id"] == measurement["id"]


def test_measurement_rule_change_creates_new_version_and_allows_partial_rows() -> None:
    dataset = _confirmed_scale_dataset()
    first = client.put(
        f"/api/v1/datasets/{dataset['id']}/measurement",
        json=_measurement_request(dataset),
    )
    second = client.put(
        f"/api/v1/datasets/{dataset['id']}/measurement",
        json=_measurement_request(dataset, minimum_valid_proportion=2 / 3),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["version"] == 2
    scores = [row["scale_wellbeing"] for row in second.json()["transformationPreview"]]
    assert scores == [1.0, 2.0, 3.0, 4.0, 5.0]


def test_measurement_rejects_sample_values_outside_confirmed_theoretical_range() -> None:
    dataset = _confirmed_scale_dataset()
    request = _measurement_request(dataset)
    request["constructs"][0]["theoretical_maximum"] = 4

    response = client.put(f"/api/v1/datasets/{dataset['id']}/measurement", json=request)

    assert response.status_code == 422
    assert "超出理论范围" in response.json()["detail"]["message"]


def test_removing_an_existing_item_requires_a_version_note() -> None:
    dataset = _confirmed_scale_dataset()
    initial = _measurement_request(dataset)
    assert (
        client.put(f"/api/v1/datasets/{dataset['id']}/measurement", json=initial).status_code == 200
    )
    revised = _measurement_request(dataset)
    revised["constructs"][0]["item_ids"] = revised["constructs"][0]["item_ids"][:2]

    rejected = client.put(f"/api/v1/datasets/{dataset['id']}/measurement", json=revised)
    assert rejected.status_code == 422
    assert "必须填写版本说明" in rejected.json()["detail"]["message"]

    revised["change_note"] = "第三题内容与构念定义不一致，结合项目分析后删除。"
    accepted = client.put(f"/api/v1/datasets/{dataset['id']}/measurement", json=revised)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["version"] == 2
    assert accepted.json()["changeNote"].startswith("第三题")
