from __future__ import annotations

import importlib.util
from pathlib import Path


def _release_evidence_module():
    root = Path(__file__).resolve().parents[3]
    path = root / "scripts" / "release-evidence.py"
    spec = importlib.util.spec_from_file_location("release_evidence", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_evidence_marks_skipped_release_steps_incomplete() -> None:
    module = _release_evidence_module()

    evidence = module.collect(
        "passed",
        mode="Release",
        run_id="run-123",
        duration_seconds=12.5,
        required_steps=["quality-gate", "r-runtime-benchmark"],
        completed_steps=["quality-gate"],
        skipped_steps=["r-runtime-benchmark"],
    )

    assert evidence["testStatus"] == "incomplete"
    assert evidence["evidenceComplete"] is False
    assert evidence["runId"] == "run-123"
    assert evidence["steps"] == {
        "required": ["quality-gate", "r-runtime-benchmark"],
        "completed": ["quality-gate"],
        "skipped": ["r-runtime-benchmark"],
        "missing": ["r-runtime-benchmark"],
    }


def test_release_evidence_marks_complete_release_passed() -> None:
    module = _release_evidence_module()

    evidence = module.collect(
        "passed",
        mode="Release",
        required_steps=["quality-gate"],
        completed_steps=["quality-gate"],
    )

    assert evidence["testStatus"] == "passed"
    assert evidence["evidenceComplete"] is True
    assert evidence["steps"]["missing"] == []
