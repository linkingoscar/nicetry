from __future__ import annotations

from pathlib import Path

import pytest

from app.contracts import (
    EstimandCausalTargetError,
    validate_contract,
    validate_estimand_causal_target,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODEL_SCHEMA = PROJECT_ROOT / "specs" / "model-spec.schema.json"
ADVANCED_SCHEMA = PROJECT_ROOT / "specs" / "advanced-analysis-spec.schema.json"


@pytest.mark.unit
def test_estimand_spec_schema_valid() -> None:
    """Verify EstimandSpec parses cleanly against JSON Schema contracts."""
    valid_model_spec = {
        "schemaVersion": "1.0.0",
        "modelId": "M_estimand_01",
        "name": "Estimand Test Model",
        "datasetVersionId": "DS_01",
        "estimandSpec": {
            "analysisRole": "preregistered_primary",
            "causalTarget": True,
            "identificationAssumptions": ["unconfoundedness", "no_measurement_error"],
            "effectScale": "regression_coefficient",
        },
        "design": {
            "timeStructure": "cross_sectional",
            "clustering": "none",
            "claimMode": "causal_with_assumptions",
        },
        "nodes": [
            {
                "id": "node_x1",
                "label": "X1",
                "kind": "observed",
                "role": "x",
                "dataType": "continuous",
            },
            {
                "id": "node_y1",
                "label": "Y1",
                "kind": "observed",
                "role": "y",
                "dataType": "continuous",
            },
        ],
        "edges": [
            {
                "id": "edge_e1",
                "from": "node_x1",
                "to": "node_y1",
                "kind": "regression",
            }
        ],
        "moderations": [],
        "covariates": [],
        "estimation": {
            "family": "ols",
            "standardErrors": "hc3",
            "confidenceLevel": 0.95,
            "bootstrap": {
                "enabled": False,
                "replicates": 1000,
                "method": "percentile",
                "seed": 42,
            },
            "missing": "complete_cases_per_model",
            "centering": {"method": "none", "nodeIds": []},
            "reportScale": "unstandardized_primary",
        },
    }

    validate_contract(valid_model_spec, MODEL_SCHEMA)
    validate_estimand_causal_target(valid_model_spec)


@pytest.mark.unit
def test_estimand_causal_target_rejected_without_assumptions() -> None:
    """Verify that causalTarget=True on cross-sectional data raises EstimandCausalTargetError if identificationAssumptions is empty."""
    invalid_spec = {
        "estimandSpec": {
            "analysisRole": "exploratory_post_data",
            "causalTarget": True,
            "identificationAssumptions": [],
            "effectScale": "mean_difference",
        },
        "design": {
            "timeStructure": "cross_sectional",
            "clustering": "none",
            "claimMode": "associational",
        },
    }

    with pytest.raises(EstimandCausalTargetError) as exc_info:
        validate_estimand_causal_target(invalid_spec)

    assert exc_info.value.code == "ESTIMAND_CAUSAL_TARGET_INVALID"
    assert "identificationAssumptions" in str(exc_info.value)


@pytest.mark.unit
def test_estimand_causal_target_accepted_for_longitudinal() -> None:
    """Verify that causalTarget=True on longitudinal data is accepted even with empty assumptions."""
    longitudinal_spec = {
        "estimandSpec": {
            "analysisRole": "planned_not_preregistered",
            "causalTarget": True,
            "identificationAssumptions": [],
            "effectScale": "within_person_slope",
        },
        "design": {
            "timeStructure": "longitudinal",
            "clustering": "none",
            "claimMode": "causal_with_assumptions",
        },
    }

    validate_estimand_causal_target(longitudinal_spec)
