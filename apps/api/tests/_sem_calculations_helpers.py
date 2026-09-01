from __future__ import annotations

from starlette.testclient import TestClient

from app.main import app

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def _ensure_independent_context(dataset: dict) -> dict:
    project_id = dataset["projectId"]
    current = client.get(f"/api/v1/projects/{project_id}/study-context")
    expected_revision = current.json()["revision"] if current.status_code == 200 else None
    saved = client.put(
        f"/api/v1/projects/{project_id}/study-context",
        json={
            "expectedRevision": expected_revision,
            "context": {
                "schemaVersion": "1.0.0",
                "timeStructure": "cross_sectional",
                "dependenceStructure": "independent",
                "design": "observational",
            },
        },
    )
    assert saved.status_code == 200, saved.text
    resolved = client.get(
        f"/api/v1/datasets/{dataset['id']}/resolved-analysis-context"
    )
    assert resolved.status_code == 200, resolved.text
    return resolved.json()


def _context_refs(dataset: dict) -> dict:
    context = _ensure_independent_context(dataset)
    return {
        "contextHash": context["contextHash"],
        "datasetSha256": context["dataset"]["sha256"],
        "sampleVersionId": context["sample"]["id"],
        "sampleHash": context["sample"]["hash"],
        "structureVersionId": context["structure"]["id"] if context.get("structure") else None,
        "structureHash": context["structure"]["hash"] if context.get("structure") else None,
        "measurementVersionId": context["measurement"]["id"] if context.get("measurement") else None,
        "measurementHash": context["measurement"]["hash"] if context.get("measurement") else None,
    }


def _sem_spec(
    dataset,
    measurement,
    estimator: str = "ML",
    group_variable: str | None = "group",
    invariance: bool = True,
) -> dict:
    item_ids = {variable["originalName"]: variable["id"] for variable in dataset["variables"]}
    spec_dict = {
        "schemaVersion": "0.3.0",
        "modelId": "sem_test_model",
        "name": "SEM Test Model",
        "description": "SEM Test Model Description",
        "datasetVersionId": measurement["derivedDataset"]["id"],
        "design": {
            "timeStructure": "cross_sectional",
            "clustering": "none",
            "claimMode": "associational",
        },
        "nodes": [
            {
                "id": "latent_f1",
                "label": "Factor1",
                "kind": "latent",
                "role": "x",
                "dataType": "continuous",
            },
            {
                "id": "latent_f2",
                "label": "Factor2",
                "kind": "latent",
                "role": "m",
                "dataType": "continuous",
            },
            {
                "id": "latent_f3",
                "label": "Factor3",
                "kind": "latent",
                "role": "y",
                "dataType": "continuous",
            },
            {
                "id": "age",
                "variableId": item_ids["age"],
                "label": "Age",
                "kind": "observed",
                "role": "covariate",
                "dataType": "continuous",
            },
            {
                "id": "group",
                "variableId": item_ids["group"],
                "label": "Group",
                "kind": "observed",
                "role": "w",
                "dataType": "binary",
            },
        ],
        "edges": [
            {"id": "edge_f1_f2", "from": "latent_f1", "to": "latent_f2", "kind": "regression"},
            {"id": "edge_f2_f3", "from": "latent_f2", "to": "latent_f3", "kind": "regression"},
        ],
        "moderations": [],
        "covariates": [{"nodeId": "age", "outcomeNodeIds": ["latent_f2", "latent_f3"]}],
        "latents": [
            {"id": "latent_f1", "name": "Factor1", "indicators": [item_ids["x1"], item_ids["x2"]]},
            {"id": "latent_f2", "name": "Factor2", "indicators": [item_ids["m1"], item_ids["m2"]]},
            {"id": "latent_f3", "name": "Factor3", "indicators": [item_ids["y1"], item_ids["y2"]]},
        ],
        "estimation": {
            "family": "sem",
            "estimator": estimator,
            "groupVariableId": group_variable,
            "invariance": invariance,
            "standardErrors": "standard",
            "confidenceLevel": 0.95,
            "bootstrap": {
                "enabled": False,
                "replicates": 1000,
                "method": "percentile",
                "seed": 12345,
            },
            "missing": "complete_cases_per_model",
            "centering": {"method": "none", "nodeIds": []},
            "reportScale": "unstandardized_primary",
        },
    }
    spec_dict.update(_context_refs(dataset))
    return spec_dict
