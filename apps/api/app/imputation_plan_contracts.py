from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.analysis_context_contracts import (
    ContractBaseModel,
    Hash,
    ImputationPlanVersion,
    ImputationSubstantiveModel,
)


class ImputationPlanCreateRequest(ContractBaseModel):
    context_hash: Hash
    sample_version_id: str
    measurement_version_id: str | None = None
    structure_version_id: str | None = None
    substantive_model: ImputationSubstantiveModel
    variables: list[dict[str, object]] = Field(min_length=1)
    passive_rules: list[dict[str, object]] = Field(default_factory=list)
    cluster_variable_id: str | None = None
    imputations: int = Field(default=20, ge=5, le=200)
    iterations: int = Field(default=20, ge=5, le=100)
    seed: int = Field(default=20260801, ge=1, le=2_147_483_647)
    diagnostics: list[Literal["trace", "distribution", "overimputation", "fraction_missing_information"]] = Field(
        default_factory=lambda: ["trace", "distribution"]
    )
    substantive_model_hash: Hash | None = None
    plan_hash: Hash | None = None


class ImputationCompatibilityResponse(ContractBaseModel):
    compatible: bool
    reasons: list[str]
    remediation: str


class ImputationDatasetVersion(ContractBaseModel):
    id: str = Field(pattern=r"^imputation_dataset_[a-f0-9]{32}$")
    imputation_plan_version_id: str = Field(pattern=r"^imputation_plan_[a-f0-9]{32}$")
    job_id: str
    artifact_manifest_path: str = Field(min_length=1)
    artifact_hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    status: Literal["ready", "failed", "superseded"]
    created_at: str


__all__ = [
    "ImputationCompatibilityResponse",
    "ImputationDatasetVersion",
    "ImputationPlanCreateRequest",
    "ImputationPlanVersion",
]
