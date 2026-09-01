from __future__ import annotations

from typing import Any

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


def escape_spreadsheet_formula(value: Any) -> Any:
    """Force user-controlled formula-like text to remain a literal cell value."""
    if not isinstance(value, str) or not value:
        return value
    candidate = value.lstrip(" ")
    if candidate.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value
