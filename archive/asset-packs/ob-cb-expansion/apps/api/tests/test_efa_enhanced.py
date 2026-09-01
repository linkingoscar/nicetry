from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.advanced_contracts import QuestionnaireMeasurementSpec
from app.settings import get_settings


def test_questionnaire_spec_extraction_method_validation() -> None:
    base_spec = {
        "family": "questionnaire_measurement",
        "modelType": "efa",
        "analysisId": "efa_test_01",
        "name": "EFA Method Test",
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
        "extractionMethod": "paf",
    }
    parsed = QuestionnaireMeasurementSpec.model_validate(base_spec)
    assert parsed.extraction_method == "paf"


def test_efa_paf_extraction_and_diagnostics() -> None:
    settings = get_settings()
    root = settings.project_root
    spec_path = root / "apps/api/tests/fixtures/advanced/questionnaire-efa-clpm.spec.json"
    source_data_path = root / "apps/api/tests/fixtures/advanced/longitudinal/clpm-three-wave.csv"
    runner = root / "engine/R/run_advanced_analysis.R"

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["extractionMethod"] = "paf"

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        input_path = work / "input.json"
        output_path = work / "output.json"
        input_path.write_text(
            json.dumps(
                {"spec": spec, "dataPath": str(source_data_path), "artifactDirectory": str(work)}
            ),
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

    efa = result["familyResult"]["efa"]
    assert efa["available"] is True
    assert efa["method"] == "paf"
    assert "diagnostics" in efa
    assert len(efa["diagnostics"]) > 0
    first_diag = efa["diagnostics"][0]
    assert "communality" in first_diag
    assert "complexity" in first_diag
    assert "crossLoading" in first_diag
