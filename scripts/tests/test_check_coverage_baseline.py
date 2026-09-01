from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_coverage_baseline", ROOT / "scripts" / "check-coverage-baseline.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_coverage_report(path: Path, modules: dict[str, int]) -> None:
    payload = {
        "totals": {"percent_covered": 80.0, "excluded_lines": 0},
        "files": {
            module: {
                "summary": {
                    "num_statements": 100,
                    "covered_lines": covered,
                    "excluded_lines": 0,
                }
            }
            for module, covered in modules.items()
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_module_baseline(path: Path, **overrides: object) -> None:
    payload = {
        "floor": 70.0,
        "maxExcludedLines": 40,
        "requiredModules": [
            "app/services/analysis_repository.py",
            "app/services/process_ownership.py",
        ],
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_module_floor_accepts_modules_above_floor(tmp_path: Path) -> None:
    report = tmp_path / "api.json"
    baseline = tmp_path / "module.json"
    write_coverage_report(
        report,
        {
            "app/services/analysis_repository.py": 91,
            "app/services/process_ownership.py": 72,
        },
    )
    write_module_baseline(baseline)
    assert MODULE.module_coverage_errors(report, baseline) == []


def test_module_floor_rejects_below_floor_and_missing_module(tmp_path: Path) -> None:
    report = tmp_path / "api.json"
    baseline = tmp_path / "module.json"
    write_coverage_report(
        report,
        {
            "app/services/analysis_repository.py": 69,
            "app/services/process_ownership.py": 88,
        },
    )
    write_module_baseline(
        baseline,
        requiredModules=[
            "app/services/analysis_repository.py",
            "app/services/process_ownership.py",
            "app/services/missing_module.py",
        ],
    )
    errors = MODULE.module_coverage_errors(report, baseline)
    assert any("below floor" in error for error in errors)
    assert any("missing for app/services/missing_module.py" in error for error in errors)


def test_excluded_lines_cap_fails_closed(tmp_path: Path) -> None:
    report = tmp_path / "api.json"
    baseline = tmp_path / "module.json"
    write_coverage_report(
        report,
        {"app/services/analysis_repository.py": 91, "app/services/process_ownership.py": 91},
    )
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["totals"]["excluded_lines"] = 41
    report.write_text(json.dumps(payload), encoding="utf-8")
    write_module_baseline(baseline)
    errors = MODULE.module_coverage_errors(report, baseline)
    assert errors and any("exceed cap" in error for error in errors)


def test_pragma_without_justification_fails_and_with_justification_passes(
    tmp_path: Path,
) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("def f():\n    return 1  # pragma: no cover\n", encoding="utf-8")
    errors = MODULE.pragma_justification_errors(tmp_path)
    assert any("requires an adjacent line" in error for error in errors)

    bad.write_text(
        "def f():  # no-cover-justification: platform-specific dormant path\n"
        "    return 1  # pragma: no cover\n",
        encoding="utf-8",
    )
    assert MODULE.pragma_justification_errors(tmp_path) == []
