from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.contract_model import ContractModel

QualityScalar = str | int | float | bool


class AttentionCheckSpec(ContractModel):
    variable_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{2,127}$")
    expected_value: QualityScalar
    label: str | None = Field(default=None, max_length=200)


class DataQualityRunRequest(ContractModel):
    quality_variable_ids: list[str] = Field(default_factory=list, max_length=500)
    case_id_variable_id: str | None = None
    response_id_variable_id: str | None = None
    duration_variable_id: str | None = None
    ip_variable_id: str | None = None
    device_variable_id: str | None = None
    text_variable_ids: list[str] = Field(default_factory=list, max_length=100)
    structural_missing_variable_ids: list[str] = Field(default_factory=list, max_length=500)
    group_variable_ids: list[str] = Field(default_factory=list, max_length=50)
    attention_checks: list[AttentionCheckSpec] = Field(default_factory=list, max_length=100)


QualityMetric = Literal[
    "duration_seconds",
    "relative_duration",
    "missing_rate",
    "structural_missing_rate",
    "longstring_max",
    "response_variance",
    "straightline_ratio",
    "extreme_response_ratio",
    "duplicate_response_id",
    "duplicate_ip",
    "duplicate_device",
    "attention_check_failed",
    "duplicate_text",
    "empty_text",
    "mahalanobis_distance",
]


class ExclusionRuleInput(ContractModel):
    id: str = Field(pattern=r"^rule_[A-Za-z0-9_-]{2,63}$")
    metric: QualityMetric
    operator: Literal["lt", "lte", "gt", "gte", "eq", "neq", "in"]
    threshold: QualityScalar | list[QualityScalar] | None = None
    variable_ids: list[str] = Field(default_factory=list, max_length=100)
    logic_group: str = Field(default="default", min_length=1, max_length=64)
    source: Literal[
        "preregistered_primary",
        "preregistered_secondary",
        "planned_not_preregistered",
        "exploratory_post_data",
    ]
    description: str = Field(min_length=1, max_length=500)
    enabled: bool = True


class AnalysisSampleVersionRequest(ContractModel):
    quality_run_id: str = Field(pattern=r"^quality_[A-Za-z0-9_-]{8,63}$")
    combine_operator: Literal["and", "or"] = "or"
    rules: list[ExclusionRuleInput] = Field(default_factory=list, max_length=100)
    label: str = Field(default="主分析样本", min_length=1, max_length=200)


class DataQualityRun(ContractModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    id: str = Field(pattern=r"^quality_[A-Za-z0-9_-]{8,63}$")
    dataset_version_id: str
    dataset_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: str
    request: DataQualityRunRequest
    row_count: int = Field(ge=0)
    case_metrics_path: str
    case_metrics_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    detected_roles: dict[str, str | None]
    metrics: dict[str, object]


class AnalysisSampleVersion(ContractModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    id: str = Field(pattern=r"^sample_[A-Za-z0-9_-]{8,63}$")
    dataset_version_id: str
    dataset_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    quality_run_id: str
    created_at: str
    label: str
    combine_operator: Literal["and", "or"]
    rules: list[ExclusionRuleInput]
    row_count: int = Field(ge=0)
    included_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    boundary_count: int = Field(ge=0)
    sample_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    case_records_path: str
    case_records_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    invalidated_analysis_ids: list[str] = Field(default_factory=list)


class QualityCasePage(ContractModel):
    items: list[dict[str, object]]
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=1000)
    total: int = Field(ge=0)
