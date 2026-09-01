"""Schema definitions for AI-Agent Gold Standard Verification Infrastructure.

Implements data structures and serialization for Specification 28:
- CapabilityBundle
- CaseManifest
- ComparisonRule
- VerificationReport
"""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ComparatorKind(str, Enum):
    EXACT = "exact"
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    ABSOLUTE_RELATIVE = "absolute_relative"
    SET_EQUIVALENT = "set_equivalent"
    SIGN_INDETERMINATE = "sign_indeterminate"
    EXPECTED_FAILURE = "expected_failure"


class ComparisonRule(BaseModel):
    path: str
    comparator: ComparatorKind = ComparatorKind.ABSOLUTE_RELATIVE
    abs_tolerance: float = Field(default=1e-5, alias="absTolerance")
    rel_tolerance: float = Field(default=1e-4, alias="relTolerance")
    required: bool = True

    model_config = {
        "populate_by_name": True,
    }


class DatasetEntry(BaseModel):
    path: str
    sha256: str
    row_count: Optional[int] = Field(default=None, alias="rowCount")
    column_count: Optional[int] = Field(default=None, alias="columnCount")

    model_config = {
        "populate_by_name": True,
    }


class ReferenceEngine(BaseModel):
    engine: str
    version: str = "pinned"
    command: Optional[str] = None
    container_digest: Optional[str] = Field(default=None, alias="containerDigest")
    normalized_output: str = Field(alias="normalizedOutput")

    model_config = {
        "populate_by_name": True,
    }


class EvidenceLevel(str, Enum):
    G0 = "G0"  # Production self-test only (invalid as standalone gold standard)
    G1 = "G1"  # Closed-form / exact mathematical derivation
    G2 = "G2"  # Official open source package
    G3 = "G3"  # Second independent implementation
    G4 = "G4"  # Frozen commercial software output (Mplus, Stata, SPSS)
    G5 = "G5"  # Simulation parameter recovery
    G6 = "G6"  # Metamorphic / property invariants
    G7 = "G7"  # Provenance & hashes


class ScenarioType(str, Enum):
    NORMAL_TYPICAL = "normal_typical"
    LEGAL_COMPLEX = "legal_complex"
    DEGENERATE_BOUNDARY = "degenerate_boundary"
    EXPECTED_FAILURE = "expected_failure"


class EvidenceGovernance(BaseModel):
    source_trust_minimum: float = Field(default=0.85, alias="sourceTrustMinimum")
    unresolved_conflicts: List[str] = Field(
        default_factory=list, alias="unresolvedConflicts"
    )

    model_config = {
        "populate_by_name": True,
    }


class CaseIdentity(BaseModel):
    golden_case_id: str = Field(alias="goldenCaseId")
    capability_id: str = Field(alias="capabilityId")
    case_version: str = Field(default="1.0.0", alias="caseVersion")
    status: str = Field(default="draft")  # draft | frozen | quarantined

    model_config = {
        "populate_by_name": True,
    }


class CaseManifest(BaseModel):
    schema_version: int = Field(default=1, alias="schemaVersion")
    identity: CaseIdentity
    scenario_type: Optional[ScenarioType] = Field(default=None, alias="scenarioType")
    dataset: Optional[List[DatasetEntry]] = Field(default_factory=list)
    spec_path: str = Field(alias="specPath")
    estimand_path: Optional[str] = Field(default=None, alias="estimandPath")
    primary_reference: Optional[ReferenceEngine] = Field(default=None, alias="primaryReference")
    secondary_reference: Optional[ReferenceEngine] = Field(default=None, alias="secondaryReference")
    comparison_rules: List[ComparisonRule] = Field(default_factory=list, alias="comparisonRules")
    expected_output_path: str = Field(alias="expectedOutputPath")
    evidence_levels: List[EvidenceLevel] = Field(default_factory=list, alias="evidenceLevels")
    evidence: Optional[EvidenceGovernance] = None

    model_config = {
        "populate_by_name": True,
    }


class CapabilityBundle(BaseModel):
    schema_version: int = Field(default=1, alias="schemaVersion")
    capability_id: str = Field(alias="capabilityId")
    method_family: str = Field(alias="methodFamily")
    cases: List[str] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
    }


class FieldFailure(BaseModel):
    path: str
    actual: Any
    expected: Any
    message: str
    comparator: str


class CaseVerificationResult(BaseModel):
    golden_case_id: str
    capability_id: str
    passed: bool
    evidence_satisfied: bool
    failures: List[FieldFailure] = Field(default_factory=list)
    provenance_matched: bool = True
