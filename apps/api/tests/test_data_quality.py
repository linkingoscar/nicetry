from __future__ import annotations

from io import BytesIO

from starlette.testclient import TestClient

from app.main import app

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def test_data_quality_and_analysis_sample_are_auditable() -> None:
    payload = (
        "response_id,duration_seconds,attention,item_1,item_2,comment,structural\n"
        "R1,120,3,1,1,认真回答,\n"
        "R2,12,2,1,1,认真回答,\n"
        "R2,130,3,5,5,重复回答,1\n"
        "R4,95,3,2,3,,\n"
    ).encode("utf-8")
    response = client.post(
        "/api/v1/datasets/import",
        files={"file": ("quality-fixture.csv", BytesIO(payload), "text/csv")},
    )
    assert response.status_code == 201, response.text
    dataset = response.json()
    variable_ids = {item["originalName"]: item["id"] for item in dataset["variables"]}

    quality_response = client.post(
        f"/api/v1/datasets/{dataset['id']}/quality-runs",
        json={
            "qualityVariableIds": [variable_ids["item_1"], variable_ids["item_2"]],
            "responseIdVariableId": variable_ids["response_id"],
            "durationVariableId": variable_ids["duration_seconds"],
            "textVariableIds": [variable_ids["comment"]],
            "structuralMissingVariableIds": [variable_ids["structural"]],
            "attentionChecks": [
                {
                    "variableId": variable_ids["attention"],
                    "expectedValue": 3,
                    "label": "instruction check",
                }
            ],
        },
    )
    assert quality_response.status_code == 201, quality_response.text
    quality = quality_response.json()
    assert quality["rowCount"] == 4
    assert quality["metrics"]["duplicateResponseId"]["duplicateRowCount"] == 2
    assert quality["metrics"]["attentionChecks"]["failedRowCount"] == 1
    assert quality["metrics"]["text"]["duplicateRowCount"] == 2

    cases_response = client.get(
        f"/api/v1/datasets/{dataset['id']}/quality-runs/{quality['id']}/cases?limit=10"
    )
    assert cases_response.status_code == 200
    cases = cases_response.json()
    assert cases["total"] == 4
    assert cases["items"][1]["relativeDuration"] < 0.5

    sample_response = client.post(
        f"/api/v1/datasets/{dataset['id']}/sample-versions",
        json={
            "qualityRunId": quality["id"],
            "combineOperator": "or",
            "label": "主分析样本",
            "rules": [
                {
                    "id": "rule_speed",
                    "metric": "duration_seconds",
                    "operator": "lt",
                    "threshold": 30,
                    "source": "preregistered_primary",
                    "description": "答题时长低于 30 秒",
                },
                {
                    "id": "rule_attention",
                    "metric": "attention_check_failed",
                    "operator": "eq",
                    "threshold": True,
                    "source": "preregistered_primary",
                    "description": "注意力检查失败",
                },
            ],
        },
    )
    assert sample_response.status_code == 201, sample_response.text
    sample = sample_response.json()
    assert sample["rowCount"] == 4
    assert sample["excludedCount"] == 1
    assert len(sample["sampleHash"]) == 64

    sample_cases_response = client.get(
        f"/api/v1/datasets/{dataset['id']}/sample-versions/{sample['id']}/cases?limit=10"
    )
    assert sample_cases_response.status_code == 200
    sample_cases = sample_cases_response.json()["items"]
    assert sample_cases[1]["included"] is False
    assert "rule_speed" in sample_cases[1]["matchedRuleIds"]

    changed_sample_response = client.post(
        f"/api/v1/datasets/{dataset['id']}/sample-versions",
        json={
            "qualityRunId": quality["id"],
            "combineOperator": "or",
            "label": "主分析样本（敏感性）",
            "rules": [
                {
                    "id": "rule_speed_changed",
                    "metric": "duration_seconds",
                    "operator": "lt",
                    "threshold": 31,
                    "source": "planned_not_preregistered",
                    "description": "敏感性时长阈值",
                }
            ],
        },
    )
    assert changed_sample_response.status_code == 201, changed_sample_response.text
    assert changed_sample_response.json()["sampleHash"] != sample["sampleHash"]

    paginated_runs = client.get(
        f"/api/v1/datasets/{dataset['id']}/quality-runs?offset=0&limit=1"
    )
    assert paginated_runs.status_code == 200
    assert len(paginated_runs.json()) == 1

    all_samples = client.get(f"/api/v1/datasets/{dataset['id']}/sample-versions")
    assert all_samples.status_code == 200
    all_sample_ids = {entry["id"] for entry in all_samples.json()}

    paginated_samples = client.get(
        f"/api/v1/datasets/{dataset['id']}/sample-versions?offset=1&limit=1"
    )
    assert paginated_samples.status_code == 200
    samples_page = paginated_samples.json()
    assert len(samples_page) == 1
    assert samples_page[0]["id"] in all_sample_ids
