from app.advanced_contracts import (
    EffectSize,
    ImputationVariable,
    MultilevelModelSpec,
    MultipleImputationSpec,
    PowerAnalysisSpec,
    RandomEffect,
)
from app.services.advanced_analysis import advanced_analysis_registry


def test_power_analysis_slice_validation() -> None:
    spec = PowerAnalysisSpec(
        analysis_id="power_test_01",
        name="Analytic Power Analysis",
        family="power_analysis",
        design_family="regression",
        method="analytic",
        solve_for="sample_size",
        alpha=0.05,
        target_power=0.80,
        effect_size=EffectSize(metric="cohens_f2", value=0.15),
        predictors=3,
    )
    result = advanced_analysis_registry.validate(spec)
    assert result["valid"] is True
    assert result["executionAvailable"] is True
    assert result["capabilityId"] == "power_analysis.analytic.regression"


def test_multiple_imputation_slice_validation() -> None:
    spec = MultipleImputationSpec(
        analysis_id="mi_test_01",
        name="Multiple Imputation FCS",
        dataset_version_id="dataset_01",
        family="multiple_imputation",
        method="mice_fcs",
        imputations=5,
        iterations=10,
        variables=[ImputationVariable(variable_id="var1", method="pmm", predictor_ids=["var2"])],
    )
    result = advanced_analysis_registry.validate(spec)
    assert result["valid"] is True
    assert result["executionAvailable"] is True
    assert result["capabilityId"] == "multiple_imputation.mice_dataset_generation"


def test_cross_sectional_multilevel_slice_validation() -> None:
    spec = MultilevelModelSpec(
        analysis_id="multilevel_test_01",
        name="Two-level clustered cross-sectional model",
        dataset_version_id="dataset_01",
        family="multilevel_model",
        analysis_type="lmm",
        outcome_id="outcome_variable",
        cluster_variable_id="team_identifier",
        fixed_effect_ids=["predictor_variable"],
        random_effects=[
            RandomEffect(
                grouping_variable_id="team_identifier",
                intercept=True,
            )
        ],
    )
    result = advanced_analysis_registry.validate(spec)
    assert result["valid"] is True
    assert result["executionAvailable"] is True
    assert result["capabilityId"] == "multilevel_model.gaussian.two_level"
