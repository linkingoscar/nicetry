import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.advanced_contracts import BetweenFactor, ExperimentalDesignSpec, PlannedContrast
from app.services.advanced_analysis import advanced_analysis_registry
from app.settings import get_settings


def test_experimental_design_slice_validation() -> None:
    spec = ExperimentalDesignSpec(
        analysis_id="exp_test_01",
        name="Experimental Factorial ANOVA",
        dataset_version_id="dataset_01",
        family="experimental_design",
        design_type="factorial_anova",
        data_layout="long",
        outcome_ids=["score"],
        between_factors=[BetweenFactor(variable_id="condition")],
    )
    result = advanced_analysis_registry.validate(spec)
    assert result["valid"] is True
    assert result["executionAvailable"] is True
    assert result["capabilityId"] == "experimental_design.factorial_anova.long.single_outcome"


def test_experimental_design_ancova_validation() -> None:
    spec = ExperimentalDesignSpec(
        analysis_id="ancova_test_01",
        name="Experimental ANCOVA",
        dataset_version_id="dataset_01",
        family="experimental_design",
        design_type="ancova",
        data_layout="long",
        outcome_ids=["score"],
        between_factors=[BetweenFactor(variable_id="condition")],
        covariate_ids=["age"],
    )
    result = advanced_analysis_registry.validate(spec)
    assert result["valid"] is True
    assert result["executionAvailable"] is True
    assert result["capabilityId"] == "experimental_design.ancova.long.single_outcome"


def test_cluster_robust_glm_slice_validation_and_runner() -> None:
    spec = ExperimentalDesignSpec.model_validate(
        json.loads(
            (
                get_settings().project_root
                / "apps/api/tests/fixtures/advanced/experimental/cluster-glm.spec.json"
            ).read_text(encoding="utf-8")
        )
    )
    result = advanced_analysis_registry.validate(spec)
    assert result["executionAvailable"] is True
    assert result["capabilityId"] == "experimental_design.glm_cluster.long.single_outcome"

    settings = get_settings()
    root = settings.project_root
    data_path = root / "apps/api/tests/fixtures/advanced/experimental/factorial-balanced.csv"
    runner = root / "engine/R/run_advanced_analysis.R"
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        input_path = work / "input.json"
        output_path = work / "output.json"
        input_path.write_text(
            json.dumps(
                {
                    "spec": spec.model_dump(mode="json", by_alias=True),
                    "dataPath": str(data_path),
                    "artifactDirectory": str(work),
                }
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
        actual = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert actual is not None
    assert actual["familyResult"]["standardErrorMethod"] == "CR0"
    assert actual["familyResult"]["clusterCount"] == 40
    assert actual["estimates"]
    for row in actual["familyResult"]["coefficients"]:
        expected_margin = 2.0226909200367604 * row["standardError"]
        assert row["confidenceUpper"] - row["estimate"] == pytest.approx(
            expected_margin, abs=1e-10
        )
        assert row["estimate"] - row["confidenceLower"] == pytest.approx(
            expected_margin, abs=1e-10
        )


def test_games_howell_slice_runs_with_heteroscedastic_pairwise_inference() -> None:
    settings = get_settings()
    root = settings.project_root
    spec = ExperimentalDesignSpec.model_validate(
        json.loads(
            (
                root
                / "apps/api/tests/fixtures/advanced/experimental/games-howell-heteroscedastic.spec.json"
            ).read_text(encoding="utf-8")
        )
    )
    data_path = (
        root / "apps/api/tests/fixtures/advanced/experimental/games-howell-heteroscedastic.csv"
    )
    runner = root / "engine/R/run_advanced_analysis.R"
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        input_path = work / "input.json"
        output_path = work / "output.json"
        input_path.write_text(
            json.dumps(
                {
                    "spec": spec.model_dump(mode="json", by_alias=True),
                    "dataPath": str(data_path),
                    "artifactDirectory": str(work),
                }
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
        actual = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert actual is not None
    contrasts = actual["familyResult"]["contrasts"]
    assert len(contrasts) == 3
    assert {row["adjustment"] for row in contrasts} == {"games_howell"}
    expected = {
        "B - A": (3.5, 2.32737334062816, 16.1764705882353, 0.31514300470217),
        "C - A": (11.5, 4.29146439652791, 12.3696498054475, 0.0480315003157867),
        "C - B": (8.0, 4.65474668125631, 16.1764705882353, 0.228524657519711),
    }
    for row in contrasts:
        expected_row = expected[row["contrast"]]
        assert row["estimate"] == pytest.approx(expected_row[0], abs=1e-10)
        assert row["standardError"] == pytest.approx(expected_row[1], abs=1e-10)
        assert row["degreesOfFreedom"] == pytest.approx(expected_row[2], abs=1e-10)
        assert row["pValue"] == pytest.approx(expected_row[3], abs=1e-10)
    assert all(row["degreesOfFreedom"] > 0 for row in contrasts)
    assert all(0 <= row["pValue"] <= 1 for row in contrasts)
    assert all(
        row["confidenceLower"] <= row["estimate"] <= row["confidenceUpper"] for row in contrasts
    )


def test_planned_contrast_slice_runs_with_declared_weights_and_metadata() -> None:
    settings = get_settings()
    root = settings.project_root
    spec = ExperimentalDesignSpec(
        analysis_id="planned_contrast_runner_test",
        name="Planned contrast runner",
        dataset_version_id="dataset1",
        family="experimental_design",
        design_type="factorial_anova",
        data_layout="long",
        outcome_ids=["outcome"],
        between_factors=[BetweenFactor(variable_id="condition", coding="sum")],
        planned_contrasts=[
            PlannedContrast(
                id="a_vs_b",
                factor_variable_id="condition",
                weights={"A": 1.0, "B": -1.0, "C": 0.0},
                multiplicity_family_id="primary_experiment",
            ),
            PlannedContrast(
                id="a_vs_c",
                factor_variable_id="condition",
                weights={"A": 1.0, "B": 0.0, "C": -1.0},
                multiplicity_family_id="secondary_experiment",
            ),
            PlannedContrast(
                id="b_vs_c",
                factor_variable_id="condition",
                weights={"A": 0.0, "B": 1.0, "C": -1.0},
                multiplicity_family_id="secondary_experiment",
            ),
        ],
    )
    data_path = (
        root / "apps/api/tests/fixtures/advanced/experimental/games-howell-heteroscedastic.csv"
    )
    runner = root / "engine/R/run_advanced_analysis.R"
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        input_path = work / "input.json"
        output_path = work / "output.json"
        input_path.write_text(
            json.dumps(
                {
                    "spec": spec.model_dump(mode="json", by_alias=True),
                    "dataPath": str(data_path),
                    "artifactDirectory": str(work),
                }
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
        actual = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert actual is not None
    planned = actual["familyResult"]["plannedContrasts"]
    assert len(planned) == 3
    row = next(item for item in planned if item["plannedContrastId"] == "a_vs_b")
    assert row["plannedContrastId"] == "a_vs_b"
    assert row["multiplicityFamilyId"] == "primary_experiment"
    assert row["analysisRole"] == "planned_contrast"
    assert row["adjustment"] == "holm"
    assert row["multiplicityFamilySize"] == 1
    assert row["pValueAdjusted"] == pytest.approx(row["pValueRaw"], abs=1e-12)
    assert row["confidenceIntervalAdjustment"] == "none_individual"
    assert row["estimate"] == pytest.approx(-3.5, abs=1e-10)
    assert row["lower.CL"] <= row["estimate"] <= row["upper.CL"]
    secondary = [
        item for item in planned if item["multiplicityFamilyId"] == "secondary_experiment"
    ]
    assert len(secondary) == 2
    assert all(item["multiplicityFamilySize"] == 2 for item in secondary)
    assert all(item["pValueAdjusted"] >= item["pValueRaw"] for item in secondary)
