from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.contract_model import ContractModel


class ResearchProgramSpec(ContractModel):
    id: str = Field(pattern=r"^program_[A-Za-z0-9_-]{2,63}$")
    title: str = Field(min_length=1, max_length=200)
    theoretical_question: str = Field(min_length=1, max_length=2000)
    target_journal: str | None = Field(default=None, max_length=200)
    owner: str | None = Field(default=None, max_length=100)
    construct_keys: list[str] = Field(default_factory=list)


class EstimandPlan(ContractModel):
    estimand_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
    population: str | None = Field(default=None, max_length=500)
    treatment_variable_id: str | None = None
    outcome_variable_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{2,100}$")
    comparison: str | None = Field(default=None, max_length=300)
    effect_measure: str | None = Field(default=None, max_length=100)
    analysis_unit: str | None = Field(default=None, max_length=200)
    timepoint: str | None = Field(default=None, max_length=100)
    analysis_method: str | None = Field(default=None, max_length=200)
    causal: bool = False
    estimand_role: Literal["primary", "secondary", "exploratory"] = "primary"
    hypothesis_id: str | None = None
    predictor_variable_ids: list[str] = Field(default_factory=list)
    covariate_variable_ids: list[str] = Field(default_factory=list)
    exclusion_rule_ids: list[str] = Field(default_factory=list)
    contrast_ids: list[str] = Field(default_factory=list)


class SamplingPlan(ContractModel):
    population: str | None = Field(default=None, max_length=500)
    recruitment: str | None = Field(default=None, max_length=500)
    inclusion_criteria: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)


class ExperimentalDesignPlan(ContractModel):
    conditions: list[str] = Field(default_factory=list)
    randomization_unit: str | None = Field(default=None, max_length=200)
    allocation_ratio: str | None = Field(default=None, max_length=100)


class ProtocolExclusionRule(ContractModel):
    id: str = Field(pattern=r"^rule_[A-Za-z0-9_-]{2,63}$")
    description: str = Field(min_length=1, max_length=500)
    metric: str = Field(min_length=1, max_length=100)
    operator: Literal["lt", "lte", "gt", "gte", "eq", "neq", "in"]
    threshold: str | int | float | bool | list[str | int | float | bool] | None = None
    source: Literal[
        "preregistered_primary",
        "preregistered_secondary",
        "planned_not_preregistered",
        "exploratory_post_data",
    ]


class StudyProtocolSpec(ContractModel):
    study_id: str = Field(pattern=r"^study_[A-Za-z0-9_-]{2,63}$")
    title: str = Field(min_length=1, max_length=200)
    design_type: Literal["survey", "experimental", "longitudinal", "diary"]
    protocol_version_id: str | None = None
    research_question: str | None = Field(default=None, max_length=2000)
    field_settings: dict[str, object] = Field(default_factory=dict)
    sampling_plan: SamplingPlan = Field(default_factory=SamplingPlan)
    experimental_plan: ExperimentalDesignPlan | None = None
    planned_estimands: list[EstimandPlan] = Field(default_factory=list)
    exclusion_rules: list[ProtocolExclusionRule] = Field(default_factory=list)
    stopping_rule: str | None = Field(default=None, max_length=1000)
    preregistration_url: str | None = Field(default=None, max_length=2000)
    preregistration_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class HypothesisInput(ContractModel):
    id: str = Field(pattern=r"^hyp_[A-Za-z0-9_-]{2,63}$")
    text: str = Field(min_length=1, max_length=2000)
    directionality: Literal["positive", "negative", "non_directional"]
    analysis_role: Literal["primary", "secondary", "exploratory"]
    is_preregistered: bool = False
    status: Literal["untested", "supported", "unsupported", "inconclusive"] = "untested"
    construct_keys: list[str] = Field(default_factory=list)
    estimand_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    counterevidence: str | None = Field(default=None, max_length=2000)


class ProtocolDeviation(ContractModel):
    deviation_type: Literal[
        "outcome_mismatch",
        "predictor_mismatch",
        "covariate_mismatch",
        "method_mismatch",
        "sample_rule_mismatch",
        "estimand_mismatch",
    ]
    field_path: str
    expected_value: object | None = None
    actual_value: object | None = None
    message: str
    deviation_id: str | None = None
    analysis_id: str | None = None
    reason: str | None = None
    created_at: str | None = None


class StudyProtocolIndex(ContractModel):
    study_id: str
    title: str
    design_type: str
    version_ids: list[str] = Field(default_factory=list)
    frozen_version_ids: list[str] = Field(default_factory=list)
