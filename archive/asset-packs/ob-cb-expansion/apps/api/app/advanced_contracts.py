from __future__ import annotations

import math
import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ContractModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class CommonAdvancedSpec(ContractModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    analysis_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
    name: str = Field(min_length=1, max_length=120)
    dataset_version_id: str | None = Field(default=None, pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,127}$")
    confidence_level: float = Field(default=0.95, gt=0.5, lt=1)
    seed: int = Field(default=20260714, ge=1, le=2_147_483_647)


class BetweenFactor(ContractModel):
    variable_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
    coding: Literal["treatment", "sum", "helmert"] = "sum"
    reference_level: str | int | float | None = None


class WithinFactor(ContractModel):
    id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
    name: str = Field(min_length=1, max_length=100)
    levels: list[str] = Field(min_length=2, max_length=20)
    columns: dict[str, str] = Field(description="被试内水平到宽格式变量 ID 的映射；长格式可为空。")

    @model_validator(mode="after")
    def validate_columns(self) -> "WithinFactor":
        if self.columns and set(self.columns) != set(self.levels):
            raise ValueError("withinFactors.columns 必须完整覆盖 levels，且不得包含额外水平")
        return self


class PlannedContrast(ContractModel):
    id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
    factor_variable_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
    weights: dict[str, float] = Field(min_length=2)
    multiplicity_family_id: str = Field(
        default="planned_contrasts", pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$"
    )

    @model_validator(mode="after")
    def validate_weights(self) -> "PlannedContrast":
        if len(self.weights) < 2:
            raise ValueError("PLANNED_CONTRAST_NEEDS_AT_LEAST_TWO_LEVELS")
        if any(not math.isfinite(weight) for weight in self.weights.values()):
            raise ValueError("PLANNED_CONTRAST_WEIGHTS_MUST_BE_FINITE")
        if sum(abs(weight) > 1e-12 for weight in self.weights.values()) < 2:
            raise ValueError("PLANNED_CONTRAST_NEEDS_TWO_NONZERO_WEIGHTS")
        if not math.isclose(sum(self.weights.values()), 0.0, abs_tol=1e-8):
            raise ValueError("PLANNED_CONTRAST_WEIGHTS_MUST_SUM_TO_ZERO")
        return self


class ExperimentalDesignSpec(CommonAdvancedSpec):
    family: Literal["experimental_design"]
    analysis_type: Literal["anova", "glm_cluster"] = "anova"
    design_type: Literal["factorial_anova", "ancova", "repeated_measures", "mixed_design"]
    data_layout: Literal["long", "wide"] = "long"
    outcome_ids: list[str] = Field(min_length=1)
    between_factors: list[BetweenFactor] = Field(default_factory=list)
    within_factors: list[WithinFactor] = Field(default_factory=list)
    subject_id: str | None = None
    covariate_ids: list[str] = Field(default_factory=list)
    sum_of_squares: Literal["II", "III"] = "III"
    sphericity_correction: Literal["auto", "greenhouse_geisser", "huynh_feldt"] = "auto"
    post_hoc_adjustment: Literal["holm", "tukey", "games_howell", "benjamini_hochberg"] = "holm"
    planned_contrasts: list[PlannedContrast] = Field(default_factory=list)
    covariate_centering: Literal["grand_mean", "none"] = "grand_mean"
    homogeneity_of_slopes: Literal["check_and_warn", "ignore"] = "check_and_warn"
    cluster_variable_id: str | None = Field(default=None, pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
    cluster_se: Literal["CR0"] = "CR0"

    @model_validator(mode="after")
    def validate_experiment_slice_1(self) -> "ExperimentalDesignSpec":
        if len(self.outcome_ids) != 1:
            raise ValueError("EXPERIMENT_MULTIPLE_OUTCOMES_NOT_SUPPORTED")
        if len(self.within_factors) > 1:
            raise ValueError("当前仅支持最多 1 个组内因子的重复测量设计")
        if len(self.between_factors) > 3:
            raise ValueError("当前仅支持最多 3 个组间因子")
        if len(self.between_factors) == 0 and len(self.within_factors) == 0:
            raise ValueError("必须提供至少一个因子")
        if self.post_hoc_adjustment == "games_howell":
            if self.design_type not in {"factorial_anova", "ancova"}:
                raise ValueError("GAMES_HOWELL_REQUIRES_BETWEEN_SUBJECTS_DESIGN")
            if len(self.between_factors) != 1 or self.within_factors or self.covariate_ids:
                raise ValueError("GAMES_HOWELL_REQUIRES_SINGLE_BETWEEN_FACTOR_NO_COVARIATES")
            if self.planned_contrasts:
                raise ValueError("GAMES_HOWELL_PLANNED_CONTRAST_NOT_SUPPORTED")
        if self.planned_contrasts:
            if len(self.between_factors) != 1 or self.within_factors or self.covariate_ids:
                raise ValueError("PLANNED_CONTRAST_REQUIRES_SINGLE_BETWEEN_FACTOR_NO_COVARIATES")
            factor_id = self.between_factors[0].variable_id
            if any(contrast.factor_variable_id != factor_id for contrast in self.planned_contrasts):
                raise ValueError("PLANNED_CONTRAST_FACTOR_NOT_DECLARED")
            contrast_ids = [contrast.id for contrast in self.planned_contrasts]
            if len(contrast_ids) != len(set(contrast_ids)):
                raise ValueError("plannedContrasts.id 不得重复")
        return self

    @model_validator(mode="after")
    def validate_design(self) -> "ExperimentalDesignSpec":
        if self.dataset_version_id is None:
            raise ValueError("实验分析必须指定 datasetVersionId")
        if self.analysis_type == "glm_cluster" and not self.cluster_variable_id:
            raise ValueError("GLM_CLUSTER_VARIABLE_REQUIRED")
        if self.design_type in {"factorial_anova", "ancova"} and not self.between_factors:
            raise ValueError("多因素 ANOVA/ANCOVA 至少需要一个 betweenFactor")
        if self.design_type == "ancova" and not self.covariate_ids:
            raise ValueError("ANCOVA 至少需要一个 covariateId")
        if self.design_type in {"repeated_measures", "mixed_design"}:
            if not self.subject_id:
                raise ValueError("重复测量或混合设计必须指定 subjectId")
            if not self.within_factors:
                raise ValueError("重复测量或混合设计至少需要一个 withinFactor")
        if self.design_type == "mixed_design" and not self.between_factors:
            raise ValueError("混合设计至少需要一个 betweenFactor")
        if self.data_layout == "wide" and any(not factor.columns for factor in self.within_factors):
            raise ValueError("宽格式重复测量数据必须为每个 withinFactor 提供 columns 映射")
        return self


class CenteringRule(ContractModel):
    variable_id: str
    method: Literal["none", "grand_mean", "group_mean"]


class RandomEffect(ContractModel):
    grouping_variable_id: str
    intercept: bool = True
    slope_variable_ids: list[str] = Field(default_factory=list)
    covariance: Literal["correlated", "diagonal"] = "correlated"


class MultilevelModelSpec(CommonAdvancedSpec):
    family: Literal["multilevel_model"]
    analysis_type: Literal["lmm", "aggregation"] = "lmm"
    outcome_id: str | None = None
    distribution: Literal["gaussian", "binomial", "poisson"] = "gaussian"
    cluster_variable_id: str
    higher_level_cluster_variable_id: str | None = None
    fixed_effect_ids: list[str] = Field(default_factory=list)
    random_effects: list[RandomEffect] = Field(default_factory=list)
    centering: list[CenteringRule] = Field(default_factory=list)
    estimator: Literal["REML", "ML", "MLR"] = "REML"
    degrees_of_freedom: Literal["satterthwaite", "kenward_roger", "asymptotic"] = "satterthwaite"
    minimum_cluster_count: int = Field(default=30, ge=10)
    scale_item_ids: list[str] = Field(default_factory=list)
    scale_min: float = 1.0
    scale_max: float = 5.0
    aggregation_method: Literal["mean", "sum"] = "mean"

    @model_validator(mode="after")
    def validate_multilevel(self) -> "MultilevelModelSpec":
        if self.dataset_version_id is None:
            raise ValueError("多层模型必须指定 datasetVersionId")
        if self.higher_level_cluster_variable_id:
            raise ValueError("MLM_THREE_LEVEL_NOT_SUPPORTED")
        if self.analysis_type == "aggregation":
            if len(self.scale_item_ids) < 2:
                raise ValueError("AGGREGATION_SCALE_ITEMS_REQUIRED")
            if len(self.scale_item_ids) != len(set(self.scale_item_ids)):
                raise ValueError("scaleItemIds 不得重复")
            if self.scale_max <= self.scale_min:
                raise ValueError("AGGREGATION_SCALE_RANGE_INVALID")
            return self
        if self.outcome_id is None:
            raise ValueError("LMM_OUTCOME_REQUIRED")
        if not self.fixed_effect_ids:
            raise ValueError("LMM_FIXED_EFFECTS_REQUIRED")
        if not self.random_effects:
            raise ValueError("LMM_RANDOM_EFFECTS_REQUIRED")
        if self.distribution != "gaussian":
            raise ValueError("当前仅支持 gaussian 分布的 LMM")
        grouping_ids = {effect.grouping_variable_id for effect in self.random_effects}
        valid_groups = {self.cluster_variable_id, self.higher_level_cluster_variable_id}
        if not grouping_ids.issubset(valid_groups):
            raise ValueError("randomEffects 只能引用已声明的聚类变量")
        return self


class LongitudinalWave(ContractModel):
    wave: str = Field(min_length=1, max_length=40)
    time_value: float
    variables: dict[str, str] = Field(
        min_length=1,
        description="稳定构念/角色 ID 到该时间点变量 ID 的映射。",
    )


class LongitudinalModelSpec(CommonAdvancedSpec):
    family: Literal["longitudinal_model"]
    model_type: Literal[
        "growth_curve",
        "cross_lagged_panel",
        "ri_clpm",
        "latent_growth",
        "longitudinal_invariance",
    ]
    subject_id: str
    group_variable_id: str | None = Field(default=None, pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
    time_variable_id: str | None = None
    waves: list[LongitudinalWave] = Field(min_length=2)
    estimator: Literal["ML", "MLR", "WLSMV"] = "MLR"
    missing: Literal["fiml", "complete_cases", "available_rows_ml"] = "fiml"
    invariance_levels: list[Literal["configural", "metric", "scalar", "strict"]] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_longitudinal(self) -> "LongitudinalModelSpec":
        if self.dataset_version_id is None:
            raise ValueError("纵向模型必须指定 datasetVersionId")
        if self.estimator == "WLSMV" and self.missing == "fiml":
            raise ValueError("WLSMV 纵向模型不能使用 FIML")
        if self.model_type == "growth_curve" and self.missing == "fiml":
            raise ValueError("LONGITUDINAL_FIML_NOT_SUPPORTED_FOR_OBSERVED_GROWTH")
        if self.model_type == "longitudinal_invariance" and not self.group_variable_id:
            raise ValueError("LONGITUDINAL_INVARIANCE_GROUP_REQUIRED")
        if self.model_type != "growth_curve" and self.missing == "available_rows_ml":
            raise ValueError("LONGITUDINAL_AVAILABLE_ROWS_ONLY_FOR_OBSERVED_GROWTH")
        wave_ids = [wave.wave for wave in self.waves]
        if len(wave_ids) != len(set(wave_ids)):
            raise ValueError("waves.wave 必须唯一")
        time_values = [wave.time_value for wave in self.waves]
        if len(time_values) != len(set(time_values)):
            raise ValueError("waves.timeValue 必须唯一")
        construct_sets = [set(wave.variables) for wave in self.waves]
        if any(keys != construct_sets[0] for keys in construct_sets[1:]):
            raise ValueError("每个 wave 必须提供相同的稳定构念/角色键")
        if self.model_type == "ri_clpm" and len(construct_sets[0]) != 2:
            raise ValueError("RI-CLPM 当前需要恰好两个稳定构念")
        minimum_waves = (
            3
            if self.model_type in {"growth_curve", "latent_growth", "ri_clpm", "cross_lagged_panel"}
            else 2
        )
        if len(self.waves) < minimum_waves:
            if self.model_type == "cross_lagged_panel":
                raise ValueError("LONGITUDINAL_INSUFFICIENT_WAVES_FOR_SUPPORTED_CLPM")
            raise ValueError(f"{self.model_type} 至少需要 {minimum_waves} 个时间点")
        return self


class ImputationVariable(ContractModel):
    variable_id: str
    method: Literal[
        "auto",
        "pmm",
        "normal",
        "logistic",
        "multinomial_logistic",
        "ordinal_logistic",
        "cart",
        "two_level_normal",
        "two_level_binary",
    ] = "auto"
    predictor_ids: list[str] = Field(default_factory=list)


class PassiveRule(ContractModel):
    target_variable_id: str
    expression: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_expression(self) -> "PassiveRule":
        if re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_-]{0,63}\s*\*\s*[A-Za-z][A-Za-z0-9_-]{0,63}",
            self.expression,
        ) is None:
            raise ValueError("PASSIVE_EXPRESSION_NOT_SUPPORTED: only variable * variable is allowed")
        return self


class PooledAnalysisSpec(ContractModel):
    model_type: Literal["linear_regression"] = "linear_regression"
    outcome_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
    predictor_ids: list[str] = Field(min_length=1)
    include_intercept: bool = True

    @model_validator(mode="after")
    def validate_predictors(self) -> "PooledAnalysisSpec":
        if len(self.predictor_ids) != len(set(self.predictor_ids)):
            raise ValueError("pooledAnalysis.predictorIds 不得重复")
        if self.outcome_id in self.predictor_ids:
            raise ValueError("pooledAnalysis.outcomeId 不得同时作为 predictor")
        return self


class MultipleImputationSpec(CommonAdvancedSpec):
    family: Literal["multiple_imputation"]
    method: Literal["mice_fcs", "joint_model"] = "mice_fcs"
    imputations: int = Field(default=20, ge=5, le=200)
    iterations: int = Field(default=20, ge=5, le=100)
    variables: list[ImputationVariable] = Field(min_length=1)
    passive_rules: list[PassiveRule] = Field(default_factory=list)
    cluster_variable_id: str | None = None
    pooling: Literal["none", "rubin"] = "none"
    pooled_analysis: PooledAnalysisSpec | None = None
    diagnostics: list[
        Literal["trace", "distribution", "overimputation", "fraction_missing_information"]
    ] = Field(default_factory=lambda: ["trace", "distribution"])

    @field_validator("pooling", mode="before")
    @classmethod
    def reject_pooling(cls, value: object) -> object:
        if value not in {"none", "rubin"}:
            raise ValueError("MI_POOLING_METHOD_NOT_SUPPORTED")
        return value

    @model_validator(mode="after")
    def validate_imputation(self) -> "MultipleImputationSpec":
        if self.dataset_version_id is None:
            raise ValueError("多重插补必须指定 datasetVersionId")
        if self.method != "mice_fcs":
            raise ValueError("JOINT_MODEL_NOT_SUPPORTED")
        if self.pooling == "rubin" and self.pooled_analysis is None:
            raise ValueError("MI_RUBIN_ANALYSIS_REQUIRED")
        if self.pooling == "none" and self.pooled_analysis is not None:
            raise ValueError("MI_POOLED_ANALYSIS_REQUIRES_RUBIN")
        variable_ids = [variable.variable_id for variable in self.variables]
        if len(variable_ids) != len(set(variable_ids)):
            raise ValueError("variables.variableId 不得重复")
        uses_two_level = any(
            variable.method.startswith("two_level_") for variable in self.variables
        )
        if uses_two_level and not self.cluster_variable_id:
            raise ValueError("两层插补方法必须指定 clusterVariableId")
        passive_targets = [rule.target_variable_id for rule in self.passive_rules]
        if len(passive_targets) != len(set(passive_targets)):
            raise ValueError("passiveRules.targetVariableId 不得重复")
        return self


class EffectSize(ContractModel):
    metric: Literal[
        "cohens_d",
        "cohens_f",
        "cohens_f2",
        "r_squared_change",
        "indirect_effect",
        "standardized_path",
        "odds_ratio",
        "intraclass_correlation",
    ]
    value: float = Field(gt=0)


class MonteCarloParameters(ContractModel):
    data_generation: dict[str, Any] = Field(description="生成数据的核心参数")
    estimand_target: str = Field(description="需要检验功效的效应项")
    missing_mechanism: dict[str, Any] | None = None
    cluster_allocation: dict[str, Any] | None = None
    repeated_measures_cov: dict[str, Any] | None = None
    convergence_failure_handling: Literal["drop", "fail"] = "drop"


class PowerAnalysisSpec(CommonAdvancedSpec):
    family: Literal["power_analysis"]
    design_family: Literal[
        "regression",
        "t_test",
        "mediation",
        "moderation",
        "factorial_anova",
        "repeated_measures",
        "multilevel",
        "sem",
    ]
    method: Literal["analytic", "monte_carlo"] = "analytic"
    solve_for: Literal["sample_size", "power", "effect_size"] = "sample_size"
    alpha: float = Field(default=0.05, gt=0, lt=0.5)
    target_power: float = Field(default=0.8, gt=0.5, lt=1)
    sample_size: int | None = Field(default=None, ge=4)
    effect_size: EffectSize | None = None
    groups: int = Field(default=1, ge=1)
    predictors: int = Field(default=1, ge=1)
    measurements: int | None = Field(default=None, ge=2)
    clusters: int | None = Field(default=None, ge=10)
    average_cluster_size: float | None = Field(default=None, gt=1)
    simulations: int = Field(default=5000, ge=1000, le=100000)
    alternative: Literal["two_sided", "one_sided"] = "two_sided"
    effect_size_metric: Literal["cohens_d", "cohens_f", "cohens_f2", "r_squared_change"] | None = (
        None
    )
    allocation_ratio: float | None = Field(default=None, gt=0)
    rounding_rule: Literal["ceil"] = "ceil"
    assumptions: list[str] = Field(default_factory=list)
    monte_carlo_parameters: MonteCarloParameters | None = None

    @model_validator(mode="after")
    def validate_power(self) -> "PowerAnalysisSpec":
        if self.method == "monte_carlo":
            if self.design_family not in {"regression", "factorial_anova"}:
                raise ValueError("POWER_MONTE_CARLO_NOT_SUPPORTED")
            if self.monte_carlo_parameters is None:
                raise ValueError("POWER_MONTE_CARLO_PARAMETERS_REQUIRED")
        elif self.design_family not in {"regression", "factorial_anova", "t_test"}:
            raise ValueError("POWER_DESIGN_NOT_SUPPORTED")
        if self.alternative == "one_sided" and self.design_family in {
            "regression",
            "factorial_anova",
        }:
            raise ValueError(
                "POWER_DESIGN_NOT_SUPPORTED: regression 和 factorial_anova 的功效分析不支持单侧检验"
            )
        if self.design_family == "t_test" and self.alternative == "one_sided":
            raise ValueError("POWER_T_TEST_DIRECTION_REQUIRED")
        if self.design_family == "t_test" and self.groups not in {1, 2}:
            raise ValueError("POWER_T_TEST_GROUP_COUNT_INVALID")
        if self.design_family == "factorial_anova" and self.groups < 2:
            raise ValueError("POWER_GROUP_COUNT_INVALID")
        valid_metrics = {
            "regression": {"cohens_f2", "r_squared_change"},
            "factorial_anova": {"cohens_f"},
            "t_test": {"cohens_d"},
        }
        allowed = valid_metrics[self.design_family]
        if self.effect_size is not None:
            if self.effect_size.metric not in allowed:
                raise ValueError("POWER_EFFECT_METRIC_NOT_SUPPORTED")
            if self.effect_size.metric == "r_squared_change" and self.effect_size.value >= 1:
                raise ValueError("POWER_R_SQUARED_CHANGE_INVALID")
        if self.effect_size_metric is not None and self.effect_size_metric not in allowed:
            raise ValueError("POWER_EFFECT_METRIC_NOT_SUPPORTED")
        if self.solve_for == "effect_size":
            if self.effect_size_metric is None:
                raise ValueError("POWER_EFFECT_METRIC_REQUIRED")
            if self.effect_size is not None:
                raise ValueError("POWER_EFFECT_SIZE_VALUE_NOT_APPLICABLE")
        else:
            if self.effect_size is None:
                raise ValueError("计算 power 或 sample_size 时必须提供 effectSize")
            if (
                self.effect_size_metric is not None
                and self.effect_size_metric != self.effect_size.metric
            ):
                raise ValueError("POWER_EFFECT_METRIC_MISMATCH")
        if self.allocation_ratio is not None:
            raise ValueError("POWER_ALLOCATION_NOT_SUPPORTED")
        if self.solve_for != "sample_size" and self.sample_size is None:
            raise ValueError("计算 power 或 effect_size 时必须提供 sampleSize")
        if self.design_family == "regression" and self.sample_size is not None:
            if self.sample_size <= self.predictors + 1:
                raise ValueError("POWER_SAMPLE_SIZE_TOO_SMALL")
        if self.design_family == "factorial_anova" and self.sample_size is not None:
            if self.sample_size < self.groups * 2:
                raise ValueError("POWER_SAMPLE_SIZE_TOO_SMALL")
            if self.sample_size % self.groups != 0:
                raise ValueError("POWER_SAMPLE_SIZE_NOT_DIVISIBLE_BY_GROUPS")
        if self.design_family == "t_test" and self.sample_size is not None:
            if self.sample_size < self.groups * 2:
                raise ValueError("POWER_SAMPLE_SIZE_TOO_SMALL")
            if self.groups == 2 and self.sample_size % self.groups != 0:
                raise ValueError("POWER_SAMPLE_SIZE_NOT_DIVISIBLE_BY_GROUPS")
        return self


class MeasurementConstruct(ContractModel):
    id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
    label: str = Field(min_length=1, max_length=120)
    item_ids: list[str] = Field(min_length=2)
    score_id: str | None = Field(default=None, pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")

    @field_validator("item_ids")
    @classmethod
    def validate_item_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("construct.itemIds 不得重复")
        return value


class QuestionnaireMeasurementSpec(CommonAdvancedSpec):
    family: Literal["questionnaire_measurement"]
    model_type: Literal[
        "reliability",
        "efa",
        "cfa",
        "measurement_invariance",
        "esem_bifactor_irt",
        "bifactor",
        "esem",
        "irt",
        "common_method_bias",
        "marker_variable",
        "ulmc",
    ]
    item_ids: list[str] = Field(min_length=3)
    constructs: list[MeasurementConstruct] = Field(min_length=2)
    group_variable_id: str | None = Field(default=None, pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
    marker_variable_id: str | None = None
    estimator: Literal["ML", "MLR", "WLSMV"] = "ML"
    item_scale: Literal["continuous", "ordinal"] = "continuous"
    factor_count: int = Field(default=2, ge=1, le=20)
    rotation: Literal["varimax", "promax"] = "promax"
    extraction_method: Literal["ml", "paf", "minres"] = "ml"
    parallel_iterations: int = Field(default=1000, ge=100, le=10000)
    invariance_levels: list[Literal["configural", "metric", "scalar", "strict"]] = Field(
        default_factory=lambda: ["configural", "metric", "scalar"]
    )
    partial_released_parameters: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_measurement(self) -> "QuestionnaireMeasurementSpec":
        if self.dataset_version_id is None:
            raise ValueError("问卷测量分析必须指定 datasetVersionId")
        if len(self.item_ids) != len(set(self.item_ids)):
            raise ValueError("itemIds 不得重复")
        construct_ids = [construct.id for construct in self.constructs]
        if len(construct_ids) != len(set(construct_ids)):
            raise ValueError("constructs.id 不得重复")
        declared_items = set(self.item_ids)
        referenced_items = {
            item_id for construct in self.constructs for item_id in construct.item_ids
        }
        if not referenced_items.issubset(declared_items):
            raise ValueError("construct.itemIds 必须属于 itemIds")
        if len(self.constructs) < 2:
            raise ValueError("问卷高级测量至少需要两个构念")
        if self.model_type in {"bifactor", "esem", "esem_bifactor_irt"}:
            if len(referenced_items) < 4 or any(
                len(construct.item_ids) < 2 for construct in self.constructs
            ):
                raise ValueError("ESEM/Bifactor 至少需要两个各含两个题项的构念")
        if self.item_scale == "ordinal" and self.estimator != "WLSMV":
            raise ValueError("有序题项必须使用 WLSMV 估计器")
        if self.item_scale == "continuous" and self.estimator == "WLSMV":
            raise ValueError("连续题项不得使用 WLSMV 估计器")
        if self.model_type == "marker_variable" and not self.marker_variable_id:
            raise ValueError("Marker Variable 分析必须指定 markerVariableId")
        if self.model_type == "measurement_invariance" and not self.group_variable_id:
            raise ValueError("MEASUREMENT_INVARIANCE_GROUP_REQUIRED")
        return self


AdvancedAnalysisSpec = Annotated[
    ExperimentalDesignSpec
    | MultilevelModelSpec
    | LongitudinalModelSpec
    | MultipleImputationSpec
    | PowerAnalysisSpec
    | QuestionnaireMeasurementSpec,
    Field(discriminator="family"),
]


class AdvancedAnalysisRequest(ContractModel):
    dataset_id: str | None = None
    spec: AdvancedAnalysisSpec

    @model_validator(mode="after")
    def validate_dataset_identity(self) -> "AdvancedAnalysisRequest":
        spec_dataset = getattr(self.spec, "dataset_version_id", None)
        if self.dataset_id and spec_dataset and self.dataset_id != spec_dataset:
            raise ValueError("datasetId 必须与 spec.datasetVersionId 一致")
        if getattr(self.spec, "family", None) != "power_analysis" and not self.dataset_id:
            raise ValueError("除功效分析外，运行请求必须指定 datasetId")
        return self
