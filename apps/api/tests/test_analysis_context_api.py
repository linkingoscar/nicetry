from __future__ import annotations

from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from app.advanced_contracts import PowerAnalysisSpec
from app.main import app
from app.services.analysis_context import AnalysisContextResolutionError
from app.services.model_service import validate_model_context
from app.study_context_contracts import DatasetStructureInput, StudyContextInput

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def test_study_context_expected_revision_is_idempotent_and_conflict_safe() -> None:
    project_id = "context-api-" + uuid4().hex[:8]
    context = {
        "schemaVersion": "1.0.0",
        "timeStructure": "cross_sectional",
        "dependenceStructure": "independent",
        "design": "observational",
    }
    first = client.put(
        f"/api/v1/projects/{project_id}/study-context",
        json={"expectedRevision": None, "context": context},
    )
    assert first.status_code == 200
    assert first.json()["revision"] == 1

    same = client.put(
        f"/api/v1/projects/{project_id}/study-context",
        json={"expectedRevision": 1, "context": context},
    )
    assert same.status_code == 200
    assert same.json()["id"] == first.json()["id"]

    changed = client.put(
        f"/api/v1/projects/{project_id}/study-context",
        json={
            "expectedRevision": 1,
            "context": {**context, "design": "randomized"},
        },
    )
    assert changed.status_code == 200
    assert changed.json()["revision"] == 2

    conflict = client.put(
        f"/api/v1/projects/{project_id}/study-context",
        json={"expectedRevision": 1, "context": context},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "REVISION_CONFLICT"


def test_structure_validation_and_version_save_use_context_version() -> None:
    dataset = client.post("/api/v1/demo/load").json()["dataset"]
    variables = [variable["id"] for variable in dataset["variables"]]
    project_id = dataset["projectId"]
    context = {
        "schemaVersion": "1.0.0",
        "timeStructure": "panel",
        "dependenceStructure": "independent",
        "design": "observational",
    }
    current_context = client.get(f"/api/v1/projects/{project_id}/study-context")
    expected_revision = (
        current_context.json()["revision"] if current_context.status_code == 200 else None
    )
    saved_context = client.put(
        f"/api/v1/projects/{project_id}/study-context",
        json={"expectedRevision": expected_revision, "context": context},
    )
    assert saved_context.status_code == 200
    context_id = saved_context.json()["id"]
    roles = {"subjectId": variables[0], "clusterId": None, "timeId": variables[1]}

    profile = client.post(
        f"/api/v1/datasets/{dataset['id']}/study-structure/validate",
        json={"studyContextVersionId": context_id, "roles": roles},
    )
    assert profile.status_code == 200
    assert profile.json()["status"] == "valid"
    assert len(profile.json()["proposedStructureHash"]) == 64

    structure = client.post(
        f"/api/v1/datasets/{dataset['id']}/study-structures",
        json={
            "expectedRevision": None,
            "studyContextVersionId": context_id,
            "roles": roles,
        },
    )
    assert structure.status_code == 201
    assert structure.json()["studyContextVersionId"] == context_id
    assert structure.json()["status"] == "valid"


def test_resolved_context_returns_deterministic_virtual_all_cases_sample() -> None:
    dataset = client.post("/api/v1/demo/load").json()["dataset"]
    response = client.get(f"/api/v1/datasets/{dataset['id']}/resolved-analysis-context")
    assert response.status_code == 200
    payload = response.json()
    assert payload["sample"]["id"] == f"sample_all_{dataset['originalFile']['sha256'][:16]}"
    assert payload["dataset"]["sha256"] == dataset["originalFile"]["sha256"]
    assert len(payload["contextHash"]) == 64
    assert payload["validity"] in {"ready", "incomplete"}

    mismatch = client.get(
        f"/api/v1/datasets/{dataset['id']}/resolved-analysis-context"
        "?sampleVersionId=sample_missing"
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "ARTIFACT_DATASET_MISMATCH"


def test_empirical_entry_rejects_a_stale_context_hash_before_queueing() -> None:
    dataset = client.post("/api/v1/demo/load").json()["dataset"]
    measurement = client.get(f"/api/v1/datasets/{dataset['id']}/measurement")
    assert measurement.status_code == 200
    response = client.post(
        f"/api/v1/datasets/{dataset['id']}/measurements/{measurement.json()['version']}/empirical-analysis",
        json={"context_hash": "0" * 64},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ANALYSIS_CONTEXT_CHANGED"


def test_context_bound_advanced_entry_rejects_stale_context_before_queueing() -> None:
    dataset = client.post("/api/v1/demo/load").json()["dataset"]
    project_id = dataset["projectId"]
    current_context = client.get(f"/api/v1/projects/{project_id}/study-context")
    context = {
        "schemaVersion": "1.0.0",
        "timeStructure": "cross_sectional",
        "dependenceStructure": "independent",
        "design": "observational",
    }
    saved_context = client.put(
        f"/api/v1/projects/{project_id}/study-context",
        json={
            "expectedRevision": current_context.json()["revision"] if current_context.status_code == 200 else None,
            "context": context,
        },
    )
    assert saved_context.status_code == 200
    current_structure = client.get(f"/api/v1/datasets/{dataset['id']}/study-structure")
    structure = client.post(
        f"/api/v1/datasets/{dataset['id']}/study-structures",
        json={
            "expectedRevision": current_structure.json()["revision"] if current_structure.status_code == 200 else None,
            "studyContextVersionId": saved_context.json()["id"],
            "roles": {"subjectId": None, "clusterId": None, "timeId": None},
        },
    )
    assert structure.status_code == 201
    resolved = client.get(f"/api/v1/datasets/{dataset['id']}/resolved-analysis-context").json()
    draft = client.post(
        f"/api/v1/datasets/{dataset['id']}/analysis-drafts",
        json={
            "sliceId": "power_analysis.analytic.regression",
            "contextHash": resolved["contextHash"],
        },
    )
    assert draft.status_code == 201
    spec = {
        "schemaVersion": "0.1.0",
        "analysisId": "context_power_demo",
        "name": "Context power demo",
        "family": "power_analysis",
        "datasetVersionId": dataset["id"],
        "contextHash": "0" * 64,
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
    response = client.post(
        "/api/v1/advanced-analyses",
        json={"datasetId": dataset["id"], "draftId": draft.json()["id"], "spec": spec},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ANALYSIS_CONTEXT_CHANGED"


def test_context_lineage_success_binds_model_advanced_and_panel_entries(monkeypatch) -> None:
    dataset = client.post("/api/v1/demo/load").json()["dataset"]
    variables = dataset["variables"]
    project_id = dataset["projectId"]
    current = client.get(f"/api/v1/projects/{project_id}/study-context")
    expected_revision = current.json()["revision"] if current.status_code == 200 else None
    context = client.put(
        f"/api/v1/projects/{project_id}/study-context",
        json={
            "expectedRevision": expected_revision,
            "context": {
                "schemaVersion": "1.0.0",
                "timeStructure": "panel",
                "dependenceStructure": "independent",
                "design": "observational",
            },
        },
    )
    assert context.status_code == 200
    roles = {"subjectId": variables[0]["id"], "clusterId": None, "timeId": variables[1]["id"]}
    structure = client.post(
        f"/api/v1/datasets/{dataset['id']}/study-structures",
        json={
            "expectedRevision": None,
            "studyContextVersionId": context.json()["id"],
            "roles": roles,
        },
    )
    assert structure.status_code == 201
    measurement = client.get(f"/api/v1/datasets/{dataset['id']}/measurement")
    assert measurement.status_code == 200
    resolved = client.get(f"/api/v1/datasets/{dataset['id']}/resolved-analysis-context").json()
    refs = {
        "contextHash": resolved["contextHash"],
        "sampleVersionId": resolved["sample"]["id"],
        "sampleHash": resolved["sample"]["hash"],
        "structureVersionId": resolved["structure"]["id"],
        "structureHash": resolved["structure"]["hash"],
        "measurementVersionId": resolved["measurement"]["id"],
        "measurementHash": resolved["measurement"]["hash"],
        "datasetSha256": resolved["dataset"]["sha256"],
    }

    with pytest.raises(AnalysisContextResolutionError, match="METHOD_NOT_APPLICABLE_TO_CONTEXT"):
        validate_model_context(
            dataset["id"],
            refs,
            app.state.services.analysis_context_service,
        )

    spec = PowerAnalysisSpec.model_validate(
        {
            "schemaVersion": "0.1.0",
            "analysisId": "context_power_success",
            "name": "Context power success",
            "family": "power_analysis",
            **refs,
            "designFamily": "regression",
            "method": "analytic",
            "solveFor": "sample_size",
            "effectSize": {"metric": "cohens_f2", "value": 0.15},
            "predictors": 3,
            "groups": 1,
            "simulations": 5000,
        }
    )
    advanced_lineage = app.state.services.advanced_job_manager._resolve_context_lineage(
        spec, dataset["id"]
    )
    assert advanced_lineage is not None
    assert advanced_lineage["measurementVersionId"] == refs["measurementVersionId"]

    manager = app.state.services.analysis_job_manager
    monkeypatch.setattr(
        manager,
        "_enqueue",
        lambda state, target, *args: state,
    )
    state = manager.start_empirical(
        dataset["id"],
        measurement.json()["version"],
        {"longitudinalPanel": {"subjectVariableId": roles["subjectId"]}},
    )
    assert state["contextLineage"]["contextHash"] == refs["contextHash"]
    assert state["contextLineage"]["structure"]["id"] == refs["structureVersionId"]


def test_analysis_draft_prefills_roles_and_rejects_stale_revision() -> None:
    dataset = client.post("/api/v1/demo/load").json()["dataset"]
    project_id = dataset["projectId"]
    variable_ids = {
        variable["originalName"]: variable["id"] for variable in dataset["variables"]
    }
    current_context = client.get(f"/api/v1/projects/{project_id}/study-context")
    expected_revision = (
        current_context.json()["revision"] if current_context.status_code == 200 else None
    )
    context = {
        "schemaVersion": "1.0.0",
        "timeStructure": "cross_sectional",
        "dependenceStructure": "nested",
        "design": "observational",
    }
    saved_context = client.put(
        f"/api/v1/projects/{project_id}/study-context",
        json={"expectedRevision": expected_revision, "context": context},
    )
    assert saved_context.status_code == 200
    structure = client.post(
        f"/api/v1/datasets/{dataset['id']}/study-structures",
        json={
            "expectedRevision": None,
            "studyContextVersionId": saved_context.json()["id"],
            "roles": {
                "subjectId": None,
                "clusterId": variable_ids["group"],
                "timeId": None,
            },
            "overrideReason": "演示数据 cluster 数量有限，继续进行方法绑定",
        },
    )
    assert structure.status_code == 201
    resolved = client.get(f"/api/v1/datasets/{dataset['id']}/resolved-analysis-context")
    assert resolved.status_code == 200
    context_hash = resolved.json()["contextHash"]

    created = client.post(
        f"/api/v1/datasets/{dataset['id']}/analysis-drafts",
        json={
            "sliceId": "multilevel_model.aggregation.icc_rwg",
            "contextHash": context_hash,
        },
    )
    assert created.status_code == 201
    draft = created.json()
    assert draft["validity"] == "ready"
    assert draft["spec"]["contextHash"] == context_hash
    assert draft["spec"]["roles"]["clusterId"] == variable_ids["group"]

    changed = client.put(
        f"/api/v1/analysis-drafts/{draft['id']}",
        json={
            "expectedRevision": 1,
            "spec": {},
            "roleOverrides": {
                "clusterId": {
                    "variableId": "missing",
                    "reason": "此覆盖不属于当前方法角色",
                }
            },
        },
    )
    assert changed.status_code == 409
    assert changed.json()["detail"]["code"] == "STRUCTURE_ROLE_INVALID"

    updated = client.put(
        f"/api/v1/analysis-drafts/{draft['id']}",
        json={
            "expectedRevision": 1,
            "spec": {"clusterVariableId": variable_ids["age"]},
            "roleOverrides": {
                "clusterId": {
                    "variableId": variable_ids["age"],
                    "reason": "已复核组内聚合单位，采用年龄分层作为敏感性结构。",
                }
            },
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"] == 2
    assert updated.json()["roleOverrides"]["clusterId"]["variableId"] == variable_ids["age"]
    assert updated.json()["spec"]["roles"]["clusterId"] == variable_ids["age"]

    revision_conflict = client.put(
        f"/api/v1/analysis-drafts/{draft['id']}",
        json={"expectedRevision": 1, "spec": {}},
    )
    assert revision_conflict.status_code == 409
    assert revision_conflict.json()["detail"]["code"] == "REVISION_CONFLICT"

    changed_context = client.put(
        f"/api/v1/projects/{project_id}/study-context",
        json={
            "expectedRevision": saved_context.json()["revision"],
            "context": {**context, "design": "randomized"},
        },
    )
    assert changed_context.status_code == 200
    refreshed = client.get(
        f"/api/v1/datasets/{dataset['id']}/resolved-analysis-context"
    )
    validity = client.get(f"/api/v1/analysis-drafts/{draft['id']}/validity")
    assert validity.status_code == 200
    assert validity.json()["validity"] == "stale"
    assert "ANALYSIS_CONTEXT_CHANGED" in validity.json()["invalidationReasons"]
    invalidation = validity.json()["invalidation"]
    assert "研究上下文版本发生变化" in invalidation["upstreamChanges"]
    assert "该分析草稿及其派生运行结果" in invalidation["affectedObjects"]
    assert invalidation["historyStatus"] == "available"
    assert invalidation["requiredAction"] == "rerun"
    replacement = client.post(
        f"/api/v1/datasets/{dataset['id']}/analysis-drafts",
        json={
            "sliceId": "multilevel_model.aggregation.icc_rwg",
            "contextHash": refreshed.json()["contextHash"],
        },
    )
    assert replacement.status_code == 201

    stale = client.put(
        f"/api/v1/analysis-drafts/{draft['id']}",
        json={"expectedRevision": 2, "spec": {}},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "ANALYSIS_DRAFT_SUPERSEDED"


def test_wide_panel_contract_uses_wave_count_and_keeps_design_role_rules() -> None:
    panel = StudyContextInput(
        time_structure="panel",
        dependence_structure="independent",
        design="observational",
    )
    wide = DatasetStructureInput(
        context=panel,
        subject_id="subject_id",
        data_layout="wide",
        wave_count=5,
    )
    assert wide.data_layout == "wide"
    assert wide.wave_count == 5

    with pytest.raises(ValueError, match="DATA_STRUCTURE_WAVE_COUNT_REQUIRED"):
        DatasetStructureInput(context=panel, subject_id="subject_id", data_layout="wide")

    randomized = StudyContextInput(
        time_structure="cross_sectional",
        dependence_structure="independent",
        design="randomized",
    )
    with pytest.raises(ValueError, match="DATA_STRUCTURE_GROUP_OR_TREATMENT_REQUIRED"):
        DatasetStructureInput(context=randomized)

    with pytest.raises(ValueError, match="DATA_STRUCTURE_ROLES_MUST_BE_DISTINCT"):
        DatasetStructureInput(
            context=panel,
            subject_id="same",
            data_layout="wide",
            wave_count=5,
            group_id="same",
        )
