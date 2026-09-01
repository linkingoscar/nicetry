import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.advanced_contracts import QuestionnaireMeasurementSpec
from app.services.advanced_analysis import advanced_analysis_registry
from app.settings import get_settings


def test_common_method_bias_capability_slice_registered() -> None:
    capabilities = advanced_analysis_registry.capabilities()
    qm_cap = next((c for c in capabilities if c.get("family") == "questionnaire_measurement"), {})
    assert qm_cap
    slices = qm_cap.get("slices", [])  # type: ignore
    cmb_slice = next(
        (s for s in slices if s.get("id") == "questionnaire_measurement.common_method_bias"), {}
    )  # type: ignore
    assert cmb_slice.get("executionAvailable") is True  # type: ignore
    assert cmb_slice.get("status") == "experimental"  # type: ignore


def test_common_method_bias_spec_validation() -> None:
    spec = QuestionnaireMeasurementSpec.model_validate(
        {
            "analysisId": "cmb_test_01",
            "name": "Common method bias",
            "datasetVersionId": "dataset_001",
            "family": "questionnaire_measurement",
            "modelType": "common_method_bias",
            "itemIds": ["item_01", "item_02", "item_03", "item_04"],
            "constructs": [
                {"id": "construct_01", "label": "Construct 1", "itemIds": ["item_01", "item_02"]},
                {"id": "construct_02", "label": "Construct 2", "itemIds": ["item_03", "item_04"]},
            ],
            "seed": 20260720,
        }
    )
    validated = advanced_analysis_registry.validate(spec)
    assert validated.get("valid") is True
    assert validated.get("sliceId") == "questionnaire_measurement.common_method_bias"
    assert validated.get("executionAvailable") is True


def test_common_method_bias_r_runner_returns_ulmc_diagnostic() -> None:
    settings = get_settings()
    root = settings.project_root
    spec_path = root / "apps/api/tests/fixtures/advanced/questionnaire-cmb-clpm.spec.json"
    data_path = root / "apps/api/tests/fixtures/advanced/longitudinal/clpm-three-wave.csv"
    runner = root / "engine/R/run_advanced_analysis.R"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
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
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    cmb = result["familyResult"]["commonMethodBias"]
    assert cmb["ulmc"]["available"] is True
    assert cmb["ulmc"]["modelComparison"]
