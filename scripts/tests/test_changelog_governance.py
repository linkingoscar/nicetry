from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_changelog_governance", ROOT / "scripts" / "check_changelog_governance.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

MARKER = MODULE.MARKER


def write_changelog(tmp_path: Path, governed: str, frozen: str = "## 2026-08-15\n") -> Path:
    path = tmp_path / "09-修改日志.md"
    path.write_text(
        "# 修改日志\n\n" + governed + MARKER + "\n" + frozen, encoding="utf-8"
    )
    digest = MODULE.compute_frozen_digest(MODULE.normalise(path.read_text(encoding="utf-8")))[1]
    (tmp_path / "09-frozen.sha256").write_text(digest + "\n", encoding="utf-8")
    return path


def test_ordered_sections_with_entries_pass(tmp_path: Path) -> None:
    governed = (
        "## 2026-08-16\n\n"
        "### fix(a): 修复\n\n- 验证：Quick 通过。\n\n"
        "## 2026-08-15\n\n"
        "### fix(b): 修复\n\n- 验证：Quick 通过。\n\n"
    )
    path = write_changelog(tmp_path, governed)
    assert MODULE.verify_changelog(path, tmp_path / "09-frozen.sha256") == []


def test_frozen_history_tampering_fails(tmp_path: Path) -> None:
    path = write_changelog(tmp_path, "## 2026-08-16\n\n### fix(a): 修复\n\n- 验证。\n\n")
    text = path.read_text(encoding="utf-8").replace("## 2026-08-15\n", "## 2026-08-14\n")
    path.write_text(text, encoding="utf-8")
    errors = MODULE.verify_changelog(path, tmp_path / "09-frozen.sha256")
    assert errors and any("frozen changelog history changed" in error for error in errors)


def test_out_of_order_dates_fail(tmp_path: Path) -> None:
    governed = (
        "## 2026-08-15\n\n### fix(a): 修复\n\n- 验证。\n\n"
        "## 2026-08-16\n\n### fix(b): 修复\n\n- 验证。\n\n"
    )
    path = write_changelog(tmp_path, governed)
    errors = MODULE.verify_changelog(path, tmp_path / "09-frozen.sha256")
    assert errors and any("not strictly newer" in error for error in errors)


def test_duplicate_date_sections_fail(tmp_path: Path) -> None:
    governed = (
        "## 2026-08-16\n\n### fix(a): 修复\n\n- 验证。\n\n"
        "## 2026-08-16\n\n### fix(b): 修复\n\n- 验证。\n\n"
    )
    path = write_changelog(tmp_path, governed)
    errors = MODULE.verify_changelog(path, tmp_path / "09-frozen.sha256")
    assert errors and any("duplicate date section" in error for error in errors)


def test_control_characters_fail(tmp_path: Path) -> None:
    governed = "## 2026-08-16\n\n### fix(a): \u0007修复\n\n- 验证。\n\n"
    path = write_changelog(tmp_path, governed)
    errors = MODULE.verify_changelog(path, tmp_path / "09-frozen.sha256")
    assert errors and any("control characters" in error for error in errors)


def test_date_section_without_entry_fails(tmp_path: Path) -> None:
    path = write_changelog(tmp_path, "## 2026-08-16\n\n")
    errors = MODULE.verify_changelog(path, tmp_path / "09-frozen.sha256")
    assert errors and any("has no ### entry" in error for error in errors)


def test_missing_marker_fails(tmp_path: Path) -> None:
    path = tmp_path / "09-修改日志.md"
    path.write_text("# 修改日志\n\n## 2026-08-16\n", encoding="utf-8")
    (tmp_path / "09-frozen.sha256").write_text("0" * 64 + "\n", encoding="utf-8")
    errors = MODULE.verify_changelog(path, tmp_path / "09-frozen.sha256")
    assert errors and any("missing governance marker" in error for error in errors)
