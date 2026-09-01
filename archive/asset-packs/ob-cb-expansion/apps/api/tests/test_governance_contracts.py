from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from app.services.advanced_analysis import advanced_analysis_registry

ROOT = Path(__file__).resolve().parents[3]


def _load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_debt_register_is_valid_and_closed_items_have_evidence() -> None:
    schema = _load("docs/debt-register.schema.json")
    register = _load("docs/debt-register.json")

    Draft202012Validator(schema).validate(register)
    assert all(item["closureEvidence"] for item in register["items"] if item["status"] == "closed")


def test_advanced_capability_registry_matches_schema_families() -> None:
    specification = _load("specs/advanced-analysis-spec.schema.json")
    schema_families = set(specification["$defs"]["common"]["properties"]["family"]["enum"])
    capabilities = advanced_analysis_registry.capabilities()

    assert {capability["family"] for capability in capabilities} == schema_families
    assert all(capability["executionAvailable"] is True for capability in capabilities)
    assert all(capability["status"] == "experimental" for capability in capabilities)
    assert all(capability["slices"] for capability in capabilities)
    assert all(
        any(slice_["executionAvailable"] for slice_ in capability["slices"])
        for capability in capabilities
    )


def test_support_matrix_names_every_formally_supported_model() -> None:
    matrix = (ROOT / "docs/11-需求追踪矩阵.md").read_text(encoding="utf-8")

    for model in ("Model 1", "Model 4", "Model 6", "Model 7", "Model 8", "Model 14", "Model 15"):
        assert model in matrix
