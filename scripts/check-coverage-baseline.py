from __future__ import annotations

import argparse
import json
from pathlib import Path

PRAGMA_MARKER = "# pragma: no cover"
JUSTIFICATION_MARKER = "no-cover-justification:"


def read_coverage(path: Path) -> float:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "totals" in payload:
        return float(payload["totals"]["percent_covered"])
    return float(payload["percent_covered"])


def read_module_baseline(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "floor": 70.0,
        "maxExcludedLines": 40,
        "requiredModules": [],
    }
    required.update(payload)
    return required


def module_coverage_errors(report: Path, baseline: Path) -> list[str]:
    payload = json.loads(report.read_text(encoding="utf-8"))
    config = read_module_baseline(baseline)
    raw_files = payload.get("files") or {}
    files = {key.replace("\\", "/"): value for key, value in raw_files.items()}
    floor = float(config["floor"])
    errors: list[str] = []
    for module in config["requiredModules"]:
        summary = (files.get(module) or {}).get("summary")
        if summary is None:
            errors.append(f"module coverage missing for {module}")
            continue
        statements = int(summary.get("num_statements") or 0)
        covered = int(summary.get("covered_lines") or 0)
        percent = (covered / statements * 100.0) if statements else 0.0
        if percent + 1e-9 < floor:
            errors.append(
                f"module {module} line coverage {percent:.2f}% is below floor {floor:.2f}%"
            )
    max_excluded = int(config["maxExcludedLines"])
    total_excluded = int((payload.get("totals") or {}).get("excluded_lines") or 0)
    if total_excluded > max_excluded:
        errors.append(
            f"excluded lines {total_excluded} exceed cap {max_excluded}; "
            "remove pragma exclusions instead of raising the cap"
        )
    return errors


def pragma_justification_errors(root: Path) -> list[str]:
    errors: list[str] = []
    for path in root.rglob("*.py"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if PRAGMA_MARKER not in line:
                continue
            previous = lines[index - 1] if index > 0 else ""
            if JUSTIFICATION_MARKER not in previous and JUSTIFICATION_MARKER not in line:
                errors.append(
                    f"{path}:{index + 1}: {PRAGMA_MARKER.strip()} requires an adjacent "
                    f"line containing {JUSTIFICATION_MARKER!r}"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reject API coverage regressions against the audited baselines."
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--module-baseline", type=Path)
    parser.add_argument("--pragma-root", type=Path)
    args = parser.parse_args()

    observed = read_coverage(args.report)
    required = read_coverage(args.baseline)
    errors: list[str] = []
    if observed + 1e-9 < required:
        errors.append(
            f"API coverage regressed: {observed:.4f}% is below the audited "
            f"baseline of {required:.4f}%"
        )
    if args.module_baseline is not None:
        errors.extend(module_coverage_errors(args.report, args.module_baseline))
    if args.pragma_root is not None:
        errors.extend(pragma_justification_errors(args.pragma_root))
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)
    print(f"API coverage baseline passed: {observed:.4f}% >= {required:.4f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
