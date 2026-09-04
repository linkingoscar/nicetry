from __future__ import annotations

from starlette.testclient import TestClient

from app.main import app

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def _document(analysis_id: str, title: str = "描述统计") -> dict[str, object]:
    return {
        "id": analysis_id,
        "projectId": "default",
        "title": title,
        "methodId": "empirical.overview.descriptives",
        "categoryId": "descriptives-relations",
        "source": "empirical",
        "datasetVersionId": "dataset_index_demo",
        "measurementVersionId": None,
        "procedure": "descriptives",
        "createdAt": "2026-09-04T00:00:00+00:00",
        "updatedAt": "2026-09-04T00:00:00+00:00",
        "currentDraftId": f"draft_{analysis_id}",
        "pinned": False,
    }


def test_analysis_index_persists_document_run_and_primary_result() -> None:
    analysis_id = "analysis_index_primary"
    run_id = "run_index_primary"
    created = client.put(
        f"/api/v1/projects/default/analysis-documents/{analysis_id}",
        json=_document(analysis_id),
    )
    assert created.status_code == 200, created.text

    registered = client.post(
        "/api/v1/projects/default/analysis-runs",
        json={
            "runId": run_id,
            "analysisId": analysis_id,
            "source": "empirical",
            "methodId": "empirical.overview.descriptives",
            "label": "描述统计",
            "categoryId": "descriptives-relations",
            "procedure": "descriptives",
            "datasetVersionId": "dataset_index_demo",
            "measurementVersionId": None,
            "status": "succeeded",
            "reportId": "empirical_index_primary",
            "createdAt": "2026-09-04T00:01:00+00:00",
        },
    )
    assert registered.status_code == 200, registered.text

    patched = client.patch(
        f"/api/v1/projects/default/analysis-documents/{analysis_id}",
        json={"title": "主要描述统计", "pinned": True, "primaryRunId": run_id},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["primaryRunId"] == run_id

    index = client.get("/api/v1/projects/default/analysis-index")
    assert index.status_code == 200, index.text
    body = index.json()
    document = next(item for item in body["documents"] if item["id"] == analysis_id)
    run = next(item for item in body["runs"] if item["id"] == run_id)
    assert document["title"] == "主要描述统计"
    assert document["pinned"] is True
    assert document["latestRunId"] == run_id
    assert document["primaryRunId"] == run_id
    assert run["analysisId"] == analysis_id
    assert run["reportId"] == "empirical_index_primary"


def test_analysis_index_rejects_primary_run_from_another_document() -> None:
    left = "analysis_index_left"
    right = "analysis_index_right"
    run_id = "run_index_right"
    assert client.put(
        f"/api/v1/projects/default/analysis-documents/{left}", json=_document(left, "左侧")
    ).status_code == 200
    assert client.put(
        f"/api/v1/projects/default/analysis-documents/{right}", json=_document(right, "右侧")
    ).status_code == 200
    assert client.post(
        "/api/v1/projects/default/analysis-runs",
        json={
            "runId": run_id,
            "analysisId": right,
            "source": "empirical",
            "methodId": "empirical.overview.descriptives",
            "label": "右侧",
            "procedure": "descriptives",
            "datasetVersionId": "dataset_index_demo",
            "measurementVersionId": None,
            "createdAt": "2026-09-04T00:02:00+00:00",
        },
    ).status_code == 200

    response = client.patch(
        f"/api/v1/projects/default/analysis-documents/{left}",
        json={"primaryRunId": run_id},
    )
    assert response.status_code == 422
    assert "必须属于当前" in response.text


def test_analysis_index_routes_are_internal_and_do_not_drift_generated_openapi() -> None:
    schema = client.get("/api/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/projects/{project_id}/analysis-index" not in paths
    assert "/api/v1/projects/{project_id}/analysis-documents/{analysis_id}" not in paths
    assert "/api/v1/projects/{project_id}/analysis-runs" not in paths
