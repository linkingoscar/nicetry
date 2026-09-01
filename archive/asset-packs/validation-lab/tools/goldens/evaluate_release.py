"""Evidence-driven Golden capability status evaluator.

The release-candidate policy follows Specification 28 rather than treating a
single passing reference case as release evidence.  Statuses are derived from
the evidence that is actually present:

* L1: a frozen, passing case backed by G1 or G2 and G7;
* L2: two independent references plus normal/boundary/failure coverage;
* L3: L2 plus declared and executed G5 or G6 evidence;
* release candidate: all strict provenance, reconciliation, offline and
  capability-specific mutation gates pass.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Set

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDENS_DIR = PROJECT_ROOT / "tests" / "goldens"
PLANS_DIR = PROJECT_ROOT / "golden-plans"

BASE_REFERENCE_LEVELS = {"G1", "G2"}
STRENGTH_LEVELS = {"G5", "G6"}
REQUIRED_SCENARIO_TYPES = {
    "normal_typical",
    "legal_complex",
    "degenerate_boundary",
    "expected_failure",
}
REQUIRED_SOURCE_FIELDS = {
    "sourceId",
    "sourceType",
    "title",
    "publisher",
    "version",
    "license",
    "sha256",
    "sourceTrustScore",
    "allowedUse",
}
UNPINNED_VALUES = {"", "pinned", "latest", "main", "master", "unknown"}

try:
    from tools.goldens.invariants import evaluate_metamorphic_invariants_for_case
    from tools.goldens.verify import verify_case_manifest
except ImportError:
    sys.path.insert(0, str(PROJECT_ROOT))
    from tools.goldens.invariants import evaluate_metamorphic_invariants_for_case
    from tools.goldens.verify import verify_case_manifest


def _load_yaml(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _is_pinned_version(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() not in UNPINNED_VALUES


def _has_digest(reference: Mapping[str, Any]) -> bool:
    digest = reference.get("containerDigest")
    return isinstance(digest, str) and digest.startswith("sha256:") and len(digest) > 15


def _reference_is_executable(reference: Mapping[str, Any], case_dir: Path) -> bool:
    command = reference.get("command")
    output = reference.get("normalizedOutput")
    return (
        isinstance(command, str)
        and bool(command.strip())
        and isinstance(output, str)
        and (case_dir / output).is_file()
    )


def _references_are_independent(manifest: Mapping[str, Any], case_dir: Path) -> bool:
    primary = manifest.get("primaryReference")
    secondary = manifest.get("secondaryReference")
    if not isinstance(primary, dict) or not isinstance(secondary, dict):
        return False
    primary_engine = str(primary.get("engine", "")).strip().lower()
    secondary_engine = str(secondary.get("engine", "")).strip().lower()
    primary_output = primary.get("normalizedOutput")
    secondary_output = secondary.get("normalizedOutput")
    return (
        _reference_is_executable(primary, case_dir)
        and _reference_is_executable(secondary, case_dir)
        and bool(primary_engine)
        and bool(secondary_engine)
        and primary_engine != secondary_engine
        and primary_output != secondary_output
    )


def _source_record_is_release_ready(case_dir: Path) -> bool:
    source_path = case_dir / "data" / "source.json"
    if not source_path.is_file():
        return False
    try:
        source = _load_json(source_path)
    except (OSError, json.JSONDecodeError):
        return False
    if REQUIRED_SOURCE_FIELDS.difference(source):
        return False
    score = source.get("sourceTrustScore")
    allowed_use = source.get("allowedUse")
    return (
        _is_pinned_version(source.get("version"))
        and isinstance(source.get("sha256"), str)
        and len(source["sha256"]) == 64
        and isinstance(score, (int, float))
        and score >= 0.85
        and isinstance(allowed_use, list)
        and "testing" in allowed_use
        and bool(str(source.get("license", "")).strip())
    )


def _environment_is_release_ready(manifest: Mapping[str, Any]) -> bool:
    references = (manifest.get("primaryReference"), manifest.get("secondaryReference"))
    return all(
        isinstance(reference, dict)
        and _is_pinned_version(reference.get("version"))
        and _has_digest(reference)
        for reference in references
    )


def _has_no_unresolved_conflicts(manifest: Mapping[str, Any], case_dir: Path) -> bool:
    evidence = manifest.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("unresolvedConflicts") != []:
        return False
    reconciliation_path = case_dir / "expected" / "reconciliation.json"
    if not reconciliation_path.is_file():
        return False
    try:
        reconciliation = _load_json(reconciliation_path)
    except (OSError, json.JSONDecodeError):
        return False
    return reconciliation.get("status") in {"pass", "consensus"} and not reconciliation.get(
        "unresolvedConflicts"
    )


def _report_passed(path: Path, *, minimum_score: float | None = None) -> bool:
    if not path.is_file():
        return False
    try:
        report = _load_json(path)
    except (OSError, json.JSONDecodeError):
        return False
    if report.get("status") not in {"pass", "passed"}:
        return False
    if minimum_score is not None:
        score = report.get("mutationScore")
        critical = report.get("criticalMutantsKilled")
        return (
            isinstance(score, (int, float))
            and score >= minimum_score
            and critical == 1
        )
    return True


def _plan_is_complete(capability_id: str) -> bool:
    plan_path = PLANS_DIR / f"{capability_id}.yaml"
    if not plan_path.is_file():
        return False
    try:
        plan = _load_yaml(plan_path)
    except (OSError, yaml.YAMLError):
        return False
    estimand = plan.get("estimand")
    support = plan.get("support")
    evidence_plan = plan.get("evidencePlan")
    return (
        plan.get("capabilityId") == capability_id
        and isinstance(estimand, dict)
        and bool(estimand.get("targets"))
        and isinstance(support, dict)
        and bool(support)
        and bool(plan.get("reject"))
        and isinstance(evidence_plan, dict)
        and isinstance(evidence_plan.get("primary"), dict)
        and isinstance(evidence_plan.get("secondary"), dict)
        and bool(plan.get("cases"))
        and not REQUIRED_SCENARIO_TYPES.difference(plan.get("scenarioTypes") or [])
        and bool(plan.get("requiredFields"))
        and bool(plan.get("tolerancePolicy"))
    )


def _derive_non_release_status(
    *, has_l1: bool, has_l2: bool, has_l3: bool, has_implementation: bool
) -> str:
    if has_l3:
        return "autoverified_l3"
    if has_l2:
        return "autoverified_l2"
    if has_l1:
        return "autoverified_l1"
    return "implemented" if has_implementation else "planned"


def evaluate_capability_release(
    cap_dir: Path,
    *,
    infrastructure_gates_passed: bool = False,
    infrastructure_gate_reasons: List[str] | None = None,
) -> Dict[str, Any]:
    """Evaluate one capability without overstating its evidence status."""
    capability_id = cap_dir.name
    cases_dir = cap_dir / "cases"
    case_dirs = (
        sorted(
            path
            for path in cases_dir.iterdir()
            if path.is_dir() and (path / "manifest.yaml").is_file()
        )
        if cases_dir.is_dir()
        else []
    )
    if not case_dirs:
        return {
            "capabilityId": capability_id,
            "status": "planned",
            "eligible": False,
            "casesCount": 0,
            "reasons": ["No case manifests"],
        }

    reasons: List[str] = list(infrastructure_gate_reasons or [])
    if not infrastructure_gates_passed and not reasons:
        reasons.append("Infrastructure gates were not executed")

    all_verified = True
    all_frozen = True
    all_base_evidence = True
    has_independent_reference = False
    has_strength_evidence = False
    all_invariants_passed = True
    all_sources_ready = True
    all_environments_ready = True
    all_conflicts_resolved = True
    scenario_types: Set[str] = set()

    for case_dir in case_dirs:
        manifest = _load_yaml(case_dir / "manifest.yaml")
        identity = manifest.get("identity") if isinstance(manifest.get("identity"), dict) else {}
        evidence_levels = set(manifest.get("evidenceLevels") or [])
        scenario_type = manifest.get("scenarioType")
        if isinstance(scenario_type, str):
            scenario_types.add(scenario_type)

        if identity.get("status") != "frozen":
            all_frozen = False
            reasons.append(f"Case {case_dir.name} is not frozen")

        verification = verify_case_manifest(case_dir, require_sut=True)
        if not verification.passed:
            all_verified = False
            reasons.append(f"Case {case_dir.name} attested SUT verification failed")

        base_evidence = bool(BASE_REFERENCE_LEVELS.intersection(evidence_levels)) and "G7" in evidence_levels
        if not base_evidence:
            all_base_evidence = False
            reasons.append(f"Case {case_dir.name} lacks (G1 or G2) plus G7")

        if "G3" in evidence_levels and _references_are_independent(manifest, case_dir):
            has_independent_reference = True

        if STRENGTH_LEVELS.intersection(evidence_levels):
            has_strength_evidence = True

        invariant = evaluate_metamorphic_invariants_for_case(case_dir)
        if not invariant.get("passed"):
            all_invariants_passed = False
            reasons.append(f"Case {case_dir.name} metamorphic evidence was not executed or failed")

        if not _source_record_is_release_ready(case_dir):
            all_sources_ready = False
            reasons.append(f"Case {case_dir.name} source/license record is incomplete or unpinned")

        if not _environment_is_release_ready(manifest):
            all_environments_ready = False
            reasons.append(f"Case {case_dir.name} reference environments are not digest-pinned")

        if not _has_no_unresolved_conflicts(manifest, case_dir):
            all_conflicts_resolved = False
            reasons.append(f"Case {case_dir.name} lacks a conflict-free reconciliation record")

    missing_scenarios = REQUIRED_SCENARIO_TYPES.difference(scenario_types)
    scenario_matrix_complete = not missing_scenarios
    if not has_independent_reference:
        reasons.append("Capability lacks two executable independent references and declared G3")
    if not has_strength_evidence:
        reasons.append("Capability lacks declared G5 or G6 evidence")
    if missing_scenarios:
        reasons.append("Scenario matrix missing: " + ", ".join(sorted(missing_scenarios)))

    plan_complete = _plan_is_complete(capability_id)
    if not plan_complete:
        reasons.append(f"GoldenPlan is missing or incomplete for {capability_id}")

    provenance_dir = cap_dir / "provenance"
    mutation_passed = _report_passed(
        provenance_dir / "mutation-report.json", minimum_score=0.85
    )
    if not mutation_passed:
        reasons.append("Capability-specific mutation report is missing or below policy")
    offline_passed = _report_passed(provenance_dir / "offline-reproduction.json")
    if not offline_passed:
        reasons.append("Offline reproduction report is missing or failed")

    has_l1 = all_verified and all_frozen and all_base_evidence
    has_l2 = has_l1 and has_independent_reference and scenario_matrix_complete
    has_l3 = has_l2 and has_strength_evidence and all_invariants_passed
    eligible = all(
        (
            infrastructure_gates_passed,
            has_l3,
            all_sources_ready,
            all_environments_ready,
            all_conflicts_resolved,
            plan_complete,
            mutation_passed,
            offline_passed,
        )
    )
    status = (
        "autonomously_verified_release_candidate"
        if eligible
        else _derive_non_release_status(
            has_l1=has_l1,
            has_l2=has_l2,
            has_l3=has_l3,
            has_implementation=True,
        )
    )
    return {
        "capabilityId": capability_id,
        "status": status,
        "eligible": eligible,
        "casesCount": len(case_dirs),
        "scenarioTypes": sorted(scenario_types),
        "reasons": list(dict.fromkeys(reasons)),
    }


def _run_infrastructure_gates() -> List[str]:
    failures: List[str] = []
    gates: Iterable[tuple[str, List[str]]] = (
        (
            "Reference independence gate",
            [sys.executable, str(PROJECT_ROOT / "scripts" / "check-reference-independence.py")],
        ),
        (
            "Mutation testing gate",
            [sys.executable, str(PROJECT_ROOT / "scripts" / "run-mutation-tests.py")],
        ),
        (
            "Capability/document consistency gate",
            [sys.executable, str(PROJECT_ROOT / "scripts" / "check-capability-consistency.py")],
        ),
    )
    for label, command in gates:
        try:
            completed = subprocess.run(
                command,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            failures.append(f"{label} timed out")
            continue
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            failures.append(f"{label} failed: {detail}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Golden capability evidence status")
    parser.add_argument("--capability", type=str, help="Capability ID to evaluate")
    parser.add_argument("--all", action="store_true", help="Evaluate all capabilities")
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional JSON output path for the machine-readable evaluation report",
    )
    args = parser.parse_args()

    capabilities: List[Path] = []
    if args.capability:
        cap_dir = GOLDENS_DIR / args.capability
        if cap_dir.exists():
            capabilities.append(cap_dir)
    elif args.all:
        capabilities.extend(
            sorted(
                path
                for path in GOLDENS_DIR.iterdir()
                if path.is_dir() and (path / "bundle.yaml").is_file()
            )
        )
    if not capabilities:
        print("No capabilities found to evaluate.")
        return 1

    gate_failures = _run_infrastructure_gates()
    gate_passed = not gate_failures
    evaluations = [
        evaluate_capability_release(
            cap_dir,
            infrastructure_gates_passed=gate_passed,
            infrastructure_gate_reasons=gate_failures,
        )
        for cap_dir in capabilities
    ]

    print(f"Evaluating {len(evaluations)} Golden capability status(es)...")
    for result in evaluations:
        tag = "[RELEASE_CANDIDATE]" if result["eligible"] else "[NOT_ELIGIBLE]"
        print(f" {tag} {result['capabilityId']} -> {result['status']}")
        for reason in result["reasons"]:
            print(f"    - {reason}")

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(
                {
                    "status": "passed" if all(item["eligible"] for item in evaluations) else "failed",
                    "infrastructureGatesPassed": gate_passed,
                    "capabilities": evaluations,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    return 0 if all(item["eligible"] for item in evaluations) else 1


if __name__ == "__main__":
    sys.exit(main())
