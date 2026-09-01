from __future__ import annotations

import math

import pytest

from app.services.canonical_identity import canonical_json, canonical_sha256


def test_canonical_json_is_utf8_sorted_and_compact() -> None:
    assert canonical_json({"b": "值", "a": [2, 1]}) == '{"a":[2,1],"b":"值"}'.encode(
        "utf-8"
    )
    assert canonical_sha256({"a": 1, "b": 2}) == canonical_sha256({"b": 2, "a": 1})


def test_canonical_json_preserves_list_order() -> None:
    assert canonical_sha256({"values": [1, 2]}) != canonical_sha256({"values": [2, 1]})


def test_canonical_json_rejects_non_finite_float() -> None:
    with pytest.raises(ValueError):
        canonical_json({"value": math.nan})
