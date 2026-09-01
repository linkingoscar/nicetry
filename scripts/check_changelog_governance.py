#!/usr/bin/env python3
"""Append-only governance check for docs/09-修改日志.md.

The file is split at the unique ``<!-- FROZEN-HISTORY-BEGIN -->`` marker:

* everything above the marker is the governed region: new entries are added
  here, newest first, under unique ``## YYYY-MM-DD`` headings in strictly
  descending order;
* everything below the marker is the frozen historical region. Its
  newline-normalised SHA-256 must equal the sidecar digest in
  ``docs/09-frozen.sha256``, so historical content cannot be deleted,
  replaced or reordered without an explicit, reviewed sidecar update.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

MARKER = "<!-- FROZEN-HISTORY-BEGIN -->"
DATE_HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2})$")
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def normalise(text: str) -> str:
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n")


def compute_frozen_digest(text: str) -> tuple[int, str]:
    """Return ``(marker_index, sha256)`` for the frozen region."""
    marker_index = text.find(MARKER + "\n")
    if marker_index < 0:
        raise ValueError(f"missing governance marker: {MARKER}")
    if text.find(MARKER, marker_index + 1) >= 0:
        raise ValueError(f"governance marker appears more than once: {MARKER}")
    frozen = text[marker_index + len(MARKER) + 1 :]
    digest = hashlib.sha256(frozen.encode("utf-8")).hexdigest()
    return marker_index, digest


def verify_changelog(path: Path, frozen_digest_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = normalise(path.read_text(encoding="utf-8"))
    except OSError as error:
        return [f"cannot read changelog: {error}"]

    try:
        marker_index, computed_digest = compute_frozen_digest(text)
    except ValueError as error:
        return [str(error)]

    try:
        expected_digest = frozen_digest_path.read_text(encoding="utf-8").strip()
    except OSError as error:
        return [f"cannot read frozen digest: {error}"]
    if computed_digest != expected_digest:
        errors.append(
            "frozen changelog history changed: "
            f"expected {expected_digest}, got {computed_digest}"
        )

    governed_lines = text[:marker_index].splitlines()
    dates: list[str] = []
    previous_date: str | None = None
    entries_in_section = 0
    for line_number, line in enumerate(governed_lines, start=1):
        if CONTROL_CHARACTERS.search(line):
            errors.append(
                f"line {line_number}: control characters are not allowed in governed entries"
            )
        if line.startswith("### "):
            entries_in_section += 1
        match = DATE_HEADING.match(line)
        if not match:
            continue
        current_date = match.group(1)
        if current_date in dates:
            errors.append(f"line {line_number}: duplicate date section {current_date}")
        dates.append(current_date)
        if previous_date is not None and current_date >= previous_date:
            errors.append(
                f"line {line_number}: date {current_date} is not strictly newer "
                f"than previous section {previous_date}"
            )
        if entries_in_section == 0 and previous_date is not None:
            errors.append(
                f"line {line_number}: date section {previous_date} has no ### entry"
            )
        previous_date = current_date
        entries_in_section = 0
    if previous_date is not None and entries_in_section == 0:
        errors.append(f"date section {previous_date} has no ### entry")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path)
    parser.add_argument("--frozen-digest", type=Path)
    arguments = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    changelog = arguments.file or root / "docs" / "09-修改日志.md"
    frozen_digest = arguments.frozen_digest or root / "docs" / "09-frozen.sha256"

    errors = verify_changelog(changelog, frozen_digest)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Changelog governance passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
