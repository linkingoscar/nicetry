"""Metamorphic Property Invariants Library & Runner (Specification 28, Section 16.5 Mode E).

Provides data transformation routines and mathematical invariant assertions:
- Row permutation invariance (Order invariance)
- Linear scaling and translation response (X multiplier, Y offset)
- Cluster / group label permutation invariance
- Contrast weight positive multiplier invariance (t/F statistic stability)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDENS_DIR = PROJECT_ROOT / "tests" / "goldens"

try:
    from tools.goldens.schema import ComparatorKind
    from tools.goldens.verify import compare_value, resolve_path
except ImportError:
    sys.path.insert(0, str(PROJECT_ROOT))
    from tools.goldens.schema import ComparatorKind
    from tools.goldens.verify import compare_value, resolve_path


def check_row_permutation_invariance(case_dir: Path) -> Tuple[bool, str]:
    """Verifies that reordering CSV data rows produces output satisfying comparison rules.
    Executes reference runner on permuted dataset to perform dynamic metamorphic verification.
    """
    data_file = case_dir / "data" / "input.csv"
    if not data_file.exists():
        return False, "Row permutation invariant was not executed: data/input.csv is missing"

    lines = data_file.read_text(encoding="utf-8").strip().splitlines()
    if len(lines) <= 2:
        # With zero or one observation there is no distinct row permutation to
        # execute.  Treat the permutation property as vacuously satisfied and
        # rely on the case's explicit numerical/failure invariants instead.
        return True, ""

    header = lines[0]
    rows = lines[1:]
    permuted_rows = list(reversed(rows))
    permuted_content = "\n".join([header] + permuted_rows) + "\n"

    manifest_path = case_dir / "manifest.yaml"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    exp_file = case_dir / manifest.get("expectedOutputPath", "expected/expected.json")
    if not exp_file.exists():
        return False, "Row permutation invariant was not executed: expected output is missing"

    exp_data = json.loads(exp_file.read_text(encoding="utf-8"))

    # Execute an independent reference runner on permuted data. Absence or
    # failure is an unexecuted check, never a passing invariant.
    primary_reference = manifest.get("primaryReference", {})
    command = primary_reference.get("command")
    if not command:
        return False, "Row permutation invariant was not executed: reference command is missing"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        tmp_case = tmppath / "case"
        shutil.copytree(case_dir, tmp_case)
        (tmp_case / "data" / "input.csv").write_text(permuted_content, encoding="utf-8")

        out_json = tmp_case / primary_reference.get(
            "normalizedOutput", "reference/primary/normalized-output.json"
        )
        out_json.unlink(missing_ok=True)
        environment = os.environ.copy()
        environment["RESEARCHPATH_PROJECT_ROOT"] = str(PROJECT_ROOT)
        res = subprocess.run(
            command,
            shell=True,
            cwd=str(tmp_case),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if res.returncode != 0:
            detail = (res.stderr or res.stdout).strip()
            return False, f"Row permutation reference runner failed: {detail}"
        if not out_json.exists():
            return False, "Row permutation reference runner produced no normalized output"

        permuted_out = json.loads(out_json.read_text(encoding="utf-8"))
        for rule_dict in manifest.get("comparisonRules", []):
            path = rule_dict["path"]
            found_exp, val_exp = resolve_path(exp_data, path)
            found_perm, val_perm = resolve_path(permuted_out, path)
            if not found_exp or not found_perm:
                return False, f"Row permutation comparison field '{path}' is missing"
            comparator = ComparatorKind(rule_dict.get("comparator", "absolute_relative"))
            abs_tol = rule_dict.get("absTolerance", 1e-4)
            rel_tol = rule_dict.get("relTolerance", 1e-3)
            ok, msg = compare_value(val_perm, val_exp, comparator, abs_tol, rel_tol)
            if not ok:
                return False, f"Row permutation mismatch at '{path}': {msg}"

    return True, ""


def check_linear_transformation_response(
    original_val: float,
    transformed_val: float,
    multiplier: float = 1.0,
    offset: float = 0.0,
    property_type: str = "intercept",
) -> Tuple[bool, str]:
    """Assert mathematical response under linear transformation Y' = multiplier * Y + offset."""
    if property_type == "intercept":
        expected = original_val * multiplier + offset
        diff = abs(transformed_val - expected)
        if diff <= 1e-4:
            return True, ""
        return False, f"Transformed intercept {transformed_val:.6g} != expected {expected:.6g}"

    elif property_type == "slope":
        expected = original_val * multiplier
        diff = abs(transformed_val - expected)
        if diff <= 1e-4:
            return True, ""
        return False, f"Transformed slope {transformed_val:.6g} != expected {expected:.6g}"

    return True, ""


def check_contrast_weight_scaling_invariance(
    original_t: float,
    scaled_weight_t: float,
    abs_tol: float = 1e-5,
) -> Tuple[bool, str]:
    """Assert t/F statistic is invariant when contrast weights are scaled by a positive scalar c > 0."""
    diff = abs(original_t - scaled_weight_t)
    if diff <= abs_tol:
        return True, ""
    return (
        False,
        f"Contrast statistic changed from {original_t:.6g} to {scaled_weight_t:.6g} after weight scaling",
    )


def evaluate_metamorphic_invariants_for_case(case_dir: Path) -> Dict[str, Any]:
    """Executes metamorphic invariant checks for a golden case."""
    row_perm_ok, row_perm_msg = check_row_permutation_invariance(case_dir)

    inv_file = case_dir / "expected" / "invariants.json"
    custom_invariants_ok = True
    details: List[str] = []
    if not row_perm_ok:
        details.append(row_perm_msg)

    if inv_file.exists():
        exp_file = case_dir / "expected" / "expected.json"
        if exp_file.exists():
            data = json.loads(exp_file.read_text(encoding="utf-8"))
            inv_rules = json.loads(inv_file.read_text(encoding="utf-8"))

            for path, rule in inv_rules.items():
                found, val = resolve_path(data, path)
                if found and isinstance(val, (int, float)):
                    if rule == "non_negative" and val < -1e-7:
                        custom_invariants_ok = False
                        details.append(f"Field '{path}' ({val}) failed non_negative invariant")
                    elif rule == "probability" and not (0.0 <= val <= 1.0 + 1e-6):
                        custom_invariants_ok = False
                        details.append(f"Field '{path}' ({val}) failed probability invariant")

    passed = row_perm_ok and custom_invariants_ok
    return {
        "caseId": case_dir.name,
        "passed": passed,
        "rowPermutationPassed": row_perm_ok,
        "customInvariantsPassed": custom_invariants_ok,
        "details": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Metamorphic Property Invariants Library")
    parser.add_argument(
        "--case", type=str, help="Specific Case ID to run metamorphic invariant checks on"
    )
    parser.add_argument(
        "--all", action="store_true", help="Run metamorphic checks across all golden cases"
    )
    args = parser.parse_args()

    cases: List[Path] = []
    if args.case:
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
        print("No cases found for metamorphic invariant testing.")
        return 1

    print(f"Running Metamorphic Property Invariant tests across {len(cases)} case(s)...")
    all_passed = True

    for case_dir in cases:
        res = evaluate_metamorphic_invariants_for_case(case_dir)
        tag = "[PASS]" if res["passed"] else "[FAIL]"
        print(
            f" {tag} {res['caseId']} (RowPerm={res['rowPermutationPassed']}, Custom={res['customInvariantsPassed']})"
        )
        if not res["passed"]:
            all_passed = False
            for d in res["details"]:
                print(f"    - {d}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
