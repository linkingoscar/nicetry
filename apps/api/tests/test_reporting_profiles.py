from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from app.services.report_facts import ensure_report_facts, report_fact_rows
from app.services.reporting_profiles import ensure_reporting_profiles

ROOT = Path(__file__).resolve().parents[3]


def test_reporting_profile_manifest_is_schema_valid_and_disclosure_only() -> None:
    payload = json.loads((ROOT / "specs" / "reporting-profiles.json").read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "specs" / "reporting-profiles.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(payload, schema)
    assert {profile["id"] for profile in payload["profiles"]} == {
        "apa_jars_quant",
        "strobe_observational",
        "consort_2025_randomized",
        "aea_data_code",
    }
    assert all(profile["purpose"] == "disclosure_completeness_only" for profile in payload["profiles"])
    assert all("不是完整" in profile["scopeNote"] or "不代表" in profile["scopeNote"] for profile in payload["profiles"])


def _observational_result() -> dict[str, object]:
    return {
        "run": {"id": "run_observational", "template": "model_4", "modelHash": "a" * 64},
        "claimBoundary": {
            "claimMode": "association",
            "causalLanguageAllowed": False,
            "temporalPrecedenceEstablished": False,
            "experimentalEffectEstablished": False,
        },
        "sampleFlow": {"original": 100, "included": 90, "excluded": 10, "missingMethod": "complete_cases"},
        "equations": [{
            "coefficients": [{
                "term": "x", "label": "X", "estimate": 0.4, "standardError": 0.1,
                "pValue": 0.001, "confidenceInterval": {"lower": 0.2, "upper": 0.6},
            }]
        }],
        "effects": [{
            "id": "indirect", "label": "Indirect", "estimate": 0.12,
            "confidenceInterval": {"lower": 0.03, "upper": 0.22},
        }],
        "diagnostics": [],
        "warnings": [{"code": "CROSS_SECTIONAL", "message": "Association only"}],
        "provenance": {
            "engine": "researchpath-r", "engineVersion": "0.3.0", "rVersion": "4.6.1",
            "dataSha256": "b" * 64, "seed": 1234,
        },
    }


def test_report_facts_cover_model_values_and_profiles_never_certify_quality_or_causality() -> None:
    result = _observational_result()
    ensure_report_facts(result)
    ensure_reporting_profiles(result)
    rows = report_fact_rows(result)
    assert any(row["sourcePath"] == "/effects/0/estimate" and row["value"] == 0.12 for row in rows)
    assert any(row["sourcePath"] == "/equations/0/coefficients/0/estimate" for row in rows)

    assessments = result["reportingProfileAssessments"]
    assert isinstance(assessments, list)
    strobe = next(item for item in assessments if item["profileId"] == "strobe_observational")
    consort = next(item for item in assessments if item["profileId"] == "consort_2025_randomized")
    assert strobe["applicable"] is True
    assert consort["applicable"] is False
    assert all(
        item["qualityCertified"] is False
        and item["causalCertified"] is False
        and item["publicationEligibilityGranted"] is False
        for item in assessments
    )


def test_randomized_profile_fails_closed_without_real_participant_flow() -> None:
    result = _observational_result()
    result["claimBoundary"]["experimentalEffectEstablished"] = True  # type: ignore[index]
    ensure_report_facts(result)
    ensure_reporting_profiles(result)
    assessments = result["reportingProfileAssessments"]
    assert isinstance(assessments, list)
    consort = next(item for item in assessments if item["profileId"] == "consort_2025_randomized")
    missing = {item["id"] for item in consort["items"] if not item["satisfied"]}
    assert consort["applicable"] is True
    assert {"allocation_flow", "analyzed", "harms", "registration"}.issubset(missing)
    assert consort["completeness"] < 1
    assert consort["publicationEligibilityGranted"] is False


def test_empirical_report_id_can_anchor_reference_only_report_facts() -> None:
    report: dict[str, object] = {
        "reportId": "empirical_0123456789abcdef",
        "sample": {"rowCount": 40, "itemCompleteCases": 36},
        "descriptives": [{"label": "Scale X", "n": 40, "mean": 3.2, "sd": 0.7, "missing": 0}],
        "warnings": [],
    }
    ensure_report_facts(report)
    facts = report["reportFacts"]
    assert isinstance(facts, list) and facts
    assert all(fact["sourceResultId"] == report["reportId"] for fact in facts)
    assert all("values" not in fact for fact in facts)
