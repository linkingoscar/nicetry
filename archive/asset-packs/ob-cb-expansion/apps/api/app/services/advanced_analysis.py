from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.advanced_contracts import (
    AdvancedAnalysisSpec,
    ExperimentalDesignSpec,
    LongitudinalModelSpec,
    MultilevelModelSpec,
    MultipleImputationSpec,
    PowerAnalysisSpec,
    QuestionnaireMeasurementSpec,
)


class AdvancedCapabilityNotImplemented(NotImplementedError):
    def __init__(
        self,
        family: str,
        capability: "AdvancedCapability",
        capability_slice: "AdvancedCapabilitySlice | None" = None,
    ) -> None:
        self.family = family
        self.capability = capability
        self.capability_slice = capability_slice
        target = capability.label
        if capability_slice is not None:
            target = f"{target} / {capability_slice.label}"
        super().__init__(
            f"{target} 的运行接口已预留，但当前切片尚未达到可执行状态；"
            f"当前状态为 {capability_slice.status if capability_slice else 'planned'}"
        )


@dataclass(frozen=True)
class AdvancedCapabilitySlice:
    id: str
    label: str
    status: str
    execution_available: bool
    support_boundary: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["executionAvailable"] = value.pop("execution_available")
        value["supportBoundary"] = value.pop("support_boundary")
        return value


@dataclass(frozen=True)
class AdvancedCapability:
    family: str
    label: str
    status: str
    spec_version: str
    result_version: str
    planned_engine: str
    minimum_validation: tuple[str, ...]
    slices: tuple[AdvancedCapabilitySlice, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["specVersion"] = value.pop("spec_version")
        value["resultVersion"] = value.pop("result_version")
        value["plannedEngine"] = value.pop("planned_engine")
        value["minimumValidation"] = list(value.pop("minimum_validation"))
        value["slices"] = []
        for item in asdict(self)["slices"]:
            item = dict(item)
            item["executionAvailable"] = item.pop("execution_available")
            item["supportBoundary"] = item.pop("support_boundary")
            value["slices"].append(item)
        return value


class AdvancedAnalysisRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[str, AdvancedCapability] = {}
        self._runners: set[str] = set()

    def declare(self, capability: AdvancedCapability) -> None:
        if capability.family in self._capabilities:
            raise ValueError(f"高级分析能力已声明: {capability.family}")
        self._capabilities[capability.family] = capability

    def register_runner(self, family: str) -> None:
        if family not in self._capabilities:
            raise KeyError(f"必须先声明高级分析能力: {family}")
        self._runners.add(family)

    def capabilities(self) -> list[dict[str, Any]]:
        return [
            {
                **capability.to_dict(),
                "executionAvailable": family in self._runners,
            }
            for family, capability in self._capabilities.items()
        ]

    def slice_for_spec(self, spec: AdvancedAnalysisSpec) -> AdvancedCapabilitySlice | None:
        capability = self._capabilities[spec.family]
        slice_id: str | None = None
        if isinstance(spec, ExperimentalDesignSpec):
            if spec.analysis_type == "glm_cluster" and spec.data_layout == "long":
                slice_id = "experimental_design.glm_cluster.long.single_outcome"
            elif spec.design_type in {"factorial_anova", "ancova"} and spec.data_layout == "long":
                slice_id = f"experimental_design.{spec.design_type}.long.single_outcome"
            elif spec.design_type == "repeated_measures" and len(spec.within_factors) == 1:
                slice_id = "experimental_design.repeated_measures.single_within"
            elif spec.design_type == "mixed_design" and len(spec.within_factors) == 1:
                slice_id = "experimental_design.mixed_design.single_within"
        elif isinstance(spec, MultilevelModelSpec):
            if spec.analysis_type == "aggregation":
                slice_id = "multilevel_model.aggregation.icc_rwg"
            elif spec.distribution == "gaussian" and spec.higher_level_cluster_variable_id is None:
                slice_id = "multilevel_model.gaussian.two_level"
        elif isinstance(spec, LongitudinalModelSpec):
            if spec.model_type == "growth_curve":
                slice_id = "longitudinal_model.observed_growth"
            elif spec.model_type == "cross_lagged_panel":
                slice_id = "longitudinal_model.traditional_clpm"
            elif spec.model_type == "ri_clpm":
                slice_id = "longitudinal_model.ri_clpm"
            elif spec.model_type == "latent_growth":
                slice_id = "longitudinal_model.latent_growth"
            elif spec.model_type == "longitudinal_invariance":
                slice_id = "longitudinal_model.longitudinal_invariance"
        elif isinstance(spec, MultipleImputationSpec):
            if spec.method == "mice_fcs" and not spec.passive_rules:
                slice_id = (
                    "multiple_imputation.rubin_pooling"
                    if spec.pooling == "rubin"
                    else "multiple_imputation.mice_dataset_generation"
                )
        elif isinstance(spec, PowerAnalysisSpec):
            if spec.method == "analytic" and spec.design_family in {
                "regression",
                "t_test",
                "factorial_anova",
            }:
                slice_id = f"power_analysis.analytic.{spec.design_family}"
            elif spec.method == "monte_carlo" and spec.design_family in {
                "regression",
                "factorial_anova",
            }:
                slice_id = "power_analysis.monte_carlo"
        elif isinstance(spec, QuestionnaireMeasurementSpec):
            if spec.model_type == "reliability":
                slice_id = "questionnaire_measurement.reliability"
            elif spec.model_type == "efa":
                slice_id = "questionnaire_measurement.efa"
            elif spec.model_type == "cfa":
                slice_id = "questionnaire_measurement.cfa"
            elif spec.model_type == "measurement_invariance":
                slice_id = "questionnaire_measurement.measurement_invariance"
            elif spec.model_type in {"esem_bifactor_irt", "bifactor", "esem", "irt"}:
                slice_id = "questionnaire_measurement.esem_bifactor_irt"
            elif spec.model_type in {"common_method_bias", "marker_variable", "ulmc"}:
                slice_id = "questionnaire_measurement.common_method_bias"

        if slice_id is None:
            return None
        return next((item for item in capability.slices if item.id == slice_id), None)

    def validate(self, spec: AdvancedAnalysisSpec) -> dict[str, Any]:
        capability = self._capabilities[spec.family]
        capability_slice = self.slice_for_spec(spec)
        warnings: list[dict[str, str]] = []
        if capability_slice is None or not capability_slice.execution_available:
            warnings.append(
                {
                    "code": "CAPABILITY_SLICE_NOT_EXECUTABLE",
                    "severity": "warning",
                    "message": "规格结构有效，但当前具体 design/model/method slice 尚未注册为可执行。",
                }
            )
        elif spec.family not in self._runners:
            warnings.append(
                {
                    "code": "CAPABILITY_PLANNED",
                    "severity": "info",
                    "message": "规格结构有效，但当前仅完成协议预留；有效不代表统计引擎已实现。",
                }
            )
        elif capability.status == "experimental":
            warnings.append(
                {
                    "code": "CAPABILITY_EXPERIMENTAL",
                    "severity": "warning",
                    "message": "该能力仅覆盖当前登记的实验切片，尚未通过正式支持所需的完整数值验证。",
                }
            )
        return {
            "valid": True,
            "family": spec.family,
            "capabilityId": capability_slice.id
            if capability_slice
            else f"{spec.family}.unclassified",
            "sliceId": capability_slice.id if capability_slice else None,
            "sliceStatus": capability_slice.status if capability_slice else "planned",
            "implementationStatus": capability_slice.status if capability_slice else "planned",
            "executionAvailable": bool(
                capability_slice
                and capability_slice.execution_available
                and spec.family in self._runners
            ),
            "spec": spec.model_dump(mode="json", by_alias=True),
            "warnings": warnings,
        }

    def assert_executable(self, spec: AdvancedAnalysisSpec) -> None:
        capability = self._capabilities[spec.family]
        capability_slice = self.slice_for_spec(spec)
        if (
            spec.family not in self._runners
            or capability_slice is None
            or not capability_slice.execution_available
        ):
            raise AdvancedCapabilityNotImplemented(spec.family, capability, capability_slice)


advanced_analysis_registry = AdvancedAnalysisRegistry()

for declared in (
    AdvancedCapability(
        family="experimental_design",
        label="组间与受限重复测量实验切片",
        status="experimental",
        spec_version="0.1.0",
        result_version="0.1.0",
        planned_engine="R: afex/emmeans",
        minimum_validation=("公开教材数据", "SPSS/R 对照", "球形性与稳健边界"),
        slices=(
            AdvancedCapabilitySlice(
                "experimental_design.glm_cluster.long.single_outcome",
                "长格式 cluster-robust GLM",
                "experimental",
                True,
                "单 outcome、identity-link Gaussian lm、CR0 cluster-robust SE；不冒充 CR2/GLMM",
            ),
            AdvancedCapabilitySlice(
                "experimental_design.factorial_anova.long.single_outcome",
                "长格式组间 factorial ANOVA",
                "experimental",
                True,
                "单 outcome、长格式、最多 3 个组间因子；单一组间因子可使用真实 Games–Howell",
            ),
            AdvancedCapabilitySlice(
                "experimental_design.ancova.long.single_outcome",
                "长格式组间 ANCOVA",
                "experimental",
                True,
                "单 outcome、长格式；协变量×处理交互只产生警告",
            ),
            AdvancedCapabilitySlice(
                "experimental_design.repeated_measures.single_within",
                "单一组内因子重复测量",
                "experimental",
                True,
                "单一 within factor；EMM+CI、GG 与完整被试内单元已自动验证",
            ),
            AdvancedCapabilitySlice(
                "experimental_design.mixed_design.single_within",
                "单一组内因子混合设计",
                "experimental",
                True,
                "单一 within factor；EMM+CI、GG 与空/缺失单元边界已自动验证",
            ),
        ),
    ),
    AdvancedCapability(
        family="multilevel_model",
        label="两层 Gaussian LMM 实验切片",
        status="experimental",
        spec_version="0.1.0",
        result_version="0.1.0",
        planned_engine="R: lme4/lmerTest/performance",
        minimum_validation=("sleepstudy", "收敛/奇异拟合", "小聚类数边界"),
        slices=(
            AdvancedCapabilitySlice(
                "multilevel_model.aggregation.icc_rwg",
                "ICC(1)/ICC(2)/rwg 聚合证据",
                "experimental",
                True,
                "显式量表题项、量表范围与 cluster；返回 cluster 级 rwg 和聚合建议，不硬编码 5 点量表",
            ),
            AdvancedCapabilitySlice(
                "multilevel_model.gaussian.two_level",
                "两层 Gaussian LMM",
                "experimental",
                True,
                "单一 cluster、Gaussian、随机截距/有限随机斜率",
            ),
        ),
    ),
    AdvancedCapability(
        family="longitudinal_model",
        label="观测增长与传统 CLPM 实验切片",
        status="experimental",
        spec_version="0.1.0",
        result_version="0.1.0",
        planned_engine="R: lavaan/lmerTest",
        minimum_validation=("公开面板数据", "时间不等距", "纵向等值性"),
        slices=(
            AdvancedCapabilitySlice(
                "longitudinal_model.observed_growth",
                "观测增长曲线",
                "experimental",
                True,
                "至少 3 波；明确区分 complete_cases 与 MAR available_rows_ml，不宣称 FIML",
            ),
            AdvancedCapabilitySlice(
                "longitudinal_model.traditional_clpm",
                "传统 CLPM",
                "experimental",
                True,
                "至少 3 波；ML/MLR FIML 的 attrition/re-entry 已验证；RI-CLPM 由独立 slice 接收",
            ),
            AdvancedCapabilitySlice(
                "longitudinal_model.ri_clpm",
                "RI-CLPM",
                "experimental",
                True,
                "两个构念、至少 3 波；显式随机截距和 within-person 自回归/交叉滞后，ML/MLR",
            ),
            AdvancedCapabilitySlice(
                "longitudinal_model.latent_growth",
                "潜在增长曲线",
                "experimental",
                True,
                "至少 3 波；显式 intercept/slope 因子与不等距 timeValue，ML/MLR/WLSMV 按缺失口径执行",
            ),
            AdvancedCapabilitySlice(
                "longitudinal_model.longitudinal_invariance",
                "纵向测量等值性",
                "experimental",
                True,
                "至少 2 波；支持 configural, metric, scalar, strict 级联检验与潜均值比较",
            ),
        ),
    ),
    AdvancedCapability(
        family="multiple_imputation",
        label="MICE 插补与 Rubin 合并推断",
        status="experimental",
        spec_version="0.1.0",
        result_version="0.1.0",
        planned_engine="R: mice",
        minimum_validation=("MCAR/MAR 合成数据", "Rubin 规则", "链收敛诊断"),
        slices=(
            AdvancedCapabilitySlice(
                "multiple_imputation.mice_dataset_generation",
                "MICE 插补数据集生成",
                "experimental",
                True,
                "只生成不可变插补数据集；不执行 pooled inference",
            ),
            AdvancedCapabilitySlice(
                "multiple_imputation.rubin_pooling",
                "Rubin 合并推断",
                "experimental",
                True,
                "仅支持冻结的线性回归下游模型；逐份拟合并返回 Qbar/Ubar/B/T/FMI/Barnard–Rubin df",
            ),
        ),
    ),
    AdvancedCapability(
        family="power_analysis",
        label="回归与组间 ANOVA 解析功效",
        status="experimental",
        spec_version="0.1.0",
        result_version="0.1.0",
        planned_engine="R: pwr",
        minimum_validation=("G*Power/pwr 对照", "Monte Carlo 重复性", "目标功效反解"),
        slices=(
            AdvancedCapabilitySlice(
                "power_analysis.analytic.regression",
                "回归解析功效",
                "experimental",
                True,
                "Cohen f²/R² change；双侧、ceil 回代",
            ),
            AdvancedCapabilitySlice(
                "power_analysis.analytic.t_test",
                "t 检验解析功效",
                "experimental",
                True,
                "单样本或两独立样本、Cohen d、双侧；总样本量按 ceil 回代",
            ),
            AdvancedCapabilitySlice(
                "power_analysis.analytic.factorial_anova",
                "均衡组间 ANOVA 解析功效",
                "experimental",
                True,
                "Cohen f；均衡组间、ceil 回代",
            ),
            AdvancedCapabilitySlice(
                "power_analysis.monte_carlo",
                "复杂设计 Monte Carlo 功效",
                "experimental",
                True,
                "当前支持显式 Gaussian 回归/均衡组间 ANOVA DGP；返回有效模拟数、失败数、MCSE、Wilson 区间与样本量/效应量反解",
            ),
        ),
    ),
    AdvancedCapability(
        family="questionnaire_measurement",
        label="问卷测量高级分析与 CMB 诊断",
        status="experimental",
        spec_version="0.1.0",
        result_version="0.1.0",
        planned_engine="R: lavaan/mirt/psych",
        minimum_validation=("Bifactor 辅助指标", "Lindell-Whitney Marker", "ULMC 拟合比较"),
        slices=(
            AdvancedCapabilitySlice(
                "questionnaire_measurement.reliability",
                "Ordinal reliability 与结构性缺失",
                "experimental",
                True,
                "显式题项/构念，返回 α/ω、ordinal α/ω 与构念级结构性缺失",
            ),
            AdvancedCapabilitySlice(
                "questionnaire_measurement.efa",
                "Polychoric EFA、MAP 与 split validation",
                "experimental",
                True,
                "题项完整案例、显式因子数/旋转，返回 MAP、载荷、因子相关与 split congruence",
            ),
            AdvancedCapabilitySlice(
                "questionnaire_measurement.cfa",
                "CFA ML/MLR/WLSMV",
                "experimental",
                True,
                "显式简单结构构念；ML/MLR 或有序题项 WLSMV，收敛/Heywood 状态显式返回",
            ),
            AdvancedCapabilitySlice(
                "questionnaire_measurement.measurement_invariance",
                "多组测量等值性与潜均值",
                "experimental",
                True,
                "必须显式提供 groupVariableId；configural/metric/scalar/strict 级联结果",
            ),
            AdvancedCapabilitySlice(
                "questionnaire_measurement.esem_bifactor_irt",
                "ESEM, Bifactor 与 IRT/DIF 测量诊断",
                "experimental",
                True,
                "支持 Bifactor (ωh, ECV, PUC)、ESEM 目标旋转与 WLSMV GRM IRT/DIF 诊断",
            ),
            AdvancedCapabilitySlice(
                "questionnaire_measurement.common_method_bias",
                "Marker Variable 与 ULMC 共同方法偏差诊断",
                "experimental",
                True,
                "支持 Lindell-Whitney Marker 变量调整与 ULMC 未测量潜方法因子嵌套模型比较",
            ),
        ),
    ),
):
    advanced_analysis_registry.declare(declared)

for family in (
    "experimental_design",
    "multilevel_model",
    "longitudinal_model",
    "multiple_imputation",
    "power_analysis",
    "questionnaire_measurement",
):
    advanced_analysis_registry.register_runner(family)
