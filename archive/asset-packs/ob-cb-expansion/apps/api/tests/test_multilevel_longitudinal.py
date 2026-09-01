import csv
import json
import os
import random
import subprocess
import tempfile
from pathlib import Path

from app.advanced_contracts import (
    LongitudinalModelSpec,
    LongitudinalWave,
    MultilevelModelSpec,
    RandomEffect,
)
from app.services.advanced_analysis import advanced_analysis_registry
from app.settings import get_settings


def test_multilevel_model_slice_validation() -> None:
    spec = MultilevelModelSpec(
        analysis_id="mlm_test_01",
        name="Two Level LMM Analysis",
        dataset_version_id="dataset_01",
        family="multilevel_model",
        distribution="gaussian",
        outcome_id="score",
        cluster_variable_id="team_id",
        fixed_effect_ids=["x1"],
        random_effects=[RandomEffect(grouping_variable_id="team_id")],
    )
    result = advanced_analysis_registry.validate(spec)
    assert result["valid"] is True
    assert result["executionAvailable"] is True
    assert result["capabilityId"] == "multilevel_model.gaussian.two_level"


def test_multilevel_aggregation_slice_validation() -> None:
    spec = MultilevelModelSpec(
        analysis_id="agg_test_01",
        name="Aggregation evidence",
        dataset_version_id="dataset_01",
        family="multilevel_model",
        analysis_type="aggregation",
        cluster_variable_id="team_id",
        scale_item_ids=["item_01", "item_02"],
        scale_min=1,
        scale_max=5,
    )
    result = advanced_analysis_registry.validate(spec)
    assert result["valid"] is True
    assert result["executionAvailable"] is True
    assert result["capabilityId"] == "multilevel_model.aggregation.icc_rwg"


def test_multilevel_aggregation_r_runner_returns_scale_aware_evidence() -> None:
    settings = get_settings()
    root = settings.project_root
    spec_path = (
        root / "apps/api/tests/fixtures/advanced/multilevel/aggregation-sleepstudy.spec.json"
    )
    data_path = root / "apps/api/tests/fixtures/advanced/reference/sleepstudy.csv"
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
    evidence = result["familyResult"]["aggregation"]
    assert evidence["scale"]["min"] == 0
    assert evidence["scale"]["max"] == 90000
    assert evidence["numClusters"] == 18
    assert len(evidence["rwgByCluster"]) == 18


def test_ri_clpm_r_runner_returns_within_person_cross_lags() -> None:
    settings = get_settings()
    root = settings.project_root
    spec_path = root / "apps/api/tests/fixtures/advanced/longitudinal/ri-clpm-three-wave.spec.json"
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
    assert result["familyResult"]["modelType"] == "ri_clpm"
    assert result["familyResult"]["parameters"]


def test_latent_growth_r_runner_preserves_unequal_time_values() -> None:
    settings = get_settings()
    root = settings.project_root
    spec_path = (
        root / "apps/api/tests/fixtures/advanced/longitudinal/latent-growth-unequal-time.spec.json"
    )
    runner = root / "engine/R/run_advanced_analysis.R"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        data_path = work / "latent-growth.csv"
        rng = random.Random(20260720)
        with data_path.open("w", encoding="utf-8", newline="") as handle:
            handle.write("subject_id,y1,y2,y3,y4\n")
            for subject_id in range(1, 201):
                intercept = rng.gauss(0.0, 1.0)
                slope = rng.gauss(0.5, 0.1)
                values = [
                    10.0 + intercept + slope * time_value + rng.gauss(0.0, 0.5)
                    for time_value in (0, 1, 2, 4)
                ]
                handle.write(f"{subject_id},{values[0]},{values[1]},{values[2]},{values[3]}\n")
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
    assert result["familyResult"]["modelType"] == "latent_growth"
    assert result["familyResult"]["timeValues"] == [0, 1, 2, 4]
    assert result["familyResult"]["parameters"]


def test_longitudinal_invariance_r_runner_returns_standard_bundle() -> None:
    settings = get_settings()
    root = settings.project_root
    spec_path = (
        root
        / "apps/api/tests/fixtures/advanced/longitudinal/longitudinal-invariance-clpm.spec.json"
    )
    source_data_path = root / "apps/api/tests/fixtures/advanced/longitudinal/clpm-three-wave.csv"
    runner = root / "engine/R/run_advanced_analysis.R"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
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
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    assert result["familyResult"]["modelType"] == "longitudinal_invariance"
    assert result["familyResult"]["invariance"]["available"] is True
    assert set(result["familyResult"]["invariance"]["models"]) == {"configural", "metric", "scalar"}


def test_longitudinal_model_slice_validation() -> None:
    spec = LongitudinalModelSpec(
        analysis_id="long_test_01",
        name="Longitudinal RI-CLPM Analysis",
        dataset_version_id="dataset_01",
        family="longitudinal_model",
        model_type="ri_clpm",
        subject_id="sub_01",
        waves=[
            LongitudinalWave(wave="T1", time_value=1.0, variables={"x": "x_t1", "y": "y_t1"}),
            LongitudinalWave(wave="T2", time_value=2.0, variables={"x": "x_t2", "y": "y_t2"}),
            LongitudinalWave(wave="T3", time_value=3.0, variables={"x": "x_t3", "y": "y_t3"}),
        ],
    )
    result = advanced_analysis_registry.validate(spec)
    assert result["valid"] is True
    assert result["executionAvailable"] is True
    assert result["capabilityId"] == "longitudinal_model.ri_clpm"
