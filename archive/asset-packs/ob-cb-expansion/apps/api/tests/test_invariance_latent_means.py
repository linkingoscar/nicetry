from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.advanced_contracts import QuestionnaireMeasurementSpec
from app.settings import get_settings


def test_questionnaire_spec_partial_released_parameters_validation() -> None:
    base_spec = {
        "family": "questionnaire_measurement",
        "modelType": "measurement_invariance",
        "analysisId": "inv_test_01",
        "name": "Invariance Partial Test",
        "datasetVersionId": "dataset_1234567890abcdef",
        "itemIds": ["var_1_12345678", "var_2_12345678", "var_3_12345678", "var_4_12345678"],
        "constructs": [
            {
                "id": "construct_a",
                "label": "Construct A",
                "itemIds": ["var_1_12345678", "var_2_12345678"],
            },
            {
                "id": "construct_b",
                "label": "Construct B",
                "itemIds": ["var_3_12345678", "var_4_12345678"],
            },
        ],
        "groupVariableId": "var_5_12345678",
        "partialReleasedParameters": ["F_construct_a =~ var_2_12345678"],
    }
    parsed = QuestionnaireMeasurementSpec.model_validate(base_spec)
    assert parsed.partial_released_parameters == ["F_construct_a =~ var_2_12345678"]


def test_invariance_latent_means_execution() -> None:
    settings = get_settings()
    root = settings.project_root
    spec_path = root / "apps/api/tests/fixtures/advanced/questionnaire-invariance-clpm.spec.json"
    source_data_path = root / "apps/api/tests/fixtures/advanced/longitudinal/clpm-three-wave.csv"
    runner = root / "engine/R/run_advanced_analysis.R"

    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        # Create grouped data for invariance test
        import csv

        rows = list(csv.DictReader(source_data_path.open(encoding="utf-8", newline="")))
        for row in rows:
            row["group"] = "g1" if int(row["subject_id"]) <= 50 else "g2"
        data_path = work / "grouped-clpm.csv"
        with data_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[*rows[0].keys()])
            writer.writeheader()
            writer.writerows(rows)

        input_path = work / "input.json"
        output_path = work / "output.json"
        input_path.write_text(
            json.dumps({"spec": spec, "dataPath": str(data_path), "artifactDirectory": str(work)}),
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(runner),
                str(input_path),
                str(output_path),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        result = json.loads(output_path.read_text(encoding="utf-8"))

    inv = result["familyResult"]["invariance"]
    assert inv["available"] is True
    assert "models" in inv
    assert "latentMeans" in inv
    assert len(inv["latentMeans"]) > 0
    first_mean = inv["latentMeans"][0]
    assert "estimate" in first_mean
    assert "ciLower" in first_mean
    assert "ciUpper" in first_mean
