from __future__ import annotations

import json
import time
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from starlette.testclient import TestClient

from app.contracts import validate_contract
from app.main import app
from app.services.repository_io import JsonObject
from app.settings import get_settings

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def _common(family: str, analysis_id: str) -> dict[str, object]:
    return {
        "schemaVersion": "0.1.0",
        "analysisId": analysis_id,
        "name": analysis_id,
        "family": family,
        "confidenceLevel": 0.95,
        "seed": 20260729,
    }


def _import_csv(name: str, content: bytes) -> tuple[str, dict[str, str]]:
    response = client.post(
        "/api/v1/datasets/import",
        files={"file": (name, BytesIO(content), "text/csv")},
    )
    assert response.status_code == 201, response.text
    dataset = response.json()
    variables = {
        variable["originalName"]: variable["id"] for variable in dataset["variables"]
    }
    return dataset["id"], variables


def _cross_sectional_dataset() -> tuple[str, dict[str, str]]:
    rows = ["subject,condition,x,y,missing_x"]
    for index in range(1, 81):
        condition = "B" if index % 2 else "A"
        x = (index % 13) / 4
        y = 1.5 + 0.7 * x + (0.9 if condition == "B" else 0)
        missing_x = "" if index % 9 == 0 else f"{x:.6f}"
        rows.append(f"{index},{condition},{x:.6f},{y:.6f},{missing_x}")
    return _import_csv("advanced-cross-sectional.csv", "\n".join(rows).encode())


def _prepare_bound_request(
    spec: dict[str, object], dataset_id: str
) -> tuple[dict[str, object], str]:
    dataset_response = client.get(f"/api/v1/datasets/{dataset_id}")
    assert dataset_response.status_code == 200, dataset_response.text
    dataset = dataset_response.json()
    project_id = dataset["projectId"]
    experimental = spec.get("family") == "experimental_design"
    context_payload = {
        "schemaVersion": "1.0.0",
        "timeStructure": "cross_sectional",
        "dependenceStructure": "independent",
        "design": "randomized" if experimental else "observational",
    }
    current_context = client.get(f"/api/v1/projects/{project_id}/study-context")
    saved_context = client.put(
        f"/api/v1/projects/{project_id}/study-context",
        json={
            "expectedRevision": current_context.json()["revision"] if current_context.status_code == 200 else None,
            "context": context_payload,
        },
    )
    assert saved_context.status_code == 200, saved_context.text
    condition_id = next(
        variable["id"] for variable in dataset["variables"] if variable["originalName"] == "condition"
    ) if experimental else None
    current_structure = client.get(f"/api/v1/datasets/{dataset_id}/study-structure")
    structure = client.post(
        f"/api/v1/datasets/{dataset_id}/study-structures",
        json={
            "expectedRevision": current_structure.json()["revision"] if current_structure.status_code == 200 else None,
            "studyContextVersionId": saved_context.json()["id"],
            "roles": {
                "subjectId": None,
                "clusterId": None,
                "timeId": None,
                "groupId": condition_id,
                "treatmentId": None,
            },
        },
    )
    assert structure.status_code == 201, structure.text
    if spec.get("family") == "questionnaire_measurement":
        dictionary = client.put(
            f"/api/v1/datasets/{dataset_id}/dictionary",
            json={
                "variables": [
                    {
                        "id": variable["id"],
                        "confirmed_type": variable["inferredType"],
                    }
                    for variable in dataset["variables"]
                ]
            },
        )
        assert dictionary.status_code == 200, dictionary.text
        raw_item_ids = spec.get("itemIds", [])
        assert isinstance(raw_item_ids, list)
        item_ids = [str(item_id) for item_id in raw_item_ids]
        measurement = client.put(
            f"/api/v1/datasets/{dataset_id}/measurement",
            json={
                "constructs": [
                    {
                        "id": "construct_x",
                        "name": "X construct",
                        "item_ids": item_ids[:2],
                        "reverse_item_ids": [],
                        "theoretical_minimum": 0,
                        "theoretical_maximum": 10,
                        "aggregation": "mean",
                        "minimum_valid_proportion": 0.8,
                    },
                    {
                        "id": "construct_y",
                        "name": "Y construct",
                        "item_ids": item_ids[2:4],
                        "reverse_item_ids": [],
                        "theoretical_minimum": 0,
                        "theoretical_maximum": 10,
                        "aggregation": "mean",
                        "minimum_valid_proportion": 0.8,
                    },
                ],
                "change_note": "为高级测量规格创建可追溯的测量版本",
            },
        )
        assert measurement.status_code == 200, measurement.text
    resolved = client.get(f"/api/v1/datasets/{dataset_id}/resolved-analysis-context")
    assert resolved.status_code == 200, resolved.text
    context = resolved.json()
    slice_id = {
        "experimental_design": "experimental_design.factorial_anova.long.single_outcome",
        "multiple_imputation": "multiple_imputation.rubin_pooling",
        "questionnaire_measurement": "questionnaire_measurement.esem_bifactor_irt",
    }[str(spec["family"])]
    draft = client.post(
        f"/api/v1/datasets/{dataset_id}/analysis-drafts",
        json={"sliceId": slice_id, "contextHash": context["contextHash"]},
    )
    assert draft.status_code == 201, draft.text
    return {**spec, "contextHash": context["contextHash"]}, draft.json()["id"]


def _wait_for_result(run_id: str, timeout_seconds: float = 185) -> JsonObject:
    started = time.monotonic()
    while True:
        status_response = client.get(f"/api/v1/advanced-analyses/{run_id}")
        assert status_response.status_code == 200, status_response.text
        state = status_response.json()
        if state["status"] in {"succeeded", "failed", "cancelled"}:
            assert state["status"] == "succeeded", (
                state.get("errorCode"),
                state.get("error"),
                state.get("errorDetails"),
            )
            break
        if time.monotonic() - started > timeout_seconds:
            raise TimeoutError(f"高级分析任务超时: {run_id}")
        time.sleep(0.25)
    result_response = client.get(f"/api/v1/advanced-analyses/{run_id}/result")
    assert result_response.status_code == 200, result_response.text
    result = result_response.json()
    validate_contract(result, get_settings().advanced_result_schema_path)
    return result


def _run(spec: dict[str, object], dataset_id: str | None = None) -> tuple[str, JsonObject]:
    draft_id = None
    prepared_spec = spec
    if dataset_id is not None:
        prepared_spec, draft_id = _prepare_bound_request(spec, dataset_id)
    request = {"datasetId": dataset_id, "draftId": draft_id, "spec": prepared_spec}
    validation = client.post("/api/v1/advanced-analyses/validate", json=request)
    assert validation.status_code == 200, validation.text
    assert validation.json()["executionAvailable"] is True
    validate_contract(validation.json()["spec"], get_settings().advanced_spec_schema_path)

    submitted = client.post("/api/v1/advanced-analyses", json=request)
    assert submitted.status_code == 202, submitted.text
    run_id = submitted.json()["id"]
    return run_id, _wait_for_result(run_id)


def test_catalog_exposes_restored_families_in_product_order() -> None:
    response = client.get("/api/v1/advanced-analyses/capabilities")
    assert response.status_code == 200
    families = [item["family"] for item in response.json()["capabilities"]]
    assert families == [
        "experimental_design",
        "multilevel_model",
        "longitudinal_model",
        "power_analysis",
        "multiple_imputation",
        "questionnaire_measurement",
    ]
    assert all(
        item["executionAvailable"] and any(
            slice_["executionAvailable"] for slice_ in item["slices"]
        )
        for item in response.json()["capabilities"]
    )
    assert all(
        item["validationLevel"] in {"unvalidated", "internally_validated", "externally_validated"}
        and item["maturityLevel"] in {"experimental", "validated", "reviewer_ready", "publication_ready"}
        and item["publicationEligibility"]
        in {"ineligible", "conditional", "eligible"}
        and item["publicationEligibilityReason"]
        and set(item["validationEvidence"]) == {
            "contractTests",
            "applicabilityTests",
            "failureFixtures",
            "externalOracle",
            "numericGoldenId",
            "oracleIndependence",
        }
        and (
            item["validationEvidence"].get("externalOracle") is None
            or bool(item["validationEvidence"].get("oracleIndependence"))
        )
        for item in response.json()["capabilities"]
    )
    assert all(
        slice_["validationLevel"] in {"unvalidated", "internally_validated", "externally_validated"}
        and slice_["maturityLevel"] in {"experimental", "validated", "reviewer_ready", "publication_ready"}
        and slice_["publicationEligibility"]
        in {"ineligible", "conditional", "eligible"}
        and slice_["publicationEligibilityReason"]
        and set(slice_["validationEvidence"]) == {
            "contractTests",
            "applicabilityTests",
            "failureFixtures",
            "externalOracle",
            "numericGoldenId",
            "oracleIndependence",
        }
        and (
            slice_["validationEvidence"].get("externalOracle") is None
            or bool(slice_["validationEvidence"].get("oracleIndependence"))
        )
        for item in response.json()["capabilities"]
        for slice_ in item["slices"]
    )
    assert not any(
        item["publicationEligibility"] == "eligible"
        for item in response.json()["capabilities"]
    )


def test_four_restored_workbench_families_run_and_export_end_to_end() -> None:
    dataset_id, variable = _cross_sectional_dataset()
    experiment = {
        **_common("experimental_design", "experiment_e2e"),
        "datasetVersionId": dataset_id,
        "designType": "factorial_anova",
        "dataLayout": "long",
        "outcomeIds": [variable["y"]],
        "betweenFactors": [{"variableId": variable["condition"], "coding": "sum"}],
        "sumOfSquares": "III",
        "postHocAdjustment": "holm",
    }
    power = {
        **_common("power_analysis", "power_e2e"),
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
    imputation = {
        **_common("multiple_imputation", "imputation_e2e"),
        "datasetVersionId": dataset_id,
        "method": "mice_fcs",
        "imputations": 5,
        "iterations": 5,
        "variables": [
            {
                "variableId": variable["missing_x"],
                "method": "pmm",
                "predictorIds": [variable["y"]],
            }
        ],
        "pooling": "rubin",
        "pooledAnalysis": {
            "modelType": "linear_regression",
            "outcomeId": variable["y"],
            "predictorIds": [variable["missing_x"]],
            "includeIntercept": True,
        },
        "diagnostics": ["trace", "distribution", "fraction_missing_information"],
    }

    measurement_path = (
        Path(__file__).parent
        / "fixtures"
        / "advanced"
        / "longitudinal"
        / "clpm-three-wave.csv"
    )
    measurement_dataset_id, measurement_variable = _import_csv(
        "advanced-measurement.csv",
        measurement_path.read_bytes(),
    )
    measurement = {
        **_common("questionnaire_measurement", "measurement_esem_e2e"),
        "datasetVersionId": measurement_dataset_id,
        "modelType": "esem",
        "itemIds": [
            measurement_variable["x1"],
            measurement_variable["y1"],
            measurement_variable["x2"],
            measurement_variable["y2"],
        ],
        "constructs": [
            {
                "id": "construct_x",
                "label": "X construct",
                "itemIds": [measurement_variable["x1"], measurement_variable["x2"]],
            },
            {
                "id": "construct_y",
                "label": "Y construct",
                "itemIds": [measurement_variable["y1"], measurement_variable["y2"]],
            },
        ],
        "estimator": "ML",
        "itemScale": "continuous",
        "factorCount": 2,
        "rotation": "target",
        "parallelIterations": 100,
    }

    runs = [
        _run(experiment, dataset_id),
        _run(power),
        _run(imputation, dataset_id),
        _run(measurement, measurement_dataset_id),
    ]
    assert [result["run"]["family"] for _, result in runs] == [
        "experimental_design",
        "power_analysis",
        "multiple_imputation",
        "questionnaire_measurement",
    ]
    assert runs[2][1]["familyResult"]["poolingStatus"] == "rubin"
    assert runs[2][1]["familyResult"]["pooledAnalysis"]["estimates"]
    esem = runs[3][1]["familyResult"]["esem"]
    assert esem["available"] is True
    assert esem["factorCount"] == 2
    assert len(esem["loadings"]) == 4

    for run_id, _result in runs:
        exported = client.get(f"/api/v1/advanced-analyses/{run_id}/export")
        assert exported.status_code == 200, exported.text
        with ZipFile(BytesIO(exported.content)) as archive:
            assert "paper/report.md" in archive.namelist()
            assert "provenance/manifest.json" in archive.namelist()
            assert "ro-crate-metadata.json" in archive.namelist()
            assert "replay/verify-package.py" in archive.namelist()
            bundled = json.loads(archive.read("result/advanced-result.json"))
            assert bundled["replay"]["packageGenerated"] is True
            assert bundled["replay"]["dataIncluded"] is False

    exported_with_data = client.get(
        f"/api/v1/advanced-analyses/{runs[0][0]}/export?include_data=true"
    )
    assert exported_with_data.status_code == 200, exported_with_data.text
    with ZipFile(BytesIO(exported_with_data.content)) as archive:
        assert "data/analysis-data.parquet" in archive.namelist()
