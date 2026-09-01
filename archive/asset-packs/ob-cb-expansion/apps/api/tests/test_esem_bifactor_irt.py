import csv
import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.advanced_contracts import QuestionnaireMeasurementSpec
from app.services.advanced_analysis import advanced_analysis_registry
from app.settings import get_settings


def _run_measurement_fixture(spec_filename: str, *, add_group: bool = False) -> dict:
    settings = get_settings()
    root = settings.project_root
    spec_path = root / "apps/api/tests/fixtures/advanced" / spec_filename
    source_data_path = root / "apps/api/tests/fixtures/advanced/longitudinal/clpm-three-wave.csv"
    runner = root / "engine/R/run_advanced_analysis.R"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        data_path = source_data_path
        if add_group:
            rows = list(csv.DictReader(source_data_path.open(encoding="utf-8", newline="")))
            for row in rows:
                row["group"] = "g1" if int(row["subject_id"]) <= 50 else "g2"
            data_path = work / "grouped-clpm.csv"
            with data_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[*rows[0].keys()])
                writer.writeheader()
                writer.writerows(rows)
        elif spec.get("itemScale") == "ordinal":
            rows = list(csv.DictReader(source_data_path.open(encoding="utf-8", newline="")))
            for row in rows:
                for item_id in spec["itemIds"]:
                    value = float(row[item_id])
                    row[item_id] = str(max(1, min(5, int(round((value - 4.0) / 1.0) + 3))))
            data_path = work / "ordinal-clpm.csv"
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
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    return result


def test_esem_bifactor_irt_capability_slice_registered() -> None:
    capabilities = advanced_analysis_registry.capabilities()
    qm_cap = next((c for c in capabilities if c.get("family") == "questionnaire_measurement"), {})
    assert qm_cap
    slices = qm_cap.get("slices", [])  # type: ignore
    esem_slice = next(
        (s for s in slices if s.get("id") == "questionnaire_measurement.esem_bifactor_irt"), {}
    )  # type: ignore
    assert esem_slice.get("executionAvailable") is True  # type: ignore
    assert esem_slice.get("status") == "experimental"  # type: ignore


def test_esem_bifactor_irt_spec_validation() -> None:
    spec = QuestionnaireMeasurementSpec.model_validate(
        {
            "analysisId": "measure_test_01",
            "name": "Questionnaire measurement",
            "datasetVersionId": "dataset_001",
            "family": "questionnaire_measurement",
            "modelType": "esem_bifactor_irt",
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
    assert validated.get("sliceId") == "questionnaire_measurement.esem_bifactor_irt"
    assert validated.get("executionAvailable") is True


def test_questionnaire_reliability_r_runner_returns_construct_diagnostics() -> None:
    settings = get_settings()
    root = settings.project_root
    spec_path = (
        root / "apps/api/tests/fixtures/advanced/questionnaire-reliability-toothgrowth.spec.json"
    )
    data_path = root / "apps/api/tests/fixtures/advanced/reference/toothgrowth-factorial.csv"
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
    assert result["familyResult"]["reliability"]["available"] is True
    assert len(result["familyResult"]["reliability"]["constructs"]) == 2
    assert result["sampleFlow"]["included"] == 60


def test_esem_r_runner_returns_rotated_loadings() -> None:
    settings = get_settings()
    root = settings.project_root
    spec_path = root / "apps/api/tests/fixtures/advanced/questionnaire-esem-clpm.spec.json"
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
    esem = result["familyResult"]["esem"]
    assert esem["available"] is True
    assert esem["factorCount"] == 2
    assert len(esem["loadings"]) == 4


def test_efa_r_runner_returns_loadings_and_parallel_analysis() -> None:
    result = _run_measurement_fixture("questionnaire-efa-clpm.spec.json")
    efa = result["familyResult"]["efa"]
    assert efa["available"] is True
    assert efa["factorCount"] == 2
    assert len(efa["loadings"]) == 6
    assert efa["parallelAnalysis"] is not None


def test_cfa_r_runner_returns_fit_and_standardized_loadings() -> None:
    result = _run_measurement_fixture("questionnaire-cfa-clpm.spec.json")
    cfa = result["familyResult"]["cfa"]
    assert cfa["available"] is True
    assert cfa["converged"] is True
    assert cfa["itemCount"] == 6
    assert len(cfa["standardizedLoadings"]) == 6


def test_ordinal_cfa_r_runner_uses_wlsmv_thresholds() -> None:
    result = _run_measurement_fixture("questionnaire-cfa-ordinal-clpm.spec.json")
    cfa = result["familyResult"]["cfa"]
    assert cfa["available"] is True
    assert cfa["estimator"].endswith("WLSMV)")
    assert cfa["itemCount"] == 6


def test_measurement_invariance_r_runner_returns_selected_levels() -> None:
    result = _run_measurement_fixture("questionnaire-invariance-clpm.spec.json", add_group=True)
    invariance = result["familyResult"]["invariance"]
    assert invariance["available"] is True
    assert set(invariance["models"]) == {"configural", "metric", "scalar"}
