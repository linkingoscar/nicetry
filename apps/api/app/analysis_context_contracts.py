from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.contract_model import ContractModel
from app.study_context_contracts import StudyContextInput

# Shared strict contract base; kept as a module alias so existing subclasses
# read naturally while the repository owns exactly one ContractModel.
ContractBaseModel = ContractModel


Hash = str
RoleKey = Literal["subjectId", "clusterId", "timeId", "groupId", "treatmentId"]
ArtifactKind = Literal["dataset", "structure", "measurement", "sample", "imputation"]
ValidationLevel = Literal["unvalidated", "internally_validated", "externally_validated"]
MaturityLevel = Literal[
    "experimental", "validated", "reviewer_ready", "publication_ready"
]
PublicationEligibility = Literal["ineligible", "conditional", "eligible"]


class CapabilityValidationEvidence(ContractBaseModel):
    contract_tests: bool
    applicability_tests: bool
    failure_fixtures: bool
    external_oracle: str | None = None
    oracle_independence: str | None = None
    numeric_golden_id: str | None = None


class StudyContextVersion(ContractBaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    id: str = Field(pattern=r"^context_[a-f0-9]{32}$")
    project_id: str
    revision: int = Field(ge=1)
    time_structure: Literal["cross_sectional", "panel", "intensive_longitudinal"]
    dependence_structure: Literal["independent", "nested"]
    design: Literal["observational", "randomized", "quasi_experimental"]
    context_hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: datetime


class StudyContextMutation(ContractBaseModel):
    expected_revision: int | None = Field(default=None, ge=1)
    context: StudyContextInput


class DatasetRoleBindings(ContractBaseModel):
    subject_id: str | None = None
    cluster_id: str | None = None
    time_id: str | None = None
    group_id: str | None = None
    treatment_id: str | None = None
    data_layout: Literal["long", "wide"] | None = None
    wave_count: int | None = Field(default=None, ge=2, le=10)


class DatasetStructureValidationRequest(ContractBaseModel):
    study_context_version_id: str
    roles: DatasetRoleBindings


class DatasetStructureVersionInput(DatasetStructureValidationRequest):
    expected_revision: int | None = Field(default=None, ge=1)
    override_reason: str | None = Field(default=None, min_length=10, max_length=1000)


class ClusterSize(ContractBaseModel):
    minimum: int = Field(ge=0)
    median: float = Field(ge=0)
    maximum: int = Field(ge=0)


class ObservationsPerSubject(ContractBaseModel):
    minimum: int = Field(ge=0)
    median: float = Field(ge=0)
    maximum: int = Field(ge=0)


class StructureProfile(ContractBaseModel):
    row_count: int = Field(ge=0)
    missing_role_counts: dict[str, int]
    duplicate_subject_time_count: int | None = Field(default=None, ge=0)
    subject_count: int | None = Field(default=None, ge=0)
    cluster_count: int | None = Field(default=None, ge=0)
    singleton_cluster_count: int | None = Field(default=None, ge=0)
    cluster_size: ClusterSize | None = None
    observations_per_subject: ObservationsPerSubject | None = None
    time_point_count: int | None = Field(default=None, ge=0)
    nesting_classification: Literal[
        "none", "two_level", "three_level", "cross_classified", "ambiguous"
    ]


class StructureWarning(ContractBaseModel):
    code: str
    severity: Literal["warning", "error"]
    message: str


class StructureValidationResponse(ContractBaseModel):
    status: Literal["valid", "warning", "invalid"]
    profile: StructureProfile
    warnings: list[StructureWarning]
    proposed_structure_hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")


class DatasetStructureVersion(ContractBaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    id: str = Field(pattern=r"^structure_[a-f0-9]{32}$")
    dataset_version_id: str
    project_id: str
    revision: int = Field(ge=1)
    study_context_version_id: str
    context_snapshot: StudyContextInput
    roles: DatasetRoleBindings
    profile: StructureProfile
    status: Literal["valid", "warning", "invalid"]
    warnings: list[StructureWarning]
    override_reason: str | None = Field(default=None, min_length=10, max_length=1000)
    structure_hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: datetime


class ResolvedArtifactRef(ContractBaseModel):
    id: str
    hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")


class ResolvedDatasetRef(ResolvedArtifactRef):
    sha256: Hash = Field(pattern=r"^[a-f0-9]{64}$")


class ResolvedStudyContextRef(ResolvedArtifactRef):
    revision: int = Field(ge=1)
    value: StudyContextInput


class ResolvedStructureRef(ResolvedArtifactRef):
    revision: int = Field(ge=1)
    study_context_version_id: str
    roles: DatasetRoleBindings
    status: Literal["valid", "warning"]
    profile: StructureProfile | None = None
    warnings: list[StructureWarning] = Field(default_factory=list)
    override_reason: str | None = Field(default=None, min_length=10, max_length=1000)


class ContextWarning(ContractBaseModel):
    code: str
    severity: Literal["info", "warning"]
    message: str


class ContextInvalidation(ContractBaseModel):
    upstream_changes: list[str]
    affected_objects: list[str]
    history_status: Literal["available", "not_available"]
    required_action: Literal["confirm", "migrate", "rerun"]


class ResolvedAnalysisContext(ContractBaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    project_id: str
    dataset: ResolvedDatasetRef
    study_context: ResolvedStudyContextRef | None
    structure: ResolvedStructureRef | None
    measurement: ResolvedArtifactRef | None = None
    sample: ResolvedArtifactRef
    imputation: ResolvedArtifactRef | None = None
    context_hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    validity: Literal["ready", "incomplete", "stale"]
    missing_requirements: list[str]
    warnings: list[ContextWarning]
    invalidation: ContextInvalidation | None = None


class ApplicableCapability(ContractBaseModel):
    family: str
    slice_id: str
    label: str
    status: Literal["experimental", "supported"]
    execution_available: bool
    validation_level: ValidationLevel
    maturity_level: MaturityLevel
    publication_eligibility: PublicationEligibility
    publication_eligibility_reason: str
    validation_evidence: CapabilityValidationEvidence
    applicable: bool
    requires_revalidation: bool
    product_visible: bool
    required_roles: list[RoleKey]
    optional_roles: list[RoleKey]
    required_artifacts: list[ArtifactKind]
    default_bindings: dict[str, str]
    missing_requirements: list[str]
    blocked_reason: str | None = None
    support_boundary: str


class ApplicableCapabilitiesResponse(ContractBaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    context_hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    capabilities: list[ApplicableCapability]


class AnalysisDraft(ContractBaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    id: str = Field(pattern=r"^draft_[a-f0-9]{32}$")
    revision: int = Field(ge=1)
    dataset_version_id: str
    family: str
    slice_id: str
    context_hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    context_snapshot_id: str
    spec: dict[str, object]
    role_overrides: dict[str, dict[str, str]]
    validity: Literal["ready", "incomplete", "stale", "superseded"]
    invalidation_reasons: list[str]
    invalidation: ContextInvalidation | None = None
    created_at: datetime
    updated_at: datetime


class AnalysisDraftCreateRequest(ContractBaseModel):
    slice_id: str
    context_hash: Hash


class RoleOverride(ContractBaseModel):
    variable_id: str
    reason: str = Field(min_length=10, max_length=1000)


class AnalysisDraftMutation(ContractBaseModel):
    expected_revision: int = Field(ge=1)
    spec: dict[str, object]
    role_overrides: dict[str, RoleOverride] = Field(default_factory=dict)


class ImputationSubstantiveModel(ContractBaseModel):
    model_type: Literal["linear_regression"]
    outcome_id: str
    predictor_ids: list[str]
    include_intercept: bool


class ImputationPlanVersion(ContractBaseModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    id: str = Field(pattern=r"^imputation_plan_[a-f0-9]{32}$")
    dataset_version_id: str
    dataset_sha256: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    context_hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    sample_version_id: str
    sample_hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    measurement_version_id: str | None = None
    measurement_hash: Hash | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    structure_version_id: str | None = None
    structure_hash: Hash | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    substantive_model: ImputationSubstantiveModel
    substantive_model_hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    predictor_matrix_hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    variables: list[dict[str, object]]
    passive_rules: list[dict[str, object]]
    cluster_variable_id: str | None = None
    imputations: int = Field(ge=1)
    iterations: int = Field(ge=1)
    seed: int
    diagnostics: list[
        Literal["trace", "distribution", "overimputation", "fraction_missing_information"]
    ]
    plan_hash: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: datetime
