from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from app.capability_catalog import ACTIVE_CAPABILITIES

ROOT = Path(__file__).resolve().parents[3]


def _manifest() -> dict[str, object]:
    return json.loads(
        (ROOT / "specs" / "statistical-validation.json").read_text(encoding="utf-8")
    )


def test_statistical_validation_manifest_is_schema_valid_and_executable() -> None:
    payload = _manifest()
    schema = json.loads(
        (ROOT / "specs" / "statistical-validation.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(payload, schema)
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    registered = {item.slice_id for item in ACTIVE_CAPABILITIES}
    for scenario in scenarios:
        assert isinstance(scenario, dict)
        assert scenario["capabilitySliceId"] in registered
        evidence_path = ROOT / str(scenario["evidenceTest"])
        assert evidence_path.exists()
        assert str(scenario["id"]) in evidence_path.read_text(encoding="utf-8")
        assert scenario["status"] == "enforced"


def test_same_implementation_or_simulation_never_claims_external_validation() -> None:
    payload = _manifest()
    scenarios = payload["scenarios"]
    assert isinstance(scenarios, list)
    non_external_levels = {"same_implementation", "same_package", "simulation_calibration"}
    for scenario in scenarios:
        assert isinstance(scenario, dict)
        oracle = scenario["oracle"]
        assert isinstance(oracle, dict)
        if oracle["level"] in non_external_levels:
            assert oracle["validationClaim"] == "internal"
        if oracle["validationClaim"] == "external":
            assert oracle["level"] in {"independent_implementation", "official_reference"}
            assert "runner" in str(oracle["independence"]).lower()

    dsem = next(item for item in ACTIVE_CAPABILITIES if item.slice_id == "empirical.diary.dsem")
    dsem_scenario = next(
        item
        for item in scenarios
        if isinstance(item, dict) and item["capabilitySliceId"] == dsem.slice_id
    )
    assert dsem_scenario["oracle"]["validationClaim"] == "internal"
    assert dsem.validation_level == "unvalidated"
    assert dsem.publication_eligibility == "ineligible"
