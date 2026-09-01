"""Reconcile two independent normalized references into a consensus expected result.

Unlike the original placeholder, this implementation never copies the primary
reference silently.  Every normalized leaf must have a comparison rule and be
present in both references.  Conflicts are recorded and prevent expected output
replacement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDENS_DIR = PROJECT_ROOT / "tests" / "goldens"

try:
    from tools.goldens.schema import CaseManifest
    from tools.goldens.verify import compare_value, resolve_path
except ImportError:
    sys.path.insert(0, str(PROJECT_ROOT))
    from tools.goldens.schema import CaseManifest
    from tools.goldens.verify import compare_value, resolve_path

# Specification 31, Section 13.4 policy floors and hard upper bounds.
DEFAULT_THEORETICAL_FLOORS = {
    "exact": 0.0,
    "closed_form": 1e-8,
    "ols": 1e-7,
    "emm": 1e-6,
    "iterative": 1e-5,
    "fit_index": 1e-4,
}

HARD_UPPER_BOUNDS = {
    "closed_form": 1e-7,
    "ols": 1e-5,
    "emm": 1e-4,
    "iterative": 1e-3,
    "fit_index": 0.002,
}


def calculate_dynamic_tolerance(
    primary_val: float,
    secondary_val: Optional[float],
    runtime_noise: float = 0.0,
    category: str = "iterative",
) -> Tuple[float, float]:
    """Return a policy-compliant tolerance or fail when the ceiling is exceeded."""
    theoretical_floor = DEFAULT_THEORETICAL_FLOORS.get(category, 1e-5)
    cross_engine_diff = abs(primary_val - secondary_val) if secondary_val is not None else 0.0
    raw_tolerance = max(10.0 * runtime_noise, 2.0 * cross_engine_diff, theoretical_floor)
    upper_bound = HARD_UPPER_BOUNDS.get(category, 1e-3)
    if raw_tolerance > upper_bound:
        raise ValueError(
            f"TOLERANCE_EXCEEDS_POLICY: {raw_tolerance:.6g} exceeds {upper_bound:.6g}"
        )
    return raw_tolerance, min(raw_tolerance * 10.0, upper_bound * 10.0)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _flatten_leaf_paths(value: Any, prefix: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten_leaf_paths(child, child_prefix)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from _flatten_leaf_paths(child, f"{prefix}[{index}]")
        return
    yield prefix


def _conflict(
    *, path: str, code: str, primary: Any = None, secondary: Any = None, message: str
) -> Dict[str, Any]:
    return {
        "path": path,
        "code": code,
        "primary": primary,
        "secondary": secondary,
        "message": message,
    }


def _covering_ancestor_rule(path: str, rules: Mapping[str, Any]) -> bool:
    return any(path.startswith(f"{rule_path}.") or path.startswith(f"{rule_path}[") for rule_path in rules)


def reconcile_case(case_dir: Path) -> Dict[str, Any]:
    manifest_path = case_dir / "manifest.yaml"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest missing at {manifest_path}")
    raw_manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest = CaseManifest.model_validate(raw_manifest)
    if manifest.secondary_reference is None:
        raise ValueError("REFERENCE_NOT_INDEPENDENT: secondaryReference is required")

    primary_path = case_dir / manifest.primary_reference.normalized_output
    secondary_path = case_dir / manifest.secondary_reference.normalized_output
    if not primary_path.is_file() or not secondary_path.is_file():
        raise FileNotFoundError("REFERENCE_OUTPUT_INCOMPLETE: normalized reference output missing")

    primary = json.loads(primary_path.read_text(encoding="utf-8"))
    secondary = json.loads(secondary_path.read_text(encoding="utf-8"))
    if not isinstance(primary, dict) or not isinstance(secondary, dict):
        raise ValueError("REFERENCE_OUTPUT_INCOMPLETE: normalized outputs must be JSON objects")

    rules = {rule.path: rule for rule in manifest.comparison_rules}
    primary_paths = set(_flatten_leaf_paths(primary))
    secondary_paths = set(_flatten_leaf_paths(secondary))
    all_paths = sorted(primary_paths | secondary_paths)
    comparisons: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []

    for path in all_paths:
        primary_found, primary_value = resolve_path(primary, path)
        secondary_found, secondary_value = resolve_path(secondary, path)
        if not primary_found or not secondary_found:
            conflicts.append(
                _conflict(
                    path=path,
                    code="REFERENCE_OUTPUT_INCOMPLETE",
                    primary=primary_value if primary_found else None,
                    secondary=secondary_value if secondary_found else None,
                    message="Field is missing from one normalized reference",
                )
            )
            continue
        rule = rules.get(path)
        if rule is None:
            if _covering_ancestor_rule(path, rules):
                continue
            conflicts.append(
                _conflict(
                    path=path,
                    code="REFERENCE_OUTPUT_UNRULED",
                    primary=primary_value,
                    secondary=secondary_value,
                    message="Normalized field has no comparison rule",
                )
            )
            continue
        passed, message = compare_value(
            primary_value,
            secondary_value,
            rule.comparator,
            rule.abs_tolerance,
            rule.rel_tolerance,
        )
        comparison = {
            "path": path,
            "comparator": rule.comparator.value,
            "primary": primary_value,
            "secondary": secondary_value,
            "passed": passed,
        }
        comparisons.append(comparison)
        if not passed:
            conflicts.append(
                _conflict(
                    path=path,
                    code="REFERENCE_IMPLEMENTATION_DISAGREEMENT",
                    primary=primary_value,
                    secondary=secondary_value,
                    message=message,
                )
            )

    unused_rules = sorted(set(rules).difference(all_paths))
    for path in unused_rules:
        primary_found, primary_value = resolve_path(primary, path)
        secondary_found, secondary_value = resolve_path(secondary, path)
        if not primary_found or not secondary_found:
            conflicts.append(
                _conflict(
                    path=path,
                    code="REFERENCE_OUTPUT_INCOMPLETE",
                    primary=primary_value if primary_found else None,
                    secondary=secondary_value if secondary_found else None,
                    message="Comparison rule does not resolve in normalized references",
                )
            )
            continue
        rule = rules[path]
        passed, message = compare_value(
            primary_value,
            secondary_value,
            rule.comparator,
            rule.abs_tolerance,
            rule.rel_tolerance,
        )
        comparisons.append(
            {
                "path": path,
                "comparator": rule.comparator.value,
                "primary": primary_value,
                "secondary": secondary_value,
                "passed": passed,
            }
        )
        if not passed:
            conflicts.append(
                _conflict(
                    path=path,
                    code="REFERENCE_IMPLEMENTATION_DISAGREEMENT",
                    primary=primary_value,
                    secondary=secondary_value,
                    message=message,
                )
            )

    report = {
        "schemaVersion": "1.0.0",
        "capabilityId": manifest.identity.capability_id,
        "goldenCaseId": manifest.identity.golden_case_id,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "reference_conflict" if conflicts else "consensus",
        "primary": {
            "engine": manifest.primary_reference.engine,
            "version": manifest.primary_reference.version,
            "sha256": _sha256(primary_path),
        },
        "secondary": {
            "engine": manifest.secondary_reference.engine,
            "version": manifest.secondary_reference.version,
            "sha256": _sha256(secondary_path),
        },
        "comparisons": comparisons,
        "unresolvedConflicts": conflicts,
    }
    expected_dir = case_dir / "expected"
    expected_dir.mkdir(parents=True, exist_ok=True)
    reconciliation_path = expected_dir / "reconciliation.json"
    reconciliation_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    # The manifest is the freeze gate's machine-readable source of truth.
    # Keep it synchronized with this freshly generated reconciliation report:
    # a previous conflict must not permanently block a later consensus, and a
    # newly observed conflict must immediately revoke an obsolete frozen
    # claim.  Consensus intentionally leaves the identity as ``quarantined``
    # or ``draft`` until freeze.py has re-hashed the complete asset set.
    evidence = raw_manifest.setdefault("evidence", {})
    if conflicts:
        evidence["unresolvedConflicts"] = [
            f"reference_conflict:{reconciliation_path.relative_to(case_dir).as_posix()}"
        ]
        raw_manifest.setdefault("identity", {})["status"] = "quarantined"
    else:
        evidence["unresolvedConflicts"] = []
    manifest_path.write_text(
        yaml.safe_dump(raw_manifest, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    if not conflicts:
        expected_path = case_dir / manifest.expected_output_path
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        expected_path.write_text(
            json.dumps(primary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return report


def _targets(args: argparse.Namespace) -> List[Path]:
    if args.capability:
        cases_dir = GOLDENS_DIR / args.capability / "cases"
        return sorted(path for path in cases_dir.iterdir() if path.is_dir()) if cases_dir.is_dir() else []
    if args.case:
        return sorted(path for path in GOLDENS_DIR.glob(f"**/cases/{args.case}") if path.is_dir())
    if args.all:
        return sorted(
            path
            for path in GOLDENS_DIR.glob("**/cases/*")
            if path.is_dir() and (path / "manifest.yaml").is_file()
        )
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile independent Golden references")
    parser.add_argument("--capability", type=str, help="Capability ID to reconcile")
    parser.add_argument("--case", type=str, help="Case ID to reconcile")
    parser.add_argument("--all", action="store_true", help="Reconcile all cases")
    args = parser.parse_args()
    targets = _targets(args)
    if not targets:
        print("No cases targeted for reconciliation.")
        return 1

    all_passed = True
    print(f"Reconciling {len(targets)} Golden case(s)...")
    for case_dir in targets:
        try:
            report = reconcile_case(case_dir)
        except Exception as exc:
            all_passed = False
            print(f" [ERROR] {case_dir.name}: {exc}")
            continue
        tag = "[CONSENSUS]" if report["status"] == "consensus" else "[CONFLICT]"
        print(f" {tag} {case_dir.name}")
        if report["status"] != "consensus":
            all_passed = False
            for conflict in report["unresolvedConflicts"]:
                print(f"    - {conflict['path']}: {conflict['code']}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
