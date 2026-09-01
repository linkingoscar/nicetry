import pytest

from app.advanced_contracts import (
    BetweenFactor,
    ExperimentalDesignSpec,
    PlannedContrast,
    WithinFactor,
)


def test_experiment_spec_rejects_multiple_outcomes():
    with pytest.raises(ValueError, match="EXPERIMENT_MULTIPLE_OUTCOMES_NOT_SUPPORTED"):
        ExperimentalDesignSpec(
            analysis_id="test",
            name="test",
            dataset_version_id="dataset1",
            family="experimental_design",
            design_type="factorial_anova",
            data_layout="long",
            outcome_ids=["out1", "out2"],
            between_factors=[BetweenFactor(variable_id="var_x", coding="sum")],
        )


def test_experiment_spec_rejects_multiple_within_subjects():
    with pytest.raises(ValueError, match="当前仅支持最多 1 个组内因子的重复测量设计"):
        ExperimentalDesignSpec(
            analysis_id="test",
            name="test",
            dataset_version_id="dataset1",
            family="experimental_design",
            design_type="repeated_measures",
            data_layout="long",
            outcome_ids=["out1"],
            within_factors=[
                WithinFactor(
                    id="var_w", name="w", levels=["a", "b"], columns={"a": "w_a", "b": "w_b"}
                ),
                WithinFactor(
                    id="var_w2", name="w2", levels=["x", "y"], columns={"x": "w_x", "y": "w_y"}
                ),
            ],
            subject_id="subj",
        )


def test_experiment_spec_requires_between_factors_for_slice():
    with pytest.raises(ValueError, match="必须提供至少一个因子"):
        ExperimentalDesignSpec(
            analysis_id="test",
            name="test",
            dataset_version_id="dataset1",
            family="experimental_design",
            design_type="factorial_anova",
            data_layout="long",
            outcome_ids=["out1"],
            between_factors=[],
            within_factors=[],
        )


def test_experiment_spec_accepts_games_howell_for_single_between_factor():
    spec = ExperimentalDesignSpec(
        analysis_id="test",
        name="test",
        dataset_version_id="dataset1",
        family="experimental_design",
        design_type="factorial_anova",
        outcome_ids=["out1"],
        between_factors=[BetweenFactor(variable_id="var_x", coding="sum")],
        post_hoc_adjustment="games_howell",
    )
    assert spec.post_hoc_adjustment == "games_howell"


def test_experiment_spec_rejects_games_howell_for_adjusted_or_within_design():
    with pytest.raises(
        ValueError, match="GAMES_HOWELL_REQUIRES_SINGLE_BETWEEN_FACTOR_NO_COVARIATES"
    ):
        ExperimentalDesignSpec(
            analysis_id="test",
            name="test",
            dataset_version_id="dataset1",
            family="experimental_design",
            design_type="ancova",
            outcome_ids=["out1"],
            between_factors=[BetweenFactor(variable_id="var_x", coding="sum")],
            covariate_ids=["cov1"],
            post_hoc_adjustment="games_howell",
        )


def test_experiment_spec_validates_planned_contrast_weights_and_scope():
    spec = ExperimentalDesignSpec(
        analysis_id="planned_contrast_test",
        name="Planned contrast",
        dataset_version_id="dataset1",
        family="experimental_design",
        design_type="factorial_anova",
        outcome_ids=["out1"],
        between_factors=[BetweenFactor(variable_id="condition", coding="sum")],
        planned_contrasts=[
            PlannedContrast(
                id="active_vs_control",
                factor_variable_id="condition",
                weights={"A": 1.0, "B": -1.0, "C": 0.0},
            )
        ],
    )
    assert spec.planned_contrasts[0].multiplicity_family_id == "planned_contrasts"

    with pytest.raises(ValueError, match="PLANNED_CONTRAST_WEIGHTS_MUST_SUM_TO_ZERO"):
        PlannedContrast(
            id="invalid_weights",
            factor_variable_id="condition",
            weights={"A": 1.0, "B": 1.0},
        )

    with pytest.raises(
        ValueError, match="PLANNED_CONTRAST_REQUIRES_SINGLE_BETWEEN_FACTOR_NO_COVARIATES"
    ):
        ExperimentalDesignSpec(
            analysis_id="planned_contrast_with_covariate",
            name="Planned contrast with covariate",
            dataset_version_id="dataset1",
            family="experimental_design",
            design_type="ancova",
            outcome_ids=["out1"],
            between_factors=[BetweenFactor(variable_id="condition")],
            covariate_ids=["age"],
            planned_contrasts=[
                PlannedContrast(
                    id="active_vs_control",
                    factor_variable_id="condition",
                    weights={"A": 1.0, "B": -1.0},
                )
            ],
        )


def test_experiment_spec_validates_ancova():
    spec = ExperimentalDesignSpec(
        analysis_id="test",
        name="test",
        dataset_version_id="dataset1",
        family="experimental_design",
        design_type="ancova",
        data_layout="long",
        outcome_ids=["out1"],
        between_factors=[BetweenFactor(variable_id="var_x", coding="sum")],
        covariate_ids=["cov1"],
        covariate_centering="grand_mean",
        homogeneity_of_slopes="check_and_warn",
    )
    assert spec.covariate_centering == "grand_mean"
    assert spec.homogeneity_of_slopes == "check_and_warn"
