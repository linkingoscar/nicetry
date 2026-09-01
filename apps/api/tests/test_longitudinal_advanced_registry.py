from __future__ import annotations

import csv
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.advanced_contracts import LongitudinalModelSpec
from app.services.advanced_analysis import advanced_analysis_registry
from app.settings import get_settings

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "advanced" / "longitudinal"


def _run_longitudinal_runner(spec: dict, data_path: Path) -> dict:
    settings = get_settings()
    with tempfile.TemporaryDirectory() as temporary:
        input_path = Path(temporary) / "input.json"
        output_path = Path(temporary) / "result.json"
        input_path.write_text(
            json.dumps(
                {
                    "spec": spec,
                    "dataPath": str(data_path),
                    "progressPath": str(Path(temporary) / "progress.json"),
                    "cancelPath": str(Path(temporary) / "cancel.requested"),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        environment["LC_ALL"] = "English_United States.utf8"
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(settings.project_root / "engine" / "R" / "run_advanced_analysis.R"),
                str(input_path),
                str(output_path),
            ],
            cwd=settings.project_root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        progress = json.loads(
            (Path(temporary) / "progress.json").read_text(encoding="utf-8")
        )
        assert progress["stage"] == "succeeded"
        assert progress["progress"] == 1.0
        return json.loads(output_path.read_text(encoding="utf-8"))


def _clpm_spec(model_type: str, missing: str = "complete_cases") -> dict:
    return {
        "schemaVersion": "0.1.0",
        "analysisId": f"{model_type}_fixture_001",
        "name": f"{model_type} fixture",
        "datasetVersionId": "dataset_fixture_001",
        "confidenceLevel": 0.95,
        "seed": 20260720,
        "family": "longitudinal_model",
        "modelType": model_type,
        "subjectId": "subject_id",
        "waves": [
            {"wave": "T1", "timeValue": 0, "variables": {"x": "x1", "y": "y1"}},
            {"wave": "T2", "timeValue": 1, "variables": {"x": "x2", "y": "y2"}},
            {"wave": "T3", "timeValue": 2, "variables": {"x": "x3", "y": "y3"}},
        ],
        "estimator": "ML" if missing == "complete_cases" else "MLR",
        "missing": missing,
        "invarianceLevels": [],
    }


def test_longitudinal_model_family_is_registered_and_all_slices_are_executable() -> None:
    capabilities = {
        capability["family"]: capability
        for capability in advanced_analysis_registry.capabilities()
    }
    longitudinal = capabilities.get("longitudinal_model")
    assert longitudinal is not None
    assert longitudinal["executionAvailable"] is True
    assert {
        item["id"]
        for item in longitudinal["slices"]
        if item["executionAvailable"]
    } == {
        "longitudinal_model.observed_growth",
        "longitudinal_model.traditional_clpm",
        "longitudinal_model.ri_clpm",
        "longitudinal_model.latent_growth",
        "longitudinal_model.longitudinal_invariance",
    }


def test_longitudinal_model_spec_validation_reports_execution_available() -> None:
    spec = LongitudinalModelSpec.model_validate(
        {
            "schemaVersion": "0.1.0",
            "analysisId": "long_test_01",
            "name": "Longitudinal test",
            "family": "longitudinal_model",
            "datasetVersionId": "dataset_001",
            "modelType": "ri_clpm",
            "subjectId": "subject",
            "confidenceLevel": 0.95,
            "seed": 20260815,
            "estimator": "MLR",
            "missing": "fiml",
            "waves": [
                {"wave": "w1", "timeValue": 0, "variables": {"x": "x1", "y": "y1"}},
                {"wave": "w2", "timeValue": 1, "variables": {"x": "x2", "y": "y2"}},
                {"wave": "w3", "timeValue": 2, "variables": {"x": "x3", "y": "y3"}},
            ],
            "invarianceLevels": [],
        }
    )
    validated = advanced_analysis_registry.validate(spec)
    assert validated["valid"] is True
    assert validated["sliceId"] == "longitudinal_model.ri_clpm"
    assert validated["executionAvailable"] is True
    advanced_analysis_registry.assert_executable(spec)


@pytest.mark.parametrize("missing", ["available_rows_ml"])
def test_available_rows_ml_is_rejected_by_the_contract(missing: str) -> None:
    with pytest.raises(ValidationError):
        LongitudinalModelSpec.model_validate(
            {
                "schemaVersion": "0.1.0",
                "analysisId": "long_bad_missing",
                "name": "Longitudinal bad missing",
                "family": "longitudinal_model",
                "datasetVersionId": "dataset_001",
                "modelType": "growth_curve",
                "subjectId": "subject",
                "confidenceLevel": 0.95,
                "seed": 20260815,
                "estimator": "ML",
                "missing": missing,
                "waves": [
                    {"wave": "w1", "timeValue": 0, "variables": {"x": "x1"}},
                    {"wave": "w2", "timeValue": 1, "variables": {"x": "x2"}},
                    {"wave": "w3", "timeValue": 2, "variables": {"x": "x3"}},
                ],
                "invarianceLevels": [],
            }
        )


def test_observed_growth_runner_enters_without_undefined_growth_singular() -> None:
    spec = {
        "schemaVersion": "0.1.0",
        "analysisId": "growth_fixture_001",
        "name": "Observed growth fixture",
        "datasetVersionId": "dataset_growth_fixture_001",
        "confidenceLevel": 0.95,
        "seed": 20260720,
        "family": "longitudinal_model",
        "modelType": "growth_curve",
        "subjectId": "subject_id",
        "waves": [
            {"wave": "T1", "timeValue": 0, "variables": {"outcome": "y1"}},
            {"wave": "T2", "timeValue": 1, "variables": {"outcome": "y2"}},
            {"wave": "T3", "timeValue": 2, "variables": {"outcome": "y3"}},
            {"wave": "T4", "timeValue": 4, "variables": {"outcome": "y4"}},
        ],
        "estimator": "ML",
        "missing": "complete_cases",
        "invarianceLevels": [],
    }
    source = FIXTURE_ROOT / "growth-unequal-time.csv"
    with (
        source.open(newline="", encoding="utf-8") as input_file,
        tempfile.TemporaryDirectory() as temporary,
    ):
        reader = csv.DictReader(input_file)
        assert reader.fieldnames is not None
        data_path = Path(temporary) / "growth.csv"
        with data_path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(
                output_file,
                fieldnames=["subject_id", "y1", "y2", "y3", "y4"],
            )
            writer.writeheader()
            for row in reader:
                writer.writerow(
                    {
                        "subject_id": row["subject_id"],
                        "y1": row["y_0"],
                        "y2": row["y_1"],
                        "y3": row["y_2"],
                        "y4": row["y_4"],
                    }
                )
        result = _run_longitudinal_runner(spec, data_path)
        assert result["familyResult"]["modelType"] == "growth_curve"
        assert result["familyResult"]["missingMethod"] == "complete_cases"


def test_cross_lagged_runner_reaches_shared_result_assembly() -> None:
    result = _run_longitudinal_runner(
        _clpm_spec("cross_lagged_panel", "complete_cases"),
        FIXTURE_ROOT / "clpm-three-wave.csv",
    )
    assert result["familyResult"]["modelType"] == "cross_lagged_panel"
    assert result["familyResult"]["missingMethod"] == "complete_cases"


def test_ri_clpm_runner_enters_with_the_registered_family() -> None:
    result = _run_longitudinal_runner(
        _clpm_spec("ri_clpm", "fiml"),
        FIXTURE_ROOT / "clpm-three-wave.csv",
    )
    assert result["familyResult"]["modelType"] == "ri_clpm"
    assert result["familyResult"]["missingMethod"] == "fiml"
