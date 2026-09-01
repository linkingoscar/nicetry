"""GoldenPlan creation and validation CLI tool (Specification 28, Section 9 & 22.1).

Generates and validates golden-plans/<capabilityId>.yaml manifest specifications
before statistical capability development.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PLANS_DIR = PROJECT_ROOT / "golden-plans"
REQUIRED_SCENARIO_TYPES = {
    "normal_typical",
    "legal_complex",
    "degenerate_boundary",
    "expected_failure",
}


class EstimandTarget(BaseModel):
    unit: str = "participant"
    scale: str = "identity"
    targets: List[str] = Field(default_factory=list)


class SupportBounds(BaseModel):
    outcomes: List[str] = Field(default_factory=list)
    levels: Optional[int] = None
    df_methods: List[str] = Field(default_factory=list, alias="dfMethods")

    model_config = {"populate_by_name": True}


class PrimaryEvidence(BaseModel):
    type: str = "official_open_source"
    tool: str = "lavaan"


class SecondaryEvidence(BaseModel):
    type: str = "independent_language"
    tool: str = "statsmodels"


class EvidencePlan(BaseModel):
    primary: PrimaryEvidence
    secondary: Optional[SecondaryEvidence] = None
    additional: List[str] = Field(default_factory=list)


class GoldenPlanSpec(BaseModel):
    schema_version: int = Field(default=1, alias="schemaVersion")
    capability_id: str = Field(alias="capabilityId")
    method_family: str = Field(alias="methodFamily")
    estimand: EstimandTarget
    support: SupportBounds
    reject: List[str] = Field(default_factory=list)
    evidence_plan: EvidencePlan = Field(alias="evidencePlan")
    cases: List[str] = Field(default_factory=list)
    scenario_types: List[str] = Field(default_factory=list, alias="scenarioTypes")
    required_fields: List[str] = Field(default_factory=list, alias="requiredFields")
    tolerance_policy: str = Field(default="iterative_v1", alias="tolerancePolicy")

    model_config = {"populate_by_name": True}


def create_sample_plan(capability_id: str) -> Dict[str, Any]:
    parts = capability_id.split(".")
    family = parts[0] if parts else "general"

    plan = GoldenPlanSpec(
        schema_version=1,
        capability_id=capability_id,
        method_family=family,
        estimand=EstimandTarget(
            unit="participant",
            scale="identity",
            targets=["point_estimate", "standard_error", "test_statistic"],
        ),
        support=SupportBounds(
            outcomes=["continuous"],
            df_methods=["satterthwaite", "asymptotic"],
        ),
        reject=["non_identifiable", "empty_cells"],
        evidence_plan=EvidencePlan(
            primary=PrimaryEvidence(type="official_open_source", tool="base_r"),
            secondary=SecondaryEvidence(type="independent_language", tool="python_scipy"),
            additional=["frozen_public_dataset", "metamorphic"],
        ),
        cases=[
            f"{parts[-2] if len(parts) > 1 else 'standard'}_normal",
            f"{parts[-2] if len(parts) > 1 else 'standard'}_complex",
            f"{parts[-2] if len(parts) > 1 else 'standard'}_boundary",
            f"{parts[-2] if len(parts) > 1 else 'standard'}_failure",
        ],
        scenario_types=sorted(REQUIRED_SCENARIO_TYPES),
        required_fields=["estimate", "standardError", "testStatistic", "pValue"],
        tolerance_policy="closed_form_v1",
    )
    return plan.model_dump(by_alias=True)


def validate_plan_file(plan_path: Path) -> bool:
    if not plan_path.exists():
        print(f"[ERROR] Golden plan file not found: {plan_path}")
        return False

    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)

        plan = GoldenPlanSpec.model_validate(raw_data)

        # Validate mandatory rules in Spec 28, Section 9
        errors: List[str] = []
        if not plan.estimand.targets:
            errors.append("estimand.targets cannot be empty")
        if not plan.support.outcomes:
            errors.append("support.outcomes cannot be empty")
        if not plan.reject:
            errors.append("reject cannot be empty")
        if not plan.required_fields:
            errors.append("requiredFields cannot be empty")
        if not plan.cases:
            errors.append("cases list cannot be empty")
        if not plan.evidence_plan.primary.tool:
            errors.append("evidencePlan.primary.tool cannot be empty")
        if plan.evidence_plan.secondary is None or not plan.evidence_plan.secondary.tool:
            errors.append("evidencePlan.secondary.tool cannot be empty")
        missing_scenarios = REQUIRED_SCENARIO_TYPES.difference(plan.scenario_types)
        if missing_scenarios:
            errors.append(
                "scenarioTypes missing required coverage: "
                + ", ".join(sorted(missing_scenarios))
            )
        if not plan.tolerance_policy.strip():
            errors.append("tolerancePolicy cannot be empty")

        if errors:
            print(f"[FAIL] Plan validation failed for {plan_path.name}:")
            for err in errors:
                print(f"  - {err}")
            return False

        print(f"[PASS] Golden plan valid: {plan.capability_id}")
        return True
    except Exception as exc:
        print(f"[ERROR] Invalid plan file format in {plan_path}: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="GoldenPlan CLI Tool")
    parser.add_argument(
        "--capability", type=str, help="Capability ID to generate or validate plan for"
    )
    parser.add_argument(
        "--create", action="store_true", help="Create a sample GoldenPlan if missing"
    )
    parser.add_argument("--validate", action="store_true", help="Validate existing GoldenPlan")
    args = parser.parse_args()

    if not args.capability:
        print("Please specify --capability <capabilityId>")
        return 1

    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    plan_path = PLANS_DIR / f"{args.capability}.yaml"

    if args.create:
        if plan_path.exists():
            print(f"[INFO] Plan already exists at {plan_path}")
        else:
            plan_dict = create_sample_plan(args.capability)
            with open(plan_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(plan_dict, f, sort_keys=False, allow_unicode=True)
            print(f"[CREATED] GoldenPlan saved to {plan_path}")

    if args.validate or not args.create:
        ok = validate_plan_file(plan_path)
        return 0 if ok else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
