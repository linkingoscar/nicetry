from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.goldens import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    evaluate_release,
    freeze,
    plan,
    reconcile,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_case(
    capability_dir: Path,
    case_id: str,
    scenario_type: str | None,
    *,
    release_evidence: bool,
) -> Path:
    case_dir = capability_dir / "cases" / case_id
    manifest: dict[str, object] = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": capability_dir.name,
            "status": "frozen",
        },
        "evidenceLevels": ["G2", "G7"],
        "primaryReference": {
            "engine": "primary-engine",
            "version": "1.2.3",
            "command": "python reference/primary/run.py",
            "containerDigest": "sha256:" + "1" * 64,
            "normalizedOutput": "reference/primary/normalized-output.json",
        },
    }
    if scenario_type is not None:
        manifest["scenarioType"] = scenario_type
    if release_evidence:
        manifest["evidenceLevels"] = ["G2", "G3", "G6", "G7"]
        manifest["secondaryReference"] = {
            "engine": "secondary-engine",
            "version": "4.5.6",
            "command": "python reference/secondary/run.py",
            "containerDigest": "sha256:" + "2" * 64,
            "normalizedOutput": "reference/secondary/normalized-output.json",
        }
        manifest["evidence"] = {"unresolvedConflicts": []}

    case_dir.mkdir(parents=True)
    (case_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    _write_json(case_dir / "reference/primary/normalized-output.json", {"estimate": 1})

    if release_evidence:
        _write_json(case_dir / "reference/secondary/normalized-output.json", {"estimate": 1})
        _write_json(
            case_dir / "data/source.json",
            {
                "sourceId": f"source-{case_id}",
                "sourceType": "official_package_dataset",
                "title": "Official fixture",
                "publisher": "Maintainer",
                "version": "1.0.0",
                "license": "MIT",
                "sha256": "a" * 64,
                "sourceTrustScore": 0.95,
                "allowedUse": ["testing", "redistribution"],
            },
        )
        _write_json(
            case_dir / "expected/reconciliation.json",
            {"status": "consensus", "unresolvedConflicts": []},
        )
    return case_dir


def _patch_runtime_checks(monkeypatch) -> None:
    monkeypatch.setattr(
        evaluate_release,
        "verify_case_manifest",
        lambda case_dir, require_sut: SimpleNamespace(passed=True),
    )
    monkeypatch.setattr(
        evaluate_release,
        "evaluate_metamorphic_invariants_for_case",
        lambda case_dir: {"passed": True},
    )


def test_generated_golden_plan_contains_all_mandatory_scenarios() -> None:
    generated = plan.create_sample_plan("measurement.cfa.continuous.mlr.v1")

    assert set(generated["scenarioTypes"]) == plan.REQUIRED_SCENARIO_TYPES
    assert len(generated["cases"]) == 4
    assert generated["evidencePlan"]["secondary"]["tool"]


def test_reconcile_requires_rule_covered_multisource_consensus(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schemaVersion": 1,
                "identity": {
                    "goldenCaseId": "case",
                    "capabilityId": "example.capability.v1",
                    "status": "draft",
                },
                "dataset": [],
                "specPath": "spec/analysis-spec.json",
                "expectedOutputPath": "expected/expected.json",
                "primaryReference": {
                    "engine": "engine-a",
                    "version": "1.0.0",
                    "command": "python run.py",
                    "normalizedOutput": "reference/primary/normalized-output.json",
                },
                "secondaryReference": {
                    "engine": "engine-b",
                    "version": "2.0.0",
                    "command": "python run.py",
                    "normalizedOutput": "reference/secondary/normalized-output.json",
                },
                "comparisonRules": [
                    {"path": "estimate", "comparator": "absolute", "absTolerance": 1e-8},
                    {"path": "method", "comparator": "exact"},
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_json(
        case_dir / "reference/primary/normalized-output.json",
        {"estimate": 1.0, "method": "closed_form"},
    )
    _write_json(
        case_dir / "reference/secondary/normalized-output.json",
        {"estimate": 1.0 + 1e-10, "method": "closed_form"},
    )

    report = reconcile.reconcile_case(case_dir)

    assert report["status"] == "consensus"
    assert report["unresolvedConflicts"] == []
    assert json.loads((case_dir / "expected/expected.json").read_text(encoding="utf-8"))[
        "estimate"
    ] == 1.0


def test_reconcile_conflict_does_not_replace_expected(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schemaVersion": 1,
                "identity": {
                    "goldenCaseId": "case",
                    "capabilityId": "example.capability.v1",
                },
                "dataset": [],
                "specPath": "spec/analysis-spec.json",
                "expectedOutputPath": "expected/expected.json",
                "primaryReference": {
                    "engine": "engine-a",
                    "normalizedOutput": "reference/primary/normalized-output.json",
                },
                "secondaryReference": {
                    "engine": "engine-b",
                    "normalizedOutput": "reference/secondary/normalized-output.json",
                },
                "comparisonRules": [
                    {"path": "estimate", "comparator": "absolute", "absTolerance": 1e-8}
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_json(case_dir / "reference/primary/normalized-output.json", {"estimate": 1.0})
    _write_json(case_dir / "reference/secondary/normalized-output.json", {"estimate": 2.0})
    _write_json(case_dir / "expected/expected.json", {"estimate": 99.0})

    report = reconcile.reconcile_case(case_dir)

    assert report["status"] == "reference_conflict"
    assert report["unresolvedConflicts"][0]["code"] == "REFERENCE_IMPLEMENTATION_DISAGREEMENT"
    assert json.loads((case_dir / "expected/expected.json").read_text(encoding="utf-8")) == {
        "estimate": 99.0
    }


def test_freeze_rejects_unresolved_reference_conflict(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "schemaVersion": 1,
                "identity": {
                    "goldenCaseId": "case",
                    "capabilityId": "example.capability.v1",
                    "status": "quarantined",
                },
                "dataset": [],
                "specPath": "spec/analysis-spec.json",
                "expectedOutputPath": "expected/expected.json",
                "evidence": {
                    "unresolvedConflicts": [
                        "reference_conflict:expected/reconciliation.json"
                    ]
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    _write_json(
        case_dir / "expected/reconciliation.json",
        {"status": "reference_conflict", "unresolvedConflicts": [{"path": "estimate"}]},
    )

    with pytest.raises(ValueError, match="must remain quarantined"):
        freeze.freeze_case(case_dir)

    freeze.freeze_case(case_dir, provenance_only=True)

    manifest = yaml.safe_load((case_dir / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["identity"]["status"] == "quarantined"
    assert (case_dir / "provenance/hashes.json").is_file()


def test_provenance_only_freeze_synchronizes_dataset_and_source_hashes(
    tmp_path: Path,
) -> None:
    case_dir = tmp_path / "case"
    (case_dir / "data").mkdir(parents=True)
    (case_dir / "expected").mkdir()
    (case_dir / "spec").mkdir()
    (case_dir / "data/input.csv").write_text("value\n1\n", encoding="utf-8")
    _write_json(
        case_dir / "data/source.json",
        {
            "sourceId": "source-1",
            "sha256": "stale",
        },
    )
    _write_json(case_dir / "expected/expected.json", {"status": "ok"})
    _write_json(case_dir / "spec/analysis-spec.json", {"family": "test"})
    (case_dir / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "identity": {"status": "quarantined"},
                "dataset": [{"path": "data/input.csv", "sha256": "stale"}],
                "specPath": "spec/analysis-spec.json",
                "expectedOutputPath": "expected/expected.json",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    hashes = freeze.freeze_case(case_dir, provenance_only=True)
    expected_hash = freeze.compute_file_sha256(case_dir / "data/input.csv")
    manifest = yaml.safe_load((case_dir / "manifest.yaml").read_text(encoding="utf-8"))
    source = json.loads((case_dir / "data/source.json").read_text(encoding="utf-8"))

    assert manifest["identity"]["status"] == "quarantined"
    assert manifest["dataset"][0]["sha256"] == expected_hash
    assert source["sha256"] == expected_hash
    assert hashes["data/input.csv"] == expected_hash
    assert hashes["data/source.json"] == freeze.compute_file_sha256(
        case_dir / "data/source.json"
    )


def test_g3_verification_rejects_tampered_source_record(tmp_path: Path) -> None:
    from tools.goldens.verify import verify_case_manifest  # pyright: ignore[reportMissingImports]

    source_case = (
        evaluate_release.GOLDENS_DIR
        / "power.t_test.analytic.v1"
        / "cases"
        / "t_test_two_sample"
    )
    case_dir = tmp_path / "t_test_two_sample"
    shutil.copytree(source_case, case_dir)
    source_path = case_dir / "data/source.json"
    source_path.write_text(source_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    result = verify_case_manifest(case_dir)

    assert not result.passed
    assert any(
        failure.path == "data/source.json" and "SHA-256 mismatch" in failure.message
        for failure in result.failures
    )


def test_single_reference_case_is_l1_not_release_candidate(
    tmp_path: Path, monkeypatch
) -> None:
    _patch_runtime_checks(monkeypatch)
    capability_dir = tmp_path / "example.capability.v1"
    _write_case(
        capability_dir,
        "standard",
        "normal_typical",
        release_evidence=False,
    )
    monkeypatch.setattr(evaluate_release, "PLANS_DIR", tmp_path / "golden-plans")

    result = evaluate_release.evaluate_capability_release(
        capability_dir, infrastructure_gates_passed=True
    )

    assert result["status"] == "autoverified_l1"
    assert not result["eligible"]
    assert any("two executable independent references" in reason for reason in result["reasons"])
    assert any("Scenario matrix missing" in reason for reason in result["reasons"])


def test_complete_multisource_evidence_reaches_release_candidate(
    tmp_path: Path, monkeypatch
) -> None:
    _patch_runtime_checks(monkeypatch)
    capability_id = "example.capability.v1"
    capability_dir = tmp_path / capability_id
    for scenario_type in evaluate_release.REQUIRED_SCENARIO_TYPES:
        _write_case(
            capability_dir,
            scenario_type,
            scenario_type,
            release_evidence=True,
        )

    plans_dir = tmp_path / "golden-plans"
    plans_dir.mkdir()
    (plans_dir / f"{capability_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "capabilityId": capability_id,
                "estimand": {"targets": ["estimate"]},
                "support": {"outcomes": ["continuous"]},
                "reject": ["unidentifiable"],
                "evidencePlan": {
                    "primary": {"tool": "primary-engine"},
                    "secondary": {"tool": "secondary-engine"},
                },
                "cases": sorted(evaluate_release.REQUIRED_SCENARIO_TYPES),
                "scenarioTypes": sorted(evaluate_release.REQUIRED_SCENARIO_TYPES),
                "requiredFields": ["estimate"],
                "tolerancePolicy": "iterative_v1",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(evaluate_release, "PLANS_DIR", plans_dir)
    _write_json(
        capability_dir / "provenance/mutation-report.json",
        {"status": "passed", "mutationScore": 0.9, "criticalMutantsKilled": 1.0},
    )
    _write_json(
        capability_dir / "provenance/offline-reproduction.json",
        {"status": "passed"},
    )

    result = evaluate_release.evaluate_capability_release(
        capability_dir, infrastructure_gates_passed=True
    )

    assert result["status"] == "autonomously_verified_release_candidate"
    assert result["eligible"]
    assert result["reasons"] == []


def test_infrastructure_failure_caps_complete_evidence_at_l3(
    tmp_path: Path, monkeypatch
) -> None:
    _patch_runtime_checks(monkeypatch)
    capability_id = "example.capability.v1"
    capability_dir = tmp_path / capability_id
    for scenario_type in evaluate_release.REQUIRED_SCENARIO_TYPES:
        _write_case(
            capability_dir,
            scenario_type,
            scenario_type,
            release_evidence=True,
        )
    plans_dir = tmp_path / "golden-plans"
    plans_dir.mkdir()
    (plans_dir / f"{capability_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "capabilityId": capability_id,
                "estimand": {"targets": ["estimate"]},
                "support": {"outcomes": ["continuous"]},
                "reject": ["unidentifiable"],
                "evidencePlan": {
                    "primary": {"tool": "primary-engine"},
                    "secondary": {"tool": "secondary-engine"},
                },
                "cases": ["normal", "complex", "boundary", "failure"],
                "scenarioTypes": sorted(evaluate_release.REQUIRED_SCENARIO_TYPES),
                "requiredFields": ["estimate"],
                "tolerancePolicy": "iterative_v1",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(evaluate_release, "PLANS_DIR", plans_dir)
    _write_json(
        capability_dir / "provenance/mutation-report.json",
        {"status": "passed", "mutationScore": 1.0, "criticalMutantsKilled": True},
    )
    _write_json(
        capability_dir / "provenance/offline-reproduction.json",
        {"status": "passed"},
    )

    result = evaluate_release.evaluate_capability_release(
        capability_dir,
        infrastructure_gates_passed=False,
        infrastructure_gate_reasons=["Reference independence gate failed"],
    )

    assert result["status"] == "autoverified_l3"
    assert not result["eligible"]
    assert "Reference independence gate failed" in result["reasons"]
