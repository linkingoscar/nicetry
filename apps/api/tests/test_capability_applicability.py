from __future__ import annotations

import pytest

from app.capability_catalog import ACTIVE_CAPABILITIES, ValidationEvidence, derive_capability_gates
from app.services.analysis_context import AnalysisContextResolutionError
from app.services.capability_applicability import CapabilityApplicabilityRegistry
from app.services.empirical_context_gate import require_empirical_capability


def test_all_documented_advanced_slices_are_registered_with_hidden_mice_generation() -> None:
    expected = {
        "experimental_design.factorial_anova.long.single_outcome",
        "experimental_design.ancova.long.single_outcome",
        "experimental_design.repeated_measures.single_within",
        "experimental_design.mixed_design.single_within",
        "experimental_design.glm_cluster.long.single_outcome",
        "multilevel_model.aggregation.icc_rwg",
        "multilevel_model.gaussian.two_level",
        "power_analysis.analytic.regression",
        "power_analysis.analytic.t_test",
        "power_analysis.analytic.factorial_anova",
        "power_analysis.monte_carlo",
        "multiple_imputation.mice_dataset_generation",
        "multiple_imputation.rubin_pooling",
        "questionnaire_measurement.reliability",
        "questionnaire_measurement.efa",
        "questionnaire_measurement.cfa",
        "questionnaire_measurement.measurement_invariance",
        "questionnaire_measurement.esem_bifactor_irt",
        "questionnaire_measurement.common_method_bias",
    }
    registered = {definition.slice_id for definition in ACTIVE_CAPABILITIES}
    assert expected <= registered
    hidden = next(
        definition
        for definition in ACTIVE_CAPABILITIES
        if definition.slice_id == "multiple_imputation.mice_dataset_generation"
    )
    assert hidden.product_visible is False
    assert hidden.execution_available is True


def test_capability_maturity_never_treats_execution_as_publication_readiness() -> None:
    validation_values = {"unvalidated", "internally_validated", "externally_validated"}
    maturity_values = {"experimental", "validated", "reviewer_ready", "publication_ready"}
    publication_values = {"ineligible", "conditional", "eligible"}
    for definition in ACTIVE_CAPABILITIES:
        assert definition.validation_level in validation_values
        assert definition.maturity_level in maturity_values
        assert definition.publication_eligibility in publication_values
        assert definition.publication_eligibility_reason
        evidence = definition.validation_evidence
        if definition.validation_level == "unvalidated":
            assert definition.maturity_level == "experimental"
            assert definition.publication_eligibility == "ineligible"
            assert not any((evidence.contract_tests, evidence.applicability_tests, evidence.failure_fixtures))
        elif definition.validation_level == "internally_validated":
            assert definition.maturity_level == "validated"
            assert definition.publication_eligibility == "conditional"
        else:
            assert definition.maturity_level == "reviewer_ready"
            assert definition.publication_eligibility == "conditional"

    assert all(definition.maturity_level != "publication_ready" for definition in ACTIVE_CAPABILITIES)
    assert all(definition.publication_eligibility != "eligible" for definition in ACTIVE_CAPABILITIES)


def test_capability_gate_derives_each_maturity_transition_from_evidence() -> None:
    unvalidated = derive_capability_gates(ValidationEvidence())
    assert (unvalidated.validation_level, unvalidated.maturity_level, unvalidated.publication_eligibility) == (
        "unvalidated", "experimental", "ineligible"
    )

    internally_validated = derive_capability_gates(
        ValidationEvidence(contract_tests=True, applicability_tests=True, failure_fixtures=True)
    )
    assert (
        internally_validated.validation_level,
        internally_validated.maturity_level,
        internally_validated.publication_eligibility,
    ) == ("internally_validated", "validated", "conditional")

    externally_validated = derive_capability_gates(
        ValidationEvidence(
            contract_tests=True,
            applicability_tests=True,
            failure_fixtures=True,
            external_oracle="process-5.0",
            numeric_golden_id="process-goldens",
        )
    )
    assert (
        externally_validated.validation_level,
        externally_validated.maturity_level,
        externally_validated.publication_eligibility,
    ) == ("externally_validated", "reviewer_ready", "conditional")

    publication_ready = derive_capability_gates(
        externally_validated.validation_evidence,
        publication_gate_passed=True,
    )
    assert (
        publication_ready.validation_level,
        publication_ready.maturity_level,
        publication_ready.publication_eligibility,
    ) == ("externally_validated", "publication_ready", "eligible")


def test_nonrandom_comparison_cannot_unlock_randomized_experiment_slices() -> None:
    registry = CapabilityApplicabilityRegistry()
    context = {
        "dataset": {"id": "dataset_a", "hash": "a" * 64, "sha256": "a" * 64},
        "studyContext": {
            "value": {
                "timeStructure": "cross_sectional",
                "dependenceStructure": "independent",
                "design": "quasi_experimental",
            }
        },
        "structure": {
            "roles": {"groupId": "group", "treatmentId": "treatment"},
            "profile": {"nestingClassification": "two_level"},
        },
        "sample": {"id": "sample_a", "hash": "b" * 64},
    }

    by_id = {item["sliceId"]: item for item in registry.list(context)}
    for slice_id in (
        "experimental_design.factorial_anova.long.single_outcome",
        "experimental_design.ancova.long.single_outcome",
    ):
        assert by_id[slice_id]["executionAvailable"] is True
        assert by_id[slice_id]["applicable"] is False
        assert "design=quasi_experimental" in by_id[slice_id]["missingRequirements"]


def test_context_applicability_blocks_three_level_lmm_and_allows_cross_classified_esm() -> None:
    registry = CapabilityApplicabilityRegistry()
    context = {
        "dataset": {"id": "dataset_a", "hash": "a" * 64, "sha256": "a" * 64},
        "studyContext": {
            "value": {
                "timeStructure": "intensive_longitudinal",
                "dependenceStructure": "nested",
                "design": "observational",
            }
        },
        "structure": {
            "roles": {"subjectId": "subject", "clusterId": "cluster", "timeId": "time"},
            "profile": {"nestingClassification": "three_level"},
        },
        "sample": {"id": "sample_a", "hash": "b" * 64},
    }
    by_id = {item["sliceId"]: item for item in registry.list(context)}
    assert by_id["empirical.diary.cross_classified_gaussian"]["applicable"] is False

    context["structure"]["profile"]["nestingClassification"] = "cross_classified"
    assert by_id["empirical.diary.cross_classified_gaussian"]["applicable"] is False
    refreshed = {item["sliceId"]: item for item in registry.list(context)}
    assert refreshed["empirical.diary.cross_classified_gaussian"]["applicable"] is True


def test_three_level_profile_blocks_cluster_glm_and_icc_rwg() -> None:
    registry = CapabilityApplicabilityRegistry()
    context = {
        "dataset": {"id": "dataset_a", "hash": "a" * 64, "sha256": "a" * 64},
        "studyContext": {
            "value": {
                "timeStructure": "cross_sectional",
                "dependenceStructure": "nested",
                "design": "randomized",
            }
        },
        "structure": {
            "roles": {"clusterId": "cluster", "groupId": "group", "treatmentId": "treatment"},
            "profile": {"nestingClassification": "three_level"},
        },
        "sample": {"id": "sample_a", "hash": "b" * 64},
    }
    by_id = {item["sliceId"]: item for item in registry.list(context)}
    assert by_id["experimental_design.glm_cluster.long.single_outcome"]["applicable"] is False
    assert "profile=two_level" in by_id["experimental_design.glm_cluster.long.single_outcome"]["missingRequirements"]
    assert by_id["multilevel_model.aggregation.icc_rwg"]["applicable"] is False
    assert "profile=two_level" in by_id["multilevel_model.aggregation.icc_rwg"]["missingRequirements"]

    context["structure"]["profile"]["nestingClassification"] = "two_level"
    refreshed = {item["sliceId"]: item for item in registry.list(context)}
    assert refreshed["experimental_design.glm_cluster.long.single_outcome"]["applicable"] is True
    assert refreshed["multilevel_model.aggregation.icc_rwg"]["applicable"] is True


def test_nested_cross_sectional_base_workflow_allows_preparation_and_blocks_iid_inference() -> None:
    registry = CapabilityApplicabilityRegistry()
    context = {
        "dataset": {"id": "dataset_a", "hash": "a" * 64, "sha256": "a" * 64},
        "measurement": {"id": "measurement_a", "hash": "c" * 64},
        "studyContext": {
            "value": {
                "timeStructure": "cross_sectional",
                "dependenceStructure": "nested",
                "design": "observational",
            }
        },
        "structure": {
            "roles": {"clusterId": "school"},
            "profile": {"nestingClassification": "two_level"},
        },
        "sample": {"id": "sample_a", "hash": "b" * 64},
    }
    slices = require_empirical_capability(
        context,
        {"aggregationVariableId": "school"},
        registry,
    )
    assert slices == (
        "empirical.cross_sectional.overview",
        "empirical.cross_sectional.measurement",
        "multilevel_model.aggregation.icc_rwg",
    )

    with pytest.raises(AnalysisContextResolutionError, match="hierarchical_regression"):
        require_empirical_capability(
            context,
            {"outcomeVariableId": "y", "predictorVariableIds": ["x"]},
            registry,
        )
    with pytest.raises(AnalysisContextResolutionError, match="group_comparison"):
        require_empirical_capability(
            context,
            {"groupVariableId": "condition"},
            registry,
        )


@pytest.mark.parametrize(
    ("time_structure", "method_options"),
    [
        ("panel", {"longitudinalPanel": {"modelType": "clpm"}}),
        ("intensive_longitudinal", {"diaryMultilevel": {"analysisType": "lmm"}}),
    ],
)
def test_repeated_measurement_workflows_reject_hidden_cross_sectional_regression(
    time_structure: str,
    method_options: dict[str, object],
) -> None:
    context = {
        "dataset": {"id": "dataset_a", "hash": "a" * 64, "sha256": "a" * 64},
        "measurement": {"id": "measurement_a", "hash": "c" * 64},
        "studyContext": {
            "value": {
                "timeStructure": time_structure,
                "dependenceStructure": "independent",
                "design": "observational",
            }
        },
        "structure": {
            "roles": {"subjectId": "participant", "timeId": "wave"},
            "profile": {"nestingClassification": "two_level"},
        },
        "sample": {"id": "sample_a", "hash": "b" * 64},
    }
    options = {
        **method_options,
        "outcomeVariableId": "y",
        "predictorVariableIds": ["x"],
    }

    with pytest.raises(AnalysisContextResolutionError, match="hierarchical_regression"):
        require_empirical_capability(context, options)
