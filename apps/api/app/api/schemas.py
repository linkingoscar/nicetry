from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.analysis_context_contracts import ContractBaseModel
from app.empirical_procedure_contracts import EmpiricalProcedure
from app.study_plan_contracts import StudyPlanBinding


class AnalysisRequest(BaseModel):
    dataset_id: str
    model_spec: dict[str, Any]


class AnalysisRunRequest(ContractBaseModel):
    study_plan_binding: StudyPlanBinding | None = None


ConfirmedVariableType = Literal[
    "continuous", "binary", "nominal", "ordinal", "likert", "id", "text"
]


class DictionaryVariableUpdate(BaseModel):
    id: str
    confirmed_type: ConfirmedVariableType


class DictionaryUpdateRequest(BaseModel):
    variables: list[DictionaryVariableUpdate]


class ConstructInput(BaseModel):
    id: str = Field(pattern=r"^construct_[a-z0-9_-]{1,50}$")
    name: str = Field(min_length=1, max_length=100)
    item_ids: list[str] = Field(min_length=2)
    reverse_item_ids: list[str] = Field(default_factory=list)
    theoretical_minimum: float
    theoretical_maximum: float
    aggregation: Literal["mean", "sum"] = "mean"
    minimum_valid_proportion: float = Field(default=0.8, gt=0, le=1)


class MeasurementUpdateRequest(BaseModel):
    constructs: list[ConstructInput] = Field(min_length=1)
    change_note: str | None = Field(default=None, max_length=500)


class ModelDraftRequest(BaseModel):
    model_spec: dict[str, Any]


class ModelFreezeRequest(ModelDraftRequest):
    override_reason: str | None = Field(default=None, max_length=1000)


class LongitudinalWaveInput(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    time_value: float
    x_variable_id: str | None = None
    y_variable_id: str | None = None
    x_item_ids: list[str] = Field(default_factory=list, max_length=20)
    y_item_ids: list[str] = Field(default_factory=list, max_length=20)


class LongitudinalPowerInput(BaseModel):
    sample_sizes: list[int] = Field(
        default_factory=lambda: [200, 300, 500, 800],
        min_length=1,
        max_length=12,
    )
    replications: int = Field(default=500, ge=20, le=5000)
    target_power: float = Field(default=0.8, gt=0, lt=1)
    alpha: float = Field(default=0.05, gt=0, lt=0.5)
    autoregressive_x: float = Field(default=0.4, gt=-0.99, lt=0.99)
    autoregressive_y: float = Field(default=0.4, gt=-0.99, lt=0.99)
    cross_lagged_x_to_y: float = Field(default=0.1, gt=-0.99, lt=0.99)
    cross_lagged_y_to_x: float = Field(default=0.1, gt=-0.99, lt=0.99)
    icc: float = Field(default=0.4, gt=0, lt=1)
    random_intercept_correlation: float = Field(default=0.3, gt=-0.99, lt=0.99)
    within_correlation: float = Field(default=0.2, gt=-0.99, lt=0.99)
    reliability: float = Field(default=0.8, gt=0, le=1)
    estimate_measurement_error: bool = False
    seed: int = Field(default=20260714, ge=1, le=2_147_483_647)

    @model_validator(mode="after")
    def validate_power(self) -> "LongitudinalPowerInput":
        if len(set(self.sample_sizes)) != len(self.sample_sizes):
            raise ValueError("纵向功效分析的候选样本量不得重复")
        if self.sample_sizes != sorted(self.sample_sizes):
            raise ValueError("纵向功效分析的候选样本量必须升序排列")
        if min(self.sample_sizes) < 50 or max(self.sample_sizes) > 10000:
            raise ValueError("纵向功效分析的候选样本量须介于 50–10000")
        if self.estimate_measurement_error and self.reliability >= 1:
            raise ValueError("显式估计测量误差时，生成模型信度必须小于 1")
        if len(self.sample_sizes) * self.replications > 5000:
            raise ValueError("纵向功效分析最多运行 5000 个样本量×重复模拟条件")
        return self


class LongitudinalPanelInput(BaseModel):
    model_type: Literal["clpm", "ri_clpm", "lcm_sr"] = "ri_clpm"
    measurement_mode: Literal["observed_scores", "latent_items"] = "observed_scores"
    subject_variable_id: str
    waves: list[LongitudinalWaveInput] = Field(min_length=2, max_length=10)
    estimator: Literal["ML", "MLR", "WLSMV"] = "MLR"
    missing: Literal["fiml", "complete_cases"] = "fiml"
    constrain_across_time: bool = False
    growth_shape: Literal["linear", "quadratic"] = "linear"
    indicator_scale: Literal["continuous", "ordinal"] = "continuous"
    invariance_level: Literal["none", "configural", "metric", "scalar", "strict"] = "strict"
    partial_invariance_positions: list[str] = Field(default_factory=list, max_length=20)
    cmb_sensitivity: Literal["none", "global_ulmc"] = "none"
    compare_competing_models: bool = True
    run_robustness_checks: bool = True
    power_analysis: LongitudinalPowerInput | None = None

    @model_validator(mode="after")
    def validate_panel(self) -> "LongitudinalPanelInput":
        if self.model_type == "ri_clpm" and len(self.waves) < 3:
            raise ValueError("RI-CLPM 至少需要三个时间点")
        if self.model_type == "lcm_sr" and len(self.waves) < 5:
            raise ValueError("LCM-SR 至少需要五个时间点")
        if self.model_type == "lcm_sr" and self.measurement_mode != "latent_items":
            raise ValueError("LCM-SR 当前要求题项级潜变量测量模式")
        if self.growth_shape == "quadratic" and self.model_type != "lcm_sr":
            raise ValueError("二次潜在生长轨迹仅适用于 LCM-SR")
        if self.cmb_sensitivity == "global_ulmc" and self.measurement_mode != "latent_items":
            raise ValueError("纵向 ULMC 敏感性分析要求题项级潜变量模式")
        if self.cmb_sensitivity == "global_ulmc" and self.indicator_scale != "continuous":
            raise ValueError("纵向 ULMC 敏感性分析当前要求连续近似题项与 ML/MLR")
        if self.cmb_sensitivity == "global_ulmc" and self.invariance_level not in {
            "scalar",
            "strict",
        }:
            raise ValueError("纵向 ULMC 敏感性分析必须事先请求标量或严格测量等值性")
        if self.power_analysis is not None and self.model_type != "ri_clpm":
            raise ValueError("当前蒙特卡洛纵向功效分析针对三时点及以上 RI-CLPM")
        if self.power_analysis is not None and self.estimator == "WLSMV":
            raise ValueError("当前 RI-CLPM 功效模拟使用连续 ML/MLR，不适用于 WLSMV")
        labels = [wave.label for wave in self.waves]
        if len(labels) != len(set(labels)):
            raise ValueError("纵向模型的波次标签不得重复")
        times = [wave.time_value for wave in self.waves]
        if len(times) != len(set(times)):
            raise ValueError("纵向模型的时间值不得重复")
        if times != sorted(times):
            raise ValueError("纵向模型的波次必须按时间升序排列")
        if self.measurement_mode == "observed_scores":
            variable_ids = [
                variable_id
                for wave in self.waves
                for variable_id in (wave.x_variable_id, wave.y_variable_id)
                if variable_id
            ]
            if len(variable_ids) != 2 * len(self.waves):
                raise ValueError("观测得分纵向模型必须为每个波次指定 X/Y 数据列")
            if len(variable_ids) != len(set(variable_ids)):
                raise ValueError("每个波次的 X/Y 必须映射到不同的数据列")
            if self.estimator == "WLSMV" or self.indicator_scale == "ordinal":
                raise ValueError("观测得分模式当前仅支持连续变量的 ML/MLR 估计")
            if self.invariance_level != "strict" or self.partial_invariance_positions:
                raise ValueError("测量等值性设置仅适用于题项级潜变量模式")
        else:
            x_counts = {len(wave.x_item_ids) for wave in self.waves}
            y_counts = {len(wave.y_item_ids) for wave in self.waves}
            if min(x_counts | y_counts, default=0) < 2:
                raise ValueError("潜变量模式下每个构念每个波次至少需要两个题项")
            if len(x_counts) != 1 or len(y_counts) != 1:
                raise ValueError("潜变量模式要求同一构念在各波次使用相同数量的对应题项")
            item_ids = [
                item_id for wave in self.waves for item_id in (*wave.x_item_ids, *wave.y_item_ids)
            ]
            if len(item_ids) != len(set(item_ids)):
                raise ValueError("题项级纵向模型的每个波次题项必须映射到不同的数据列")
            if self.indicator_scale == "ordinal" and self.estimator != "WLSMV":
                raise ValueError("有序题项必须使用 WLSMV 估计")
            if self.estimator == "WLSMV" and self.missing == "fiml":
                raise ValueError("WLSMV 不支持 FIML；请选择完整案例")
            valid_positions = {
                f"{construct}:{position}"
                for construct, count in (("x", next(iter(x_counts))), ("y", next(iter(y_counts))))
                for position in range(1, count + 1)
            }
            invalid_positions = set(self.partial_invariance_positions) - valid_positions
            if invalid_positions:
                raise ValueError("部分等值位置无效: " + ", ".join(sorted(invalid_positions)))
        return self


class DiaryReliabilityConstructInput(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    item_ids: list[str] = Field(min_length=2, max_length=20)


class DiaryPowerInput(BaseModel):
    person_counts: list[int] = Field(
        default_factory=lambda: [50, 80, 120],
        min_length=1,
        max_length=8,
    )
    observations_per_person: list[int] = Field(
        default_factory=lambda: [7, 10, 14],
        min_length=1,
        max_length=8,
    )
    replications: int = Field(default=500, ge=20, le=5000)
    target_power: float = Field(default=0.8, gt=0, lt=1)
    alpha: float = Field(default=0.05, gt=0, lt=0.5)
    within_effect: float = Field(default=0.15, gt=-5, lt=5)
    between_effect: float = Field(default=0.2, gt=-5, lt=5)
    random_intercept_sd: float = Field(default=0.5, ge=0, le=10)
    random_slope_sd: float = Field(default=0.1, ge=0, le=10)
    residual_sd: float = Field(default=1.0, gt=0, le=10)
    predictor_between_sd: float = Field(default=0.7, gt=0, le=10)
    predictor_within_sd: float = Field(default=1.0, gt=0, le=10)
    residual_ar1: float = Field(default=0.2, gt=-0.99, lt=0.99)
    seed: int = Field(default=20260714, ge=1, le=2_147_483_647)

    @model_validator(mode="after")
    def validate_power(self) -> "DiaryPowerInput":
        if len(set(self.person_counts)) != len(self.person_counts):
            raise ValueError("ESM 功效分析的候选人数不得重复")
        if len(set(self.observations_per_person)) != len(self.observations_per_person):
            raise ValueError("ESM 功效分析的候选测量次数不得重复")
        if self.person_counts != sorted(self.person_counts):
            raise ValueError("ESM 功效分析的候选人数必须升序排列")
        if self.observations_per_person != sorted(self.observations_per_person):
            raise ValueError("ESM 功效分析的候选测量次数必须升序排列")
        if min(self.person_counts) < 20 or max(self.person_counts) > 5000:
            raise ValueError("ESM 功效分析的候选人数须介于 20–5000")
        if min(self.observations_per_person) < 3:
            raise ValueError("ESM 功效分析每人至少需要三个测量时点")
        if len(self.person_counts) * len(self.observations_per_person) * self.replications > 5000:
            raise ValueError("ESM 功效分析最多运行 5000 个设计条件×重复模拟")
        return self


class DiaryDsemInput(BaseModel):
    chains: int = Field(default=4, ge=2, le=8)
    iterations: int = Field(default=2000, ge=400, le=20000)
    warmup: int = Field(default=1000, ge=200, le=10000)
    thin: int = Field(default=1, ge=1, le=20)
    prior_mean_sd: float = Field(default=1.0, gt=0, le=10)
    prior_scale: float = Field(default=1.0, gt=0, le=10)
    random_dynamic_slopes: bool = True
    plot_draws_per_chain: int = Field(default=300, ge=100, le=500)
    predictive_replications: int = Field(default=200, ge=100, le=500)
    run_prior_sensitivity: bool = True
    seed: int = Field(default=20260728, ge=1, le=2_147_483_647)

    @model_validator(mode="after")
    def validate_dsem(self) -> "DiaryDsemInput":
        if self.warmup >= self.iterations:
            raise ValueError("Bayesian DSEM 的 warmup 必须小于每链总迭代数")
        retained = (self.iterations - self.warmup) // self.thin
        if retained < 200:
            raise ValueError("Bayesian DSEM 每条链至少须保留 200 个后验抽样")
        if self.chains * self.iterations > 80000:
            raise ValueError("Bayesian DSEM 最多运行 80000 次链迭代")
        return self


class DiaryMultilevelInput(BaseModel):
    analysis_type: Literal["lmm", "glmm", "mediation", "bayesian_dsem"] = "lmm"
    subject_variable_id: str
    time_variable_id: str
    outcome_variable_id: str
    predictor_variable_id: str
    mediator_variable_id: str | None = None
    level2_covariate_ids: list[str] = Field(default_factory=list)
    control_variable_ids: list[str] = Field(default_factory=list)
    random_slope: bool = True
    residual_structure: Literal["independent", "ar1"] = "independent"
    outcome_family: Literal["gaussian", "binomial", "poisson", "negative_binomial"] = "gaussian"
    count_model: Literal["standard", "zero_inflated", "hurdle"] = "standard"
    zero_process_predictors: Literal["intercept_only", "shared"] = "intercept_only"
    distribution_diagnostic_simulations: int = Field(default=250, ge=100, le=2000)
    distribution_diagnostic_seed: int = Field(
        default=20260729, ge=1, le=2_147_483_647
    )
    cluster_structure: Literal["nested", "cross_classified"] = "nested"
    cross_class_variable_id: str | None = None
    exposure_variable_id: str | None = None
    centering: Literal["person_mean", "grand_mean", "none"] = "person_mean"
    mediation_type: Literal["1-1-1", "2-1-1"] = "1-1-1"
    temporal_effect: Literal["contemporaneous", "lagged", "both"] = "contemporaneous"
    lag_order: int = Field(default=1, ge=1, le=10)
    expected_time_interval: float | None = Field(default=None, gt=0)
    time_interval_tolerance: float = Field(default=0, ge=0)
    include_linear_time: bool = True
    include_quadratic_time: bool = False
    time_origin_strategy: Literal["sample_mean", "first_observed", "custom"] = "sample_mean"
    custom_time_origin: float | None = None
    level2_moderator_variable_id: str | None = None
    expected_observations_per_person: int | None = Field(default=None, ge=2, le=1000)
    minimum_compliance_rate: float = Field(default=0.0, ge=0, le=1)
    exclude_low_compliance: bool = False
    response_latency_variable_id: str | None = None
    minimum_response_latency: float | None = Field(default=None, ge=0)
    maximum_response_latency: float | None = Field(default=None, gt=0)
    exclude_out_of_window: bool = False
    reliability_constructs: list[DiaryReliabilityConstructInput] = Field(
        default_factory=list, max_length=10
    )
    missing_strategy: Literal["complete_cases", "multilevel_mi"] = "complete_cases"
    imputation_count: int = Field(default=20, ge=5, le=100)
    imputation_iterations: int = Field(default=10, ge=5, le=100)
    run_robustness_checks: bool = True
    power_analysis: DiaryPowerInput | None = None
    dsem: DiaryDsemInput | None = None

    @model_validator(mode="after")
    def validate_diary(self) -> "DiaryMultilevelInput":
        if self.analysis_type == "lmm" and self.outcome_family != "gaussian":
            raise ValueError("LMM 仅适用于连续 Gaussian 结局；二元或计数结局请选择 GLMM")
        if self.analysis_type == "glmm" and self.outcome_family == "gaussian":
            raise ValueError("GLMM 必须选择 binomial、poisson 或 negative_binomial 结局族")
        if self.count_model != "standard" and (
            self.analysis_type != "glmm"
            or self.outcome_family not in {"poisson", "negative_binomial"}
        ):
            raise ValueError("零膨胀与 Hurdle 仅适用于 Poisson 或负二项计数 GLMM")
        if self.count_model == "standard" and self.zero_process_predictors != "intercept_only":
            raise ValueError("仅在零膨胀或 Hurdle 模型中可配置零过程预测变量")
        if self.analysis_type in {"mediation", "bayesian_dsem"} and (
            self.outcome_family != "gaussian"
        ):
            raise ValueError("多层中介与当前 Bayesian DSEM 切片要求连续 Gaussian 变量")
        if self.analysis_type == "glmm" and self.residual_structure != "independent":
            raise ValueError("当前 GLMM 使用条件分布建模，不支持 nlme AR(1) 残差选项")
        if (
            self.cluster_structure == "cross_classified"
            and self.residual_structure != "independent"
        ):
            raise ValueError("当前交叉分类切片要求独立条件残差，不支持 nlme AR(1)")
        if self.cluster_structure == "cross_classified" and not self.cross_class_variable_id:
            raise ValueError("交叉分类模型必须指定第二个交叉分类单元")
        if self.cluster_structure == "nested" and self.cross_class_variable_id is not None:
            raise ValueError("仅在 cross_classified 结构下可指定交叉分类单元")
        if self.analysis_type in {"mediation", "bayesian_dsem"} and (
            self.cluster_structure != "nested"
        ):
            raise ValueError("多层中介与当前 Bayesian DSEM 切片暂不支持交叉分类结构")
        if self.exposure_variable_id and self.outcome_family not in {
            "poisson",
            "negative_binomial",
        }:
            raise ValueError("暴露量 offset 仅适用于 Poisson 或负二项计数模型")
        if self.analysis_type == "bayesian_dsem" and self.dsem is None:
            raise ValueError("Bayesian DSEM 必须提供链数、迭代数、先验和随机动态参数设置")
        if self.analysis_type != "bayesian_dsem" and self.dsem is not None:
            raise ValueError("DSEM 抽样设置仅适用于 bayesian_dsem 分析")
        if self.analysis_type == "bayesian_dsem" and self.centering != "person_mean":
            raise ValueError("当前 Bayesian DSEM 要求 CWC 以分离个体内动态与个体间均值")
        if self.analysis_type == "bayesian_dsem" and (
            self.temporal_effect != "lagged" or self.lag_order != 1
        ):
            raise ValueError("当前 Bayesian DSEM 固定为双向一阶滞后结构")
        if self.analysis_type == "bayesian_dsem" and (
            self.level2_covariate_ids
            or self.control_variable_ids
            or self.level2_moderator_variable_id
        ):
            raise ValueError("当前 Bayesian DSEM 切片暂不接收协变量或跨层调节")
        if self.include_quadratic_time and not self.include_linear_time:
            raise ValueError("二次时间趋势必须与线性时间趋势同时进入模型")
        if self.time_origin_strategy == "custom" and self.custom_time_origin is None:
            raise ValueError("自定义时间原点时必须提供有限的原点数值")
        if self.time_origin_strategy != "custom" and self.custom_time_origin is not None:
            raise ValueError("仅当时间原点策略为 custom 时可提供自定义原点")
        roles = [
            self.subject_variable_id,
            self.time_variable_id,
            self.outcome_variable_id,
            self.predictor_variable_id,
        ]
        if len(roles) != len(set(roles)):
            raise ValueError("日记研究的 ID、时间、结果和预测变量必须不同")
        if self.analysis_type == "mediation":
            if not self.mediator_variable_id:
                raise ValueError("多层中介必须指定中介变量")
            if self.mediator_variable_id in roles:
                raise ValueError("中介变量不能与 ID、时间、结果或预测变量重复")
            if self.temporal_effect == "both":
                raise ValueError("多层中介需分别运行同时效应或滞后效应，不能在同一模型混合")
        if self.mediation_type == "2-1-1" and self.centering == "person_mean":
            raise ValueError("2-1-1 中介的 Level-2 预测变量不能进行 person-mean centering")
        covariates = self.level2_covariate_ids + self.control_variable_ids
        if len(covariates) != len(set(covariates)):
            raise ValueError("多层模型的协变量不得重复或同时进入两个层级")
        reserved = set(roles)
        if self.mediator_variable_id:
            reserved.add(self.mediator_variable_id)
        if self.cross_class_variable_id:
            reserved.add(self.cross_class_variable_id)
        if self.exposure_variable_id:
            reserved.add(self.exposure_variable_id)
        if len(reserved) != len(roles) + bool(self.mediator_variable_id) + bool(
            self.cross_class_variable_id
        ) + bool(self.exposure_variable_id):
            raise ValueError("交叉分类、暴露量与核心变量角色不得重复")
        overlap = reserved & set(covariates)
        if overlap:
            raise ValueError(f"多层模型协变量与核心角色重复: {', '.join(sorted(overlap))}")
        if self.level2_moderator_variable_id and self.level2_moderator_variable_id in reserved:
            raise ValueError("跨层调节变量不能与 ID、时间、X、M 或 Y 重复")
        if self.level2_moderator_variable_id and self.level2_moderator_variable_id in covariates:
            raise ValueError("跨层调节变量不应同时作为普通协变量重复进入模型")
        if self.exclude_low_compliance and self.expected_observations_per_person is None:
            raise ValueError("排除低依从性被试前必须指定每人预期观测次数")
        if self.exclude_low_compliance and self.minimum_compliance_rate <= 0:
            raise ValueError("排除低依从性被试前必须设置大于 0 的最低依从率")
        if (
            self.minimum_response_latency is not None
            and self.maximum_response_latency is not None
            and self.minimum_response_latency >= self.maximum_response_latency
        ):
            raise ValueError("有效响应延迟下限必须小于上限")
        if self.exclude_out_of_window and not self.response_latency_variable_id:
            raise ValueError("排除窗口外响应前必须指定响应延迟变量")
        if self.missing_strategy == "multilevel_mi" and self.analysis_type != "lmm":
            raise ValueError("二层多重插补当前适用于 LMM；多层中介请使用完整案例敏感性分析")
        if (
            self.missing_strategy == "multilevel_mi"
            and self.cluster_structure == "cross_classified"
        ):
            raise ValueError("当前二层多重插补不适用于交叉分类结构")
        if self.power_analysis is not None and self.analysis_type != "lmm":
            raise ValueError("当前 ESM 蒙特卡洛功效分析针对二层线性混合模型")
        reliability_ids = [
            item_id for construct in self.reliability_constructs for item_id in construct.item_ids
        ]
        if len(reliability_ids) != len(set(reliability_ids)):
            raise ValueError("多层信度构念之间不能重复使用题项")
        return self


class EmpiricalAnalysisRequest(BaseModel):
    procedure: EmpiricalProcedure | None = None
    analysis_variable_ids: list[str] = Field(default_factory=list, max_length=800)
    construct_ids: list[str] = Field(default_factory=list, max_length=100)

    context_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    sample_version_id: str | None = Field(default=None, pattern=r"^sample_[A-Za-z0-9_-]{8,63}$")
    study_plan_binding: StudyPlanBinding | None = None
    factor_count: int | None = Field(default=None, ge=1, le=20)
    group_variable_id: str | None = None
    aggregation_variable_id: str | None = None
    outcome_variable_id: str | None = None
    predictor_variable_ids: list[str] = Field(default_factory=list)
    control_variable_ids: list[str] = Field(default_factory=list)
    response_surface_predictor_ids: list[str] = Field(default_factory=list, max_length=2)
    correlation_method: Literal["pearson", "spearman", "partial"] = "pearson"
    correlation_p_adjust: Literal["none", "holm", "BH"] = "BH"
    group_omnibus_p_adjust: Literal["none", "holm", "BH"] = "holm"
    multiplicity_p_adjust: Literal["none", "holm", "BH"] = "BH"
    confidence_level: float = Field(default=0.95, gt=0.5, lt=1.0)
    multiplicity_family_id: str = Field(
        default="cross_sectional_inference",
        min_length=1,
        max_length=80,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    rotation: Literal["varimax", "promax"] = "varimax"
    factor_count_method: Literal["kaiser", "parallel_analysis", "manual"] = "kaiser"
    parallel_iterations: int = Field(default=1000, ge=100, le=10000)
    random_seed: int = Field(default=20260714, ge=1, le=2_147_483_647)
    longitudinal_panel: LongitudinalPanelInput | None = None
    diary_multilevel: DiaryMultilevelInput | None = None

    @model_validator(mode="after")
    def validate_response_surface_selection(self) -> "EmpiricalAnalysisRequest":
        selected = self.response_surface_predictor_ids
        if selected and (len(selected) != 2 or len(set(selected)) != 2):
            raise ValueError("响应面分析必须选择两个不同的焦点预测变量")
        return self


class DatasetMergeRequest(BaseModel):
    target_dataset_id: str
    subject_key: str
    wave_key: str | None = None
