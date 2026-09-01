"""Selective Test Execution Helper (Specification 29, Section 25).

Selects pytest target test files based on git diff or explicitly passed changed files.
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path
from typing import Any, List, Set

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = PROJECT_ROOT / "config" / "test-impact-map.yaml"


def get_git_changed_files() -> List[str]:
    """Gets list of changed files from git diff and status."""
    try:
        cmd = ["git", "diff", "--name-only", "HEAD"]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
        files = result.stdout.strip().splitlines() if result.returncode == 0 else []

        # Include untracked/modified
        cmd_status = ["git", "status", "--porcelain"]
        result_status = subprocess.run(
            cmd_status, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False
        )
        if result_status.returncode == 0:
            for line in result_status.stdout.strip().splitlines():
                if len(line) > 3:
                    files.append(line[3:].strip())

        return sorted(list(set(files)))
    except Exception:
        return []


def load_impact_map() -> dict[str, Any]:
    if not MAP_FILE.exists():
        return {"rules": {}, "fallbackMarker": "unit or contract"}
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def select_affected_tests(changed_files: List[str]) -> List[str]:
    impact_config = load_impact_map()
    rules: dict[str, List[str]] = impact_config.get("rules", {})
    selected_tests: Set[str] = set()

    for changed in changed_files:
        path_obj = Path(changed)

        # If a test file itself is changed, include it
        if ("test_" in path_obj.name or path_obj.name.endswith(".test.ts")) and path_obj.exists():
            selected_tests.add(changed)

        # Match against impact map rules
        for pattern, test_targets in rules.items():
            if fnmatch.fnmatch(changed, pattern) or fnmatch.fnmatch(
                changed.replace("\\", "/"), pattern
            ):
                for target in test_targets:
                    selected_tests.add(target)

    return sorted(list(selected_tests))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Select affected test files based on code changes."
    )
    parser.add_argument("--changed-files", nargs="*", help="List of changed file paths")
    parser.add_argument(
        "--git-diff", action="store_true", help="Automatically fetch changed files via git"
    )
    args = parser.parse_args()

    changed = args.changed_files or []
    if args.git_diff or not changed:
        git_files = get_git_changed_files()
        changed = sorted(list(set(changed + git_files)))

    if not changed:
        print("[INFO] No changed files detected.")
        return 0

    print(f"[IMPACT AUDIT] Evaluated {len(changed)} changed file(s):")
    for c in changed:
        print(f" - {c}")

    affected = select_affected_tests(changed)

    print("\n[SELECTED TESTS]:")
    if affected:
        for t in affected:
            print(f" - {t}")
    else:
        fallback = load_impact_map().get("fallbackMarker", "unit or contract")
        print(f' [FALLBACK] No specific target mapped. Recommended pytest marker: -m "{fallback}"')

    return 0


if __name__ == "__main__":
    sys.exit(main())
