from __future__ import annotations

import time
from io import BytesIO
from zipfile import ZipFile

import pytest
from starlette.testclient import TestClient

from app.contracts import validate_contract
from app.main import app
from app.services.advanced_runner import (
    AdvancedExecutionError,
    _normalize_optional_presentation_assets,
)
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


def _advanced_dataset() -> tuple[str, dict[str, str]]:
    lines = ["subject,cluster,condition,x,y,y1,y2,y3,missing_x"]
    for index in range(1, 61):
        cluster = (index - 1) // 5 + 1
        condition = "B" if index % 2 else "A"
        x = (index % 11) / 3
        cluster_effect = cluster / 10
        y = 2 + 0.6 * x + (0.8 if condition == "B" else 0) + cluster_effect
        missing_x = "" if index % 7 == 0 else f"{x:.6f}"
        lines.append(
            f"{index},{cluster},{condition},{x:.6f},{y:.6f},"
            f"{(y - 0.4):.6f},{y:.6f},{(y + 0.5):.6f},{missing_x}"
        )
    response = client.post(
        "/api/v1/datasets/import",
        files={"file": ("advanced.csv", BytesIO("\n".join(lines).encode()), "text/csv")},
    )
    assert response.status_code == 201, response.text
    dataset = response.json()
    variables = {variable["originalName"]: variable["id"] for variable in dataset["variables"]}
    return dataset["id"], variables


def test_optional_apa_reports_normalize_empty_r_values() -> None:
    engine_result = {"apaReports": ["Model fit was acceptable.", [], None]}

    _normalize_optional_presentation_assets(engine_result)

    assert engine_result["apaReports"] == ["Model fit was acceptable."]


@pytest.mark.parametrize(
    "engine_result, code",
    [
        ({"apaReports": "not-an-array"}, "INVALID_APA_REPORTS"),
        ({"apaReports": [{"text": "not-a-string"}]}, "INVALID_APA_REPORT"),
    ],
)
def test_optional_apa_reports_reject_invalid_values(engine_result: dict, code: str) -> None:
    with pytest.raises(AdvancedExecutionError) as error:
        _normalize_optional_presentation_assets(engine_result)

    assert error.value.code == code


def test_capability_catalog_declares_experimental_runners() -> None:
    response = client.get("/api/v1/advanced-analyses/capabilities")
    assert response.status_code == 200
    payload = response.json()
    capabilities = payload["capabilities"]
    assert payload["schemaVersion"] == "0.1.0"
    assert {item["family"] for item in capabilities} == {
        "experimental_design",
        "multilevel_model",
        "longitudinal_model",
        "multiple_imputation",
        "power_analysis",
        "questionnaire_measurement",
    }
    assert all(item["status"] == "experimental" for item in capabilities)
    assert all(item["executionAvailable"] is True for item in capabilities)
    assert all(item["slices"] for item in capabilities)
    assert all(
        any(slice_["executionAvailable"] for slice_ in item["slices"]) for item in capabilities
    )
    power = next(item for item in capabilities if item["family"] == "power_analysis")
    assert any(
        slice_["id"] == "power_analysis.monte_carlo" and slice_["executionAvailable"]
        for slice_ in power["slices"]
    )


def test_each_advanced_family_has_a_validatable_reserved_contract() -> None:
    dataset_id = "dataset_future_001"
    experiment = {
        **_common("experimental_design", "analysis_experiment"),
        "datasetVersionId": dataset_id,
        "designType": "factorial_anova",
        "dataLayout": "long",
        "outcomeIds": ["outcome_score"],
        "betweenFactors": [{"variableId": "condition_id", "coding": "sum"}],
        "withinFactors": [],
        "subjectId": "participant_id",
        "covariateIds": [],
        "sumOfSquares": "III",
        "sphericityCorrection": "auto",
        "postHocAdjustment": "holm",
    }
    multilevel = {
        **_common("multilevel_model", "analysis_multilevel"),
        "datasetVersionId": dataset_id,
        "outcomeId": "outcome_score",
        "distribution": "gaussian",
        "clusterVariableId": "team_id",
        "fixedEffectIds": ["predictor_x"],
        "randomEffects": [
            {
                "groupingVariableId": "team_id",
                "intercept": True,
                "slopeVariableIds": [],
                "covariance": "correlated",
            }
        ],
        "centering": [{"variableId": "predictor_x", "method": "group_mean"}],
        "estimator": "REML",
        "degreesOfFreedom": "satterthwaite",
        "minimumClusterCount": 30,
    }
    longitudinal = {
        **_common("longitudinal_model", "analysis_longitudinal"),
        "datasetVersionId": dataset_id,
        "modelType": "cross_lagged_panel",
        "subjectId": "participant_id",
        "waves": [
            {"wave": "T1", "timeValue": 0, "variables": {"x": "x_time_1", "y": "y_time_1"}},
            {"wave": "T2", "timeValue": 1, "variables": {"x": "x_time_2", "y": "y_time_2"}},
            {"wave": "T3", "timeValue": 2, "variables": {"x": "x_time_3", "y": "y_time_3"}},
        ],
        "estimator": "MLR",
        "missing": "fiml",
        "invarianceLevels": [],
    }
    imputation = {
        **_common("multiple_imputation", "analysis_imputation"),
        "datasetVersionId": dataset_id,
        "method": "mice_fcs",
        "imputations": 20,
        "iterations": 20,
        "variables": [
            {"variableId": "outcome_score", "method": "pmm", "predictorIds": ["predictor_x"]}
        ],
        "passiveRules": [],
        "pooling": "none",
        "diagnostics": ["trace", "distribution"],
    }
    power = {
        **_common("power_analysis", "analysis_power"),
        "designFamily": "regression",
        "method": "analytic",
        "solveFor": "sample_size",
        "alpha": 0.05,
        "targetPower": 0.8,
        "effectSize": {"metric": "cohens_f2", "value": 0.15},
        "groups": 1,
        "predictors": 4,
        "simulations": 5000,
    }

    for spec in (experiment, multilevel, longitudinal, imputation, power):
        request_dataset = None if spec["family"] == "power_analysis" else dataset_id
        response = client.post(
            "/api/v1/advanced-analyses/validate",
            json=_request(spec, request_dataset),
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["valid"] is True
        assert payload["implementationStatus"] == "experimental"
        assert payload["executionAvailable"] is True
        assert payload["warnings"][0]["code"] == "CAPABILITY_EXPERIMENTAL"
        assert payload["spec"]["family"] == spec["family"]
        validate_contract(payload["spec"], get_settings().advanced_spec_schema_path)


def test_repeated_measures_requires_subject_and_within_factor() -> None:
    dataset_id = "dataset_future_001"
    invalid = {
        **_common("experimental_design", "analysis_invalid"),
        "datasetVersionId": dataset_id,
        "designType": "repeated_measures",
        "dataLayout": "long",
        "outcomeIds": ["outcome_score"],
        "betweenFactors": [],
        "withinFactors": [],
        "covariateIds": [],
        "sumOfSquares": "III",
        "sphericityCorrection": "auto",
        "postHocAdjustment": "holm",
    }
    response = client.post(
        "/api/v1/advanced-analyses/validate",
        json=_request(invalid, dataset_id),
    )
    assert response.status_code == 422
    assert "必须提供至少一个因子" in response.text or "subjectId" in response.text


def test_longitudinal_clpm_requires_three_waves() -> None:
    dataset_id = "dataset_future_001"
    invalid_longitudinal = {
        **_common("longitudinal_model", "analysis_longitudinal_invalid"),
        "datasetVersionId": dataset_id,
        "modelType": "cross_lagged_panel",
        "subjectId": "subj",
        "waves": [
            {"wave": "w1", "timeValue": 1.0, "variables": {"c1": "v1"}},
            {"wave": "w2", "timeValue": 2.0, "variables": {"c1": "v2"}},
        ],
        "estimator": "MLR",
        "missing": "fiml",
    }
    response = client.post(
        "/api/v1/advanced-analyses/validate",
        json=_request(invalid_longitudinal, dataset_id),
    )
    assert response.status_code == 422
    assert "LONGITUDINAL_INSUFFICIENT_WAVES_FOR_SUPPORTED_CLPM" in response.text


def test_ri_clpm_slice_is_visible_and_executable_for_two_constructs() -> None:
    dataset_id = "dataset_future_001"
    planned = {
        **_common("longitudinal_model", "analysis_ri_clpm_experimental"),
        "datasetVersionId": dataset_id,
        "modelType": "ri_clpm",
        "subjectId": "participant_id",
        "waves": [
            {"wave": "T1", "timeValue": 0, "variables": {"x": "x1", "y": "y1"}},
            {"wave": "T2", "timeValue": 1, "variables": {"x": "x2", "y": "y2"}},
            {"wave": "T3", "timeValue": 2, "variables": {"x": "x3", "y": "y3"}},
        ],
        "estimator": "MLR",
        "missing": "fiml",
        "invarianceLevels": [],
    }
    response = client.post(
        "/api/v1/advanced-analyses/validate",
        json=_request(planned, dataset_id),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["capabilityId"] == "longitudinal_model.ri_clpm"
    assert payload["sliceStatus"] == "experimental"
    assert payload["executionAvailable"] is True
    assert payload["warnings"][0]["code"] == "CAPABILITY_EXPERIMENTAL"


def test_power_sensitivity_preserves_requested_r_squared_change_metric() -> None:
    spec = {
        **_common("power_analysis", "analysis_power_sensitivity"),
        "designFamily": "regression",
        "method": "analytic",
        "solveFor": "effect_size",
        "alpha": 0.05,
        "targetPower": 0.8,
        "sampleSize": 100,
        "effectSizeMetric": "r_squared_change",
        "predictors": 3,
        "groups": 1,
        "simulations": 5000,
        "alternative": "two_sided",
        "roundingRule": "ceil",
    }
    validation = client.post(
        "/api/v1/advanced-analyses/validate",
        json=_request(spec),
    )
    assert validation.status_code == 200, validation.text
    validation_payload = validation.json()
    assert validation_payload["capabilityId"] == "power_analysis.analytic.regression"
    assert validation_payload["spec"]["effectSizeMetric"] == "r_squared_change"

    response = client.post("/api/v1/advanced-analyses", json=_request(spec))
    assert response.status_code == 202, response.text
    run_id = response.json()["id"]
    started = time.time()
    while True:
        status = client.get(f"/api/v1/advanced-analyses/{run_id}").json()["status"]
        if status in {"succeeded", "failed", "cancelled"}:
            break
        if time.time() - started > 10:
            raise TimeoutError("Test timed out waiting for power sensitivity analysis")
        time.sleep(0.5)

    assert status == "succeeded"
    result_response = client.get(f"/api/v1/advanced-analyses/{run_id}/result")
    assert result_response.status_code == 200
    result = result_response.json()
    validate_contract(result, get_settings().advanced_result_schema_path)
    family_result = result["familyResult"]
    assert family_result["solvedValue"] == pytest.approx(0.101981133444645, abs=1e-10)
    assert family_result["achievedPower"] == pytest.approx(0.8, abs=1e-10)
    assert family_result["parameters"]["effectSizeMetric"] == "r_squared_change"
    assert family_result["parameters"]["solvedValueMetric"] == "r_squared_change"
    assert family_result["parameters"]["solvedEffectSize"]["metric"] == "r_squared_change"


def test_power_anova_rejects_non_divisible_total_sample_size() -> None:
    spec = {
        **_common("power_analysis", "analysis_power_invalid_anova_n"),
        "designFamily": "factorial_anova",
        "method": "analytic",
        "solveFor": "power",
        "alpha": 0.05,
        "targetPower": 0.8,
        "sampleSize": 100,
        "effectSize": {"metric": "cohens_f", "value": 0.25},
        "groups": 3,
        "predictors": 1,
        "simulations": 5000,
        "alternative": "two_sided",
        "roundingRule": "ceil",
    }
    response = client.post(
        "/api/v1/advanced-analyses/validate",
        json=_request(spec),
    )
    assert response.status_code == 422
    assert "POWER_SAMPLE_SIZE_NOT_DIVISIBLE_BY_GROUPS" in response.text


def test_data_backed_advanced_runners_produce_valid_results() -> None:
    dataset_id, variable = _advanced_dataset()
    specifications = [
        {
            **_common("experimental_design", "analysis_experimental_run"),
            "datasetVersionId": dataset_id,
            "designType": "factorial_anova",
            "dataLayout": "long",
            "outcomeIds": [variable["y"]],
            "betweenFactors": [{"variableId": variable["condition"], "coding": "sum"}],
            "withinFactors": [],
            "covariateIds": [],
            "sumOfSquares": "III",
            "sphericityCorrection": "auto",
            "postHocAdjustment": "holm",
        },
        {
            **_common("multilevel_model", "analysis_multilevel_run"),
            "datasetVersionId": dataset_id,
            "outcomeId": variable["y"],
            "distribution": "gaussian",
            "clusterVariableId": variable["cluster"],
            "fixedEffectIds": [variable["x"]],
            "randomEffects": [
                {
                    "groupingVariableId": variable["cluster"],
                    "intercept": True,
                    "slopeVariableIds": [],
                    "covariance": "correlated",
                }
            ],
            "centering": [{"variableId": variable["x"], "method": "group_mean"}],
            "estimator": "REML",
            "degreesOfFreedom": "satterthwaite",
            "minimumClusterCount": 10,
        },
        {
            **_common("longitudinal_model", "analysis_longitudinal_run"),
            "datasetVersionId": dataset_id,
            "modelType": "growth_curve",
            "subjectId": variable["subject"],
            "waves": [
                {"wave": "T1", "timeValue": 0, "variables": {"y": variable["y1"]}},
                {"wave": "T2", "timeValue": 1, "variables": {"y": variable["y2"]}},
                {"wave": "T3", "timeValue": 2, "variables": {"y": variable["y3"]}},
            ],
            "estimator": "MLR",
            "missing": "complete_cases",
            "invarianceLevels": [],
        },
        {
            **_common("multiple_imputation", "analysis_imputation_run"),
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
            "passiveRules": [],
            "pooling": "none",
            "diagnostics": ["trace", "distribution"],
        },
    ]

    for spec in specifications:
        response = client.post(
            "/api/v1/advanced-analyses",
            json=_request(spec, dataset_id),
        )
        assert response.status_code == 202, response.text
        run_id = response.json()["id"]

        timeout = 20
        started = time.time()
        while True:
            status_response = client.get(f"/api/v1/advanced-analyses/{run_id}")
            assert status_response.status_code == 200
            status = status_response.json()["status"]
            if status in {"succeeded", "failed", "cancelled"}:
                break
            if time.time() - started > timeout:
                raise TimeoutError(f"Test timed out waiting for advanced job {spec['family']}")
            time.sleep(0.5)

        assert status == "succeeded", (
            f"Job failed with error: {status_response.json().get('error')}"
        )
        result_response = client.get(f"/api/v1/advanced-analyses/{run_id}/result")
        assert result_response.status_code == 200
        result = result_response.json()

        validate_contract(result, get_settings().advanced_result_schema_path)
        assert result["run"]["family"] == spec["family"]
        assert result["sampleFlow"]["included"] > 0
        if spec["family"] == "multiple_imputation":
            assert result["familyResult"]["poolingStatus"] == "not_available"
            assert "pooledEstimates" not in result["familyResult"]
            assert "poolingMethod" not in result["provenance"]
        if spec["family"] == "experimental_design":
            reports = "\n".join(result.get("apaReports", []))
            for omnibus in result["familyResult"]["omnibusTests"]:
                assert omnibus["term"] in reports
            assert result.get("plots", []) == []
            assert "significant" not in reports.lower()
            exported = client.get(f"/api/v1/advanced-analyses/{run_id}/export")
            assert exported.status_code == 200, exported.text
            with ZipFile(BytesIO(exported.content)) as archive:
                assert "paper/report.md" in archive.namelist()
                assert "data/analysis-data.parquet" not in archive.namelist()
            exported_with_data = client.get(
                f"/api/v1/advanced-analyses/{run_id}/export?include_data=true"
            )
            assert exported_with_data.status_code == 200, exported_with_data.text
            with ZipFile(BytesIO(exported_with_data.content)) as archive:
                assert "data/analysis-data.parquet" in archive.namelist()
        if spec["family"] == "multilevel_model":
            assert (
                variable["x"] + "__between" not in result["familyResult"]["compiledFixedEffectIds"]
            )
            assert any(item["code"] == "MISSING_BETWEEN_EFFECT" for item in result["warnings"])
            assert result["provenance"]["missingMethod"] == "complete_cases"
            assert result["provenance"]["centering"][0]["method"] == "group_mean"
        if spec["family"] == "longitudinal_model":
            assert result["familyResult"]["modelType"] == "growth_curve"
            assert result["familyResult"]["missingMethod"] == "complete_cases"
            assert result["familyResult"]["timeValues"] == [0, 1, 2]
