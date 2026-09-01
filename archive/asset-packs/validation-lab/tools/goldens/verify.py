"""Verification runner for AI-Agent Gold Standard Bundles (Specification 28, Section 22.7 & 23).

Parses Case Manifests, verifies dataset SHA-256 hashes, runs canonicalized comparison,
and evaluates field-level tolerances and invariants.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, List, Tuple

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDENS_DIR = PROJECT_ROOT / "tests" / "goldens"

try:
    from tools.goldens.schema import (
        CaseManifest,
        CaseVerificationResult,
        ComparatorKind,
        EvidenceLevel,
        FieldFailure,
    )
except ImportError:
    # Fallback if executed directly as script
    sys.path.insert(0, str(PROJECT_ROOT))
    from tools.goldens.schema import (
        CaseManifest,
        CaseVerificationResult,
        ComparatorKind,
        EvidenceLevel,
        FieldFailure,
    )


def resolve_path(data: Any, path: str) -> Tuple[bool, Any]:
    """Retrieve value from nested dictionary/list using dot notation and list indexing.
    Example paths: 'estimates.beta', 'fixed_effects[0].estimate', 'fit.cfi'
    """
    current = data
    parts = path.replace("]", "").split(".")

    for part in parts:
        if "[" in part:
            key, idx_str = part.split("[")
            if key:
                if not isinstance(current, dict) or key not in current:
                    return False, None
                current = current[key]
            try:
                idx = int(idx_str)
                if not isinstance(current, list) or idx >= len(current):
                    return False, None
                current = current[idx]
            except ValueError:
                return False, None
        else:
            if not isinstance(current, dict) or part not in current:
                return False, None
            current = current[part]

    return True, current


def resolve_case_asset(case_dir: Path, relative_path: str) -> Path:
    case_root = case_dir.resolve()
    candidate = (case_root / relative_path).resolve()
    if not candidate.is_relative_to(case_root):
        raise ValueError(f"Golden asset escapes case directory: {relative_path}")
    return candidate


def compare_value(
    actual: Any,
    expected: Any,
    comparator: ComparatorKind,
    abs_tol: float,
    rel_tol: float,
) -> Tuple[bool, str]:
    if comparator == ComparatorKind.EXACT:
        if actual == expected:
            return True, ""
        return False, f"Expected exact {expected}, got {actual}"

    if comparator in (
        ComparatorKind.ABSOLUTE,
        ComparatorKind.RELATIVE,
        ComparatorKind.ABSOLUTE_RELATIVE,
    ):
        if (
            isinstance(actual, bool)
            or isinstance(expected, bool)
            or not isinstance(actual, (int, float))
            or not isinstance(expected, (int, float))
        ):
            return False, f"Non-numeric values for comparison: actual={actual}, expected={expected}"

        act_f = float(actual)
        exp_f = float(expected)
        if not math.isfinite(act_f) or not math.isfinite(exp_f):
            return False, f"Non-finite values are not comparable: actual={actual}, expected={expected}"

        if comparator == ComparatorKind.ABSOLUTE:
            diff = abs(act_f - exp_f)
            if diff <= abs_tol:
                return True, ""
            return False, f"Absolute difference {diff:.6g} exceeds tolerance {abs_tol}"

        if comparator == ComparatorKind.RELATIVE:
            diff = abs(act_f - exp_f)
            denom = abs(exp_f) if exp_f != 0 else 1.0
            rel_diff = diff / denom
            if rel_diff <= rel_tol:
                return True, ""
            return False, f"Relative difference {rel_diff:.6g} exceeds tolerance {rel_tol}"

        # ABSOLUTE_RELATIVE
        allowed = abs_tol + rel_tol * abs(exp_f)
        diff = abs(act_f - exp_f)
        if diff <= allowed:
            return True, ""
        return (
            False,
            f"Difference {diff:.6g} exceeds tolerance limit {allowed:.6g} (abs={abs_tol}, rel={rel_tol})",
        )

    if comparator == ComparatorKind.SIGN_INDETERMINATE:
        if (
            not isinstance(actual, bool)
            and not isinstance(expected, bool)
            and isinstance(actual, (int, float))
            and isinstance(expected, (int, float))
            and math.isfinite(float(actual))
            and math.isfinite(float(expected))
        ):
            act_f = float(actual)
            exp_f = float(expected)
            diff = min(abs(act_f - exp_f), abs(-act_f - exp_f))
            allowed = abs_tol + rel_tol * abs(exp_f)
            if diff <= allowed:
                return True, ""
            return (
                False,
                f"Sign indeterminate difference {diff:.6g} exceeds tolerance {allowed:.6g}",
            )

    if comparator == ComparatorKind.SET_EQUIVALENT:
        if isinstance(actual, list) and isinstance(expected, list):
            try:
                import numpy as np

                act_arr = np.array(actual, dtype=float)
                exp_arr = np.array(expected, dtype=float)

                if act_arr.shape == exp_arr.shape and act_arr.ndim == 2:
                    n_cols = act_arr.shape[1]
                    if n_cols > 16:
                        return False, "Set-equivalent matrices support at most 16 columns"

                    # Exact minimum-bottleneck bipartite assignment. This is
                    # global rather than the previous per-column greedy match,
                    # which could reject a valid factor permutation.
                    costs: list[list[tuple[float, bool]]] = []
                    for expected_index in range(n_cols):
                        expected_col = exp_arr[:, expected_index]
                        row: list[tuple[float, bool]] = []
                        for actual_index in range(n_cols):
                            actual_col = act_arr[:, actual_index]
                            positive = float(np.max(np.abs(actual_col - expected_col)))
                            negative = float(np.max(np.abs(-actual_col - expected_col)))
                            row.append(
                                (negative, True) if negative < positive else (positive, False)
                            )
                        costs.append(row)

                    states: dict[int, tuple[float, list[tuple[int, bool]]]] = {0: (0.0, [])}
                    for expected_index in range(n_cols):
                        next_states: dict[int, tuple[float, list[tuple[int, bool]]]] = {}
                        for mask, (current_cost, assignment) in states.items():
                            for actual_index in range(n_cols):
                                bit = 1 << actual_index
                                if mask & bit:
                                    continue
                                edge_cost, flipped = costs[expected_index][actual_index]
                                candidate = max(current_cost, edge_cost)
                                next_mask = mask | bit
                                incumbent = next_states.get(next_mask)
                                if incumbent is None or candidate < incumbent[0]:
                                    next_states[next_mask] = (
                                        candidate,
                                        [*assignment, (actual_index, flipped)],
                                    )
                        states = next_states

                    _, assignment = states[(1 << n_cols) - 1]
                    aligned_act = np.zeros_like(act_arr)
                    for expected_index, (actual_index, flipped) in enumerate(assignment):
                        aligned_act[:, expected_index] = (
                            -act_arr[:, actual_index]
                            if flipped
                            else act_arr[:, actual_index]
                        )

                    max_diff = float(np.max(np.abs(aligned_act - exp_arr)))
                    allowed = abs_tol + rel_tol * float(np.max(np.abs(exp_arr)))
                    if max_diff <= allowed:
                        return True, ""
                    return (
                        False,
                        f"Matched factor matrix max difference {max_diff:.6g} exceeds limit {allowed:.6g}",
                    )
                return False, "Set-equivalent comparison requires equally shaped 2D numeric arrays"
            except Exception as exc:
                return False, f"Factor matrix comparison failed: {exc}"

    if comparator == ComparatorKind.EXPECTED_FAILURE:
        if isinstance(actual, dict) and actual.get("status") in ("failed", "error"):
            return True, ""
        return False, f"Expected failure state, got actual={actual}"

    return False, f"Values are invalid for comparator '{comparator.value}'"


def _verify_sut_attestation(case_dir: Path, sut_file: Path) -> Tuple[bool, str]:
    """Bind a required SUT output to the adapter and manifest that generated it."""
    provenance_file = case_dir / "sut" / "provenance.json"
    runner = case_dir / "sut" / "run.py"
    if not runner.is_file():
        return False, "Production SUT adapter sut/run.py is missing"
    if not provenance_file.is_file():
        return False, "SUT provenance sut/provenance.json is missing"
    try:
        provenance = json.loads(provenance_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"SUT provenance is invalid: {exc}"

    bindings = {
        "runnerSha256": runner,
        "manifestSha256": case_dir / "manifest.yaml",
        "outputSha256": sut_file,
    }
    for field, path in bindings.items():
        expected_hash = provenance.get(field)
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected_hash != actual_hash:
            return False, f"SUT provenance hash mismatch for {field}"
    return True, ""


def verify_case_manifest(case_dir: Path, require_sut: bool = False) -> CaseVerificationResult:
    manifest_path = case_dir / "manifest.yaml"
    if not manifest_path.exists():
        return CaseVerificationResult(
            golden_case_id=case_dir.name,
            capability_id="unknown",
            passed=False,
            evidence_satisfied=False,
            failures=[
                FieldFailure(
                    path="manifest",
                    actual=None,
                    expected=True,
                    message="Manifest missing",
                    comparator="exact",
                )
            ],
        )

    with open(manifest_path, "r", encoding="utf-8") as f:
        raw_manifest = yaml.safe_load(f)

    manifest = CaseManifest.model_validate(raw_manifest)
    case_id = manifest.identity.golden_case_id
    cap_id = manifest.identity.capability_id
    has_g1_or_g2 = any(level.value in ("G1", "G2") for level in manifest.evidence_levels)
    has_g7 = any(level.value == "G7" for level in manifest.evidence_levels)

    failures: List[FieldFailure] = []

    # 1. Verify Dataset Hashes
    provenance_matched = True
    for ds_entry in manifest.dataset:
        try:
            ds_file = resolve_case_asset(case_dir, ds_entry.path)
        except ValueError as exc:
            provenance_matched = False
            failures.append(
                FieldFailure(
                    path=ds_entry.path,
                    actual=None,
                    expected="case-contained path",
                    message=str(exc),
                    comparator="path_containment",
                )
            )
            continue
        if not ds_file.exists():
            failures.append(
                FieldFailure(
                    path=ds_entry.path,
                    actual=None,
                    expected=True,
                    message=f"Dataset file missing: {ds_entry.path}",
                    comparator="exact",
                )
            )
            provenance_matched = False
            continue
        actual_sha = hashlib.sha256(ds_file.read_bytes()).hexdigest()
        if ds_entry.sha256 and ds_entry.sha256 != actual_sha:
            failures.append(
                FieldFailure(
                    path=ds_entry.path,
                    actual=actual_sha,
                    expected=ds_entry.sha256,
                    message=f"Dataset SHA mismatch for {ds_entry.path}",
                    comparator="exact",
                )
            )
            provenance_matched = False

    # Verify the immutable hash record. G3 cases must bind both independent
    # normalized references, their reconciliation and their source record.
    hash_record_path = case_dir / "provenance" / "hashes.json"
    try:
        hash_record = json.loads(hash_record_path.read_text(encoding="utf-8"))
        if not isinstance(hash_record, dict) or not hash_record:
            raise ValueError("hash record must be a non-empty JSON object")
    except Exception as exc:
        hash_record = {}
        provenance_matched = False
        failures.append(
            FieldFailure(
                path="provenance/hashes.json",
                actual=None,
                expected=True,
                message=f"Golden hash record is missing or invalid: {exc}",
                comparator="sha256",
            )
        )

    required_hashed_paths = {
        *(entry.path for entry in manifest.dataset),
        manifest.spec_path,
        manifest.expected_output_path,
    }
    if EvidenceLevel.G3 in manifest.evidence_levels:
        required_hashed_paths.add(manifest.primary_reference.normalized_output)
        if manifest.secondary_reference is not None:
            required_hashed_paths.add(manifest.secondary_reference.normalized_output)
        required_hashed_paths.update(
            {"data/source.json", "expected/reconciliation.json"}
        )

    for relative_path in sorted(required_hashed_paths):
        expected_hash = hash_record.get(relative_path)
        try:
            governed_file = resolve_case_asset(case_dir, relative_path)
        except ValueError as exc:
            provenance_matched = False
            failures.append(
                FieldFailure(
                    path=relative_path,
                    actual=None,
                    expected="case-contained path",
                    message=str(exc),
                    comparator="path_containment",
                )
            )
            continue
        if not isinstance(expected_hash, str) or not governed_file.is_file():
            provenance_matched = False
            failures.append(
                FieldFailure(
                    path=relative_path,
                    actual=expected_hash,
                    expected="recorded SHA-256",
                    message="Required Golden asset is absent from provenance/hashes.json",
                    comparator="sha256",
                )
            )
            continue
        actual_hash = hashlib.sha256(governed_file.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            provenance_matched = False
            failures.append(
                FieldFailure(
                    path=relative_path,
                    actual=actual_hash,
                    expected=expected_hash,
                    message="Golden governed asset SHA-256 mismatch",
                    comparator="sha256",
                )
            )
            continue

    # 2. Load Expected and Normalized Actual Output
    exp_file = case_dir / manifest.expected_output_path
    if not exp_file.exists():
        failures.append(
            FieldFailure(
                path=manifest.expected_output_path,
                actual=None,
                expected=True,
                message="Expected output file missing",
                comparator="exact",
            )
        )
        return CaseVerificationResult(
            golden_case_id=case_id,
            capability_id=cap_id,
            passed=False,
            evidence_satisfied=has_g1_or_g2 and has_g7 and provenance_matched,
            failures=failures,
            provenance_matched=provenance_matched,
        )

    expected_data = json.loads(exp_file.read_text(encoding="utf-8"))

    # SUT output resolution. Static bundle verification compares the independent
    # reference; end-to-end verification must use an attested production output.
    sut_file = case_dir / "sut" / "normalized-output.json"
    if require_sut:
        if not sut_file.is_file():
            failures.append(
                FieldFailure(
                    path="sut_output",
                    actual=None,
                    expected=True,
                    message="Required SUT output file sut/normalized-output.json is missing",
                    comparator="exact",
                )
            )
        else:
            attested, message = _verify_sut_attestation(case_dir, sut_file)
            if not attested:
                failures.append(
                    FieldFailure(
                        path="sut/provenance.json",
                        actual=None,
                        expected=True,
                        message=message,
                        comparator="provenance",
                    )
                )
    else:
        if manifest.primary_reference and manifest.primary_reference.normalized_output:
            sut_file = case_dir / manifest.primary_reference.normalized_output
        else:
            sut_file = case_dir / manifest.expected_output_path

    if failures or not sut_file.is_file():
        if not failures:
            failures.append(
                FieldFailure(
                    path="reference_output",
                    actual=None,
                    expected=True,
                    message="Primary reference output missing for bundle verification",
                    comparator="exact",
                )
            )
        return CaseVerificationResult(
            golden_case_id=case_id,
            capability_id=cap_id,
            passed=False,
            evidence_satisfied=has_g1_or_g2 and has_g7 and provenance_matched,
            failures=failures,
            provenance_matched=provenance_matched,
        )

    actual_data = json.loads(sut_file.read_text(encoding="utf-8"))

    # 3. Evaluate Comparison Rules
    for rule in manifest.comparison_rules:
        exp_found, exp_val = resolve_path(expected_data, rule.path)
        act_found, act_val = resolve_path(actual_data, rule.path)

        if not exp_found:
            if rule.required:
                failures.append(
                    FieldFailure(
                        path=rule.path,
                        actual=None,
                        expected=True,
                        message=f"Field path '{rule.path}' missing in expected output",
                        comparator=rule.comparator.value,
                    )
                )
            continue

        if not act_found:
            failures.append(
                FieldFailure(
                    path=rule.path,
                    actual=None,
                    expected=exp_val,
                    message=f"Field path '{rule.path}' missing in actual output",
                    comparator=rule.comparator.value,
                )
            )
            continue

        ok, msg = compare_value(
            actual=act_val,
            expected=exp_val,
            comparator=rule.comparator,
            abs_tol=rule.abs_tolerance,
            rel_tol=rule.rel_tolerance,
        )
        if not ok:
            failures.append(
                FieldFailure(
                    path=rule.path,
                    actual=act_val,
                    expected=exp_val,
                    message=msg,
                    comparator=rule.comparator.value,
                )
            )

    # 4. Evaluate Metamorphic Invariants (Spec 28, Section 16.5 Mode E)
    inv_file = case_dir / "expected" / "invariants.json"
    if inv_file.exists():
        try:
            invariants = json.loads(inv_file.read_text(encoding="utf-8"))
            for inv_path, inv_rule in invariants.items():
                found, val = resolve_path(actual_data, inv_path)
                if not found:
                    continue
                if isinstance(val, (int, float)):
                    if inv_rule == "non_negative" and float(val) < -1e-7:
                        failures.append(
                            FieldFailure(
                                path=inv_path,
                                actual=val,
                                expected=">=0",
                                message="Invariant non_negative violated",
                                comparator="invariant",
                            )
                        )
                    elif inv_rule == "probability" and not (0.0 <= float(val) <= 1.0 + 1e-6):
                        failures.append(
                            FieldFailure(
                                path=inv_path,
                                actual=val,
                                expected="[0,1]",
                                message="Invariant probability violated",
                                comparator="invariant",
                            )
                        )
        except Exception as inv_exc:
            failures.append(
                FieldFailure(
                    path="invariants",
                    actual=None,
                    expected=True,
                    message=f"Failed to check invariants: {inv_exc}",
                    comparator="invariant",
                )
            )

    # Evidence Level check: Must have at least G1 or G2, plus G7
    evidence_satisfied = has_g1_or_g2 and has_g7 and provenance_matched

    passed = (len(failures) == 0) and provenance_matched and evidence_satisfied

    return CaseVerificationResult(
        golden_case_id=case_id,
        capability_id=cap_id,
        passed=passed,
        evidence_satisfied=evidence_satisfied,
        failures=failures,
        provenance_matched=provenance_matched,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify AI-Agent Golden Cases")
    parser.add_argument("--capability", type=str, help="Capability ID to verify")
    parser.add_argument("--case", type=str, help="Case ID to verify")
    parser.add_argument("--all", action="store_true", help="Verify all cases")
    parser.add_argument(
        "--require-sut", action="store_true", help="Require sut/normalized-output.json to exist"
    )
    args = parser.parse_args()

    if not GOLDENS_DIR.exists():
        print(f"No goldens directory found at {GOLDENS_DIR}")
        return 1

    cases: list[Path] = []
    if args.capability:
        cap_dir = GOLDENS_DIR / args.capability
        if cap_dir.exists():
            cases.extend([d for d in (cap_dir / "cases").iterdir() if d.is_dir()])
    elif args.case:
        for p in GOLDENS_DIR.glob(f"**/cases/{args.case}"):
            if p.is_dir():
                cases.append(p)
    else:
        cases.extend(
            [
                p
                for p in GOLDENS_DIR.glob("**/cases/*")
                if p.is_dir() and (p / "manifest.yaml").exists()
            ]
        )

    if not cases:
        print("No golden cases found to verify.")
        return 1

    print(f"Verifying {len(cases)} Golden Case(s)...")
    results: list[CaseVerificationResult] = []

    for case_dir in cases:
        res = verify_case_manifest(case_dir, require_sut=args.require_sut)
        results.append(res)
        status_str = "[PASS]" if res.passed else "[FAIL]"
        print(f" {status_str} {res.capability_id} / {res.golden_case_id}")
        if not res.passed:
            for f in res.failures:
                print(f"    - [{f.comparator}] {f.path}: {f.message}")

    passed_count = sum(1 for r in results if r.passed)
    print(f"\nVerification summary: {passed_count}/{len(results)} cases passed.")

    return 0 if passed_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
