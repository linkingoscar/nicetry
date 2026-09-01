from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_contract_consistency", ROOT / "scripts" / "check_contract_consistency.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_contract_model_singleton_holds_on_real_source() -> None:
    assert MODULE.check_contract_model_singleton() == []


def test_real_schema_pydantic_openapi_parity_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["check_contract_consistency.py"])
    assert MODULE.main() == 0


def test_advanced_power_enum_has_no_unimplemented_values() -> None:
    schema = json.loads(
        (ROOT / "specs" / "advanced-analysis-spec.schema.json").read_text(encoding="utf-8")
    )
    power = MODULE.resolve_schema_node(schema, schema["$defs"]["powerAnalysis"])
    enum = power["properties"]["solveFor"]["enum"]
    assert "tost_power" not in enum
    assert "lowBound" not in power["properties"]
    assert "highBound" not in power["properties"]
    assert "ci_width" in enum
    assert "sensitivity" in enum
    assert "targetCIWidth" in power["properties"]


def test_power_pydantic_fields_align_with_schema_aliases() -> None:
    models = MODULE.load_models()
    power = models["PowerAnalysisSpec"]
    assert "target_ci_width" in power.model_fields
    assert power.model_fields["target_ci_width"].alias == "targetCIWidth"
    assert "sd" in power.model_fields
