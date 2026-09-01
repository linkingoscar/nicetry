import pytest

from app.advanced_contracts import CenteringRule, MultilevelModelSpec, RandomEffect


def test_mlm_rejects_three_levels():
    with pytest.raises(ValueError, match="MLM_THREE_LEVEL_NOT_SUPPORTED"):
        MultilevelModelSpec(
            analysis_id="test",
            name="test",
            dataset_version_id="dataset1",
            family="multilevel_model",
            outcome_id="out",
            distribution="gaussian",
            cluster_variable_id="level2",
            higher_level_cluster_variable_id="level3",
            fixed_effect_ids=["pred"],
            random_effects=[RandomEffect(grouping_variable_id="level2")],
            estimator="REML",
            degrees_of_freedom="satterthwaite",
            minimum_cluster_count=30,
        )


def test_mlm_rejects_non_gaussian():
    with pytest.raises(ValueError, match="当前仅支持 gaussian 分布的 LMM"):
        MultilevelModelSpec(
            analysis_id="test",
            name="test",
            dataset_version_id="dataset1",
            family="multilevel_model",
            outcome_id="out",
            distribution="binomial",
            cluster_variable_id="level2",
            fixed_effect_ids=["pred"],
            random_effects=[RandomEffect(grouping_variable_id="level2")],
            estimator="ML",
            degrees_of_freedom="satterthwaite",
            minimum_cluster_count=30,
        )


def test_mlm_rejects_invalid_random_effect_grouping():
    with pytest.raises(ValueError, match="randomEffects 只能引用已声明的聚类变量"):
        MultilevelModelSpec(
            analysis_id="test",
            name="test",
            dataset_version_id="dataset1",
            family="multilevel_model",
            outcome_id="out",
            distribution="gaussian",
            cluster_variable_id="level2",
            fixed_effect_ids=["pred"],
            random_effects=[RandomEffect(grouping_variable_id="wrong_level")],
            estimator="REML",
            degrees_of_freedom="satterthwaite",
            minimum_cluster_count=30,
        )


def test_mlm_group_mean_centering_is_explicitly_declared() -> None:
    spec = MultilevelModelSpec(
        analysis_id="test",
        name="test",
        dataset_version_id="dataset1",
        family="multilevel_model",
        outcome_id="out",
        distribution="gaussian",
        cluster_variable_id="level2",
        fixed_effect_ids=["pred"],
        random_effects=[RandomEffect(grouping_variable_id="level2")],
        centering=[CenteringRule(variable_id="pred", method="group_mean")],
    )

    assert spec.centering[0].variable_id == "pred"
    assert "pred__between" not in spec.fixed_effect_ids
