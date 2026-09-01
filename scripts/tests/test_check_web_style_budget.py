from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_web_style_budget", ROOT / "scripts" / "check_web_style_budget.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_baseline(path: Path, maximum: int) -> None:
    path.write_text(json.dumps({"maxInlineStyleObjects": maximum}), encoding="utf-8")


def test_counts_inline_style_objects(tmp_path: Path) -> None:
    source = tmp_path / "apps" / "web" / "src"
    source.mkdir(parents=True)
    component = source / "component.tsx"
    component.write_text("const a = <div style={{ color: 'red' }} />\n" * 3, encoding="utf-8")
    assert MODULE.count_inline_style_objects(tmp_path) == 3


def test_growth_above_budget_fails(tmp_path: Path) -> None:
    source = tmp_path / "apps" / "web" / "src"
    source.mkdir(parents=True)
    (source / "component.tsx").write_text(
        "const a = <div style={{ color: 'red' }} />\n" * 4, encoding="utf-8"
    )
    baseline = tmp_path / "budget.json"
    _write_baseline(baseline, 3)
    errors = MODULE.verify(tmp_path, baseline)
    assert errors and "grew" in errors[0]


def test_at_or_below_budget_passes(tmp_path: Path) -> None:
    source = tmp_path / "apps" / "web" / "src"
    source.mkdir(parents=True)
    (source / "component.tsx").write_text(
        "const a = <div style={{ color: 'red' }} />\n" * 3, encoding="utf-8"
    )
    baseline = tmp_path / "budget.json"
    _write_baseline(baseline, 3)
    assert MODULE.verify(tmp_path, baseline) == []


def test_real_workspace_is_within_budget() -> None:
    baseline = json.loads(
        (ROOT / "docs/baselines/web-style-budget.json").read_text(encoding="utf-8")
    )
    assert (
        MODULE.count_inline_style_objects(ROOT)
        <= int(baseline["maxInlineStyleObjects"])
    )
