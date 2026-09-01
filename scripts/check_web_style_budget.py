#!/usr/bin/env python3
"""Freeze and slowly reduce the frontend inline-style object count."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "docs" / "baselines" / "web-style-budget.json"


def count_inline_style_objects(root: Path) -> int:
    total = 0
    for path in (root / "apps" / "web" / "src").rglob("*.tsx"):
        text = path.read_text(encoding="utf-8", errors="replace")
        total += text.count("style={{")
    return total


def verify(root: Path, baseline_path: Path) -> list[str]:
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    maximum = int(payload["maxInlineStyleObjects"])
    observed = count_inline_style_objects(root)
    if observed > maximum:
        return [
            f"inline style objects grew: {observed} > baseline {maximum}; "
            "migrate them to tokens.css/CSS modules instead of raising the budget"
        ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args()
    errors = verify(args.root, args.baseline)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(
        f"Inline style budget passed: {count_inline_style_objects(args.root)} "
        f"<= {json.loads(args.baseline.read_text(encoding='utf-8'))['maxInlineStyleObjects']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
