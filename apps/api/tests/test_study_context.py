from __future__ import annotations

from starlette.testclient import TestClient

from app.main import app

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def test_project_study_context_is_versioned_and_persistent() -> None:
    context = {
        "schemaVersion": "1.0.0",
        "timeStructure": "cross_sectional",
        "dependenceStructure": "nested",
        "design": "observational",
    }
    first = client.put("/api/v1/projects/context-test/study-context", json=context)
    assert first.status_code == 200
    assert first.json()["revision"] == 1

    second = client.put(
        "/api/v1/projects/context-test/study-context",
        json={**context, "design": "quasi_experimental"},
    )
    assert second.status_code == 200
    assert second.json()["revision"] == 2
    restored = client.get("/api/v1/projects/context-test/study-context")
    assert restored.json()["design"] == "quasi_experimental"


def test_dataset_structure_requires_roles_and_binds_known_variables() -> None:
    demo = client.post("/api/v1/demo/load").json()
    dataset = demo["dataset"]
    variable_ids = [variable["id"] for variable in dataset["variables"]]
    context = {
        "schemaVersion": "1.0.0",
        "timeStructure": "panel",
        "dependenceStructure": "nested",
        "design": "observational",
    }
    missing = client.put(
        f"/api/v1/datasets/{dataset['id']}/study-structure",
        json={"context": context},
    )
    assert missing.status_code == 422
    assert "DATA_STRUCTURE_ROLES_REQUIRED" in missing.text

    unknown = client.put(
        f"/api/v1/datasets/{dataset['id']}/study-structure",
        json={
            "context": context,
            "subjectId": variable_ids[0],
            "timeId": variable_ids[1],
            "clusterId": "unknown_variable",
        },
    )
    assert unknown.status_code == 422
    assert "DATA_STRUCTURE_UNKNOWN_VARIABLES" in unknown.text

    saved = client.put(
        f"/api/v1/datasets/{dataset['id']}/study-structure",
        json={
            "context": context,
            "subjectId": variable_ids[0],
            "timeId": variable_ids[1],
            "clusterId": variable_ids[2],
            "overrideReason": "已检查聚类数量与个体重复测量结构，后续报告将披露小聚类数带来的推断限制。",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["revision"] == 1
    assert saved.json()["clusterId"] == variable_ids[2]
