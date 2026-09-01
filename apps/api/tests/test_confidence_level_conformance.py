"""Static guard for declared confidence-level ownership in active inference paths."""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SEM_CONFORMANCE_TEST = PROJECT_ROOT / "engine" / "R" / "tests" / "testthat" / "test-confidence-level-conformance.R"
STATISTICAL_GUIDE = PROJECT_ROOT / "docs" / "02-统计方法与报告规范.md"
ACTIVE_ROOTS = (
    PROJECT_ROOT / "engine" / "R" / "lib",
    PROJECT_ROOT / "engine" / "R" / "run_analysis.R",
    PROJECT_ROOT / "engine" / "R" / "run_advanced_analysis.R",
    PROJECT_ROOT / "engine" / "R" / "run_empirical_analysis.R",
    PROJECT_ROOT / "apps" / "api" / "app",
    PROJECT_ROOT / "apps" / "web" / "src",
)
FORBIDDEN_PATTERNS = (
    re.compile(r"(?<![0-9.])0\.975(?![0-9.])"),
    re.compile(r"(?<![0-9.])1\.9599(?![0-9.])"),
    re.compile(r"(?<![0-9.])1\.96(?![0-9.])"),
    re.compile(r"qnorm\s*\(\s*0\.975"),
    re.compile(r"qt\s*\(\s*0\.975"),
)
ALLOWLIST = {
    "engine/R/lib/diary_bayesian_dsem.R": {
        "marker": 'confidenceLevelSource = "method_definition"',
        "reason": "Posterior/prior predictive diagnostic interval is a method-defined 95% interval, not a general inferential CI.",
    }
}


def _active_files() -> list[Path]:
    files: list[Path] = []
    for root in ACTIVE_ROOTS:
        if root.is_file():
            files.append(root)
            continue
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".r", ".py", ".ts", ".tsx"}
            and not path.name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
            and "vendor" not in path.parts
        )
    return files


def test_fixed_confidence_literals_are_allowlisted() -> None:
    violations: list[str] = []
    for path in _active_files():
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        allowlisted = ALLOWLIST.get(relative)
        if allowlisted is not None:
            assert allowlisted["marker"] in text, f"allowlist marker missing from {relative}"
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in FORBIDDEN_PATTERNS):
                if allowlisted is None:
                    violations.append(f"{relative}:{line_number}: {line.strip()}")
    assert not violations, "Fixed confidence literal in active path; route through declared level or add a justified method-definition allowlist:\n" + "\n".join(violations)


def test_confidence_literal_allowlist_is_explicit_and_live() -> None:
    active_paths = {path.relative_to(PROJECT_ROOT).as_posix() for path in _active_files()}
    for relative, entry in ALLOWLIST.items():
        assert relative in active_paths
        assert entry["reason"]


def test_sem_confidence_claim_matches_public_result_contract() -> None:
    test_text = SEM_CONFORMANCE_TEST.read_text(encoding="utf-8")
    guide_text = STATISTICAL_GUIDE.read_text(encoding="utf-8")
    assert "SEM path and group-difference intervals follow the declared confidence matrix" in test_text
    assert "SEM 的 90%/95%/99% execution conformance matrix 已冻结" in guide_text
    assert "`semResult.loadings`、`semResult.paths` 与多组路径差异" in guide_text
