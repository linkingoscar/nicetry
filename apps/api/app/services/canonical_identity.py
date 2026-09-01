"""Canonical identities shared by versioned ResearchPath objects.

The workflow specification deliberately keeps identity generation in the
Python service layer.  UI labels, timestamps and database row ids must not
change the identity of an otherwise identical domain object.
"""

from __future__ import annotations

import hashlib
import json


def canonical_json(value: object) -> bytes:
    """Serialize a JSON-compatible value using the repository-wide rules."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    """Return the lowercase SHA-256 of :func:`canonical_json`."""

    return hashlib.sha256(canonical_json(value)).hexdigest()
