"""Mutation testing gate script (Specification 28, Section 27).

Injects targeted statistical and manifest mutations into comparison rule target fields
to verify that the Golden Case verification engine catches mutants (Mutation Score >= 0.85).
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDENS_DIR = PROJECT_ROOT / "tests" / "goldens"

try:
    from tools.goldens.schema import CaseManifest
    from tools.goldens.verify import verify_case_manifest
except ImportError:
    sys.path.insert(0, str(PROJECT_ROOT))
    from tools.goldens.schema import CaseManifest
    from tools.goldens.verify import verify_case_manifest


def mutate_nested_path(data: Dict[str, Any], path: str, factor: float = -1.5) -> bool:
    """Targeted mutation on exact path specified in comparison rules."""
    parts = path.replace("]", "").split(".")
    curr = data

    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        if "[" in part:
            key, idx_str = part.split("[")
            idx = int(idx_str)
            if key:
                if key not in curr or not isinstance(curr[key], list):
                    return False
                curr = curr[key]
            if idx >= len(curr):
                return False
            if is_last:
                if isinstance(curr[idx], (int, float)):
                    curr[idx] = float(curr[idx]) * factor + 5.0
                    return True
            else:
                curr = curr[idx]
        else:
            if part not in curr:
                return False
            if is_last:
                if isinstance(curr[part], bool):
                    curr[part] = not curr[part]
                    return True
                if isinstance(curr[part], (int, float)):
                    curr[part] = float(curr[part]) * factor + 5.0
                    return True
            else:
                curr = curr[part]
    return False


def run_mutation_test_suite(
    capability_id: str | None = None, *, write_reports: bool = False
) -> Tuple[int, int, float]:
    cases = [
        p
        for p in GOLDENS_DIR.glob("**/cases/*")
        if p.is_dir()
        and (p / "manifest.yaml").exists()
        and (capability_id is None or p.parent.parent.name == capability_id)
    ]

    if not cases:
        print("No Golden Cases found for mutation testing.")
        return 0, 0, 1.0

    print(f"Running Mutation Testing Gate across {len(cases)} Golden Case(s)...")

    total_mutants = 0
    killed_mutants = 0
    by_capability: Dict[str, Dict[str, int]] = {}

    for case_dir in cases:
        manifest_path = case_dir / "manifest.yaml"
        with open(manifest_path, "r", encoding="utf-8") as f:
            raw_manifest = yaml.safe_load(f)
        manifest = CaseManifest.model_validate(raw_manifest)
        capability_counts = by_capability.setdefault(
            manifest.identity.capability_id, {"total": 0, "killed": 0}
        )

        # Baseline check
        base_res = verify_case_manifest(case_dir)
        if not base_res.passed:
            print(f"[SKIP] Base case {case_dir.name} failed verification before mutation")
            continue

        if manifest.primary_reference and manifest.primary_reference.normalized_output:
            primary_out = case_dir / manifest.primary_reference.normalized_output
        else:
            primary_out = case_dir / manifest.expected_output_path
        if not primary_out.exists():
            continue

        original_data = json.loads(primary_out.read_text(encoding="utf-8"))

        # Inject mutant per comparison rule
        for rule in manifest.comparison_rules:
            mutated_data = copy.deepcopy(original_data)
            success = mutate_nested_path(mutated_data, rule.path, factor=-2.0)
            if not success:
                continue

            total_mutants += 1
            capability_counts["total"] += 1
            # Mutate an isolated copy of the primary reference. The verifier's
            # static mode intentionally compares that reference with expected;
            # no checked-in SUT artifact is overwritten or deleted.
            with tempfile.TemporaryDirectory(prefix="researchpath-mutant-") as temporary:
                isolated_case = Path(temporary) / case_dir.name
                shutil.copytree(case_dir, isolated_case)
                if manifest.primary_reference and manifest.primary_reference.normalized_output:
                    isolated_primary = isolated_case / manifest.primary_reference.normalized_output
                else:
                    isolated_primary = isolated_case / manifest.expected_output_path
                isolated_primary.parent.mkdir(parents=True, exist_ok=True)
                isolated_primary.write_text(
                    json.dumps(mutated_data, indent=2) + "\n", encoding="utf-8"
                )
                res = verify_case_manifest(isolated_case)
                if not res.passed:
                    killed_mutants += 1
                    capability_counts["killed"] += 1
                else:
                    print(
                        f" [SURVIVED] Mutant on path '{rule.path}' survived in {case_dir.name}"
                    )

    score = killed_mutants / total_mutants if total_mutants > 0 else 0.0
    print(f"\nMutation Testing Summary: {killed_mutants}/{total_mutants} mutants killed.")
    print(f"Mutation Score: {score * 100:.1f}% (Required Threshold: >= 85.0%)")

    if write_reports:
        generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for current_capability, counts in sorted(by_capability.items()):
            capability_score = (
                counts["killed"] / counts["total"] if counts["total"] > 0 else 0.0
            )
            critical_killed = counts["total"] > 0 and counts["killed"] == counts["total"]
            report = {
                "schemaVersion": "1.0.0",
                "capabilityId": current_capability,
                "generatedAt": generated_at,
                "status": (
                    "passed" if capability_score >= 0.85 and critical_killed else "failed"
                ),
                "totalMutants": counts["total"],
                "killedMutants": counts["killed"],
                "mutationScore": capability_score,
                "criticalMutantsKilled": critical_killed,
            }
            report_path = GOLDENS_DIR / current_capability / "provenance" / "mutation-report.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            print(f"Capability mutation report written: {report_path.relative_to(PROJECT_ROOT)}")

    return total_mutants, killed_mutants, score


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Golden mutation testing")
    parser.add_argument("--capability", help="Limit mutation testing to one capability ID")
    parser.add_argument(
        "--write-reports",
        action="store_true",
        help="Write capability-level provenance/mutation-report.json records",
    )
    args = parser.parse_args()
    total, killed, score = run_mutation_test_suite(
        args.capability, write_reports=args.write_reports
    )
    if total > 0 and score >= 0.85:
        print("[PASS] Mutation Testing Gate satisfied.")
        return 0
    else:
        print(f"[FAIL] Mutation Score {score * 100:.1f}% is below 85% threshold.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
