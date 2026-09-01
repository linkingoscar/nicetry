from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_source_lines", ROOT / "scripts" / "check_source_lines.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_count_lines_includes_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "padded.py"
    path.write_text("\n\nreturn_1 = 1\n\n", encoding="utf-8")
    assert MODULE.count_lines(path) == 4


def test_blank_padding_cannot_bypass_ceiling(tmp_path: Path) -> None:
    source = tmp_path / "src.py"
    source.write_text("\n" * 50 + "x = 1\n", encoding="utf-8")
    limits = {
        "hardCeiling": 10,
        "excludeNames": [],
        "thinEntryPoints": {},
        "scopes": [],
        "sourceRoots": ["."],
    }
    errors = MODULE.scan(tmp_path, limits)
    assert any("hard ceiling" in error for error in errors)


def test_baseline_freezes_but_does_not_allow_growth(tmp_path: Path) -> None:
    source = tmp_path / "src.py"
    source.write_text("x = 1\n" * 5, encoding="utf-8")
    limits = {
        "hardCeiling": 2,
        "excludeNames": [],
        "thinEntryPoints": {},
        "scopes": [],
        "sourceRoots": ["."],
    }
    assert MODULE.scan(tmp_path, limits, {"src.py": 5}) == []
    source.write_text("x = 1\n" * 6, encoding="utf-8")
    errors = MODULE.scan(tmp_path, limits, {"src.py": 5})
    assert errors and any("hard ceiling" in error for error in errors)


def test_real_workspace_passes_with_audited_baselines() -> None:
    baseline = json.loads(
        (ROOT / "docs/baselines/source-line-baselines.json").read_text(encoding="utf-8")
    )
    files = {
        str(relative): int(lines) for relative, lines in baseline.get("files", {}).items()
    }
    assert MODULE.scan(ROOT, MODULE.LIMITS, files) == []
