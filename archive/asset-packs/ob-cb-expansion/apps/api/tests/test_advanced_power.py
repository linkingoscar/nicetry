import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.advanced_contracts import EffectSize, MonteCarloParameters, PowerAnalysisSpec
from app.settings import get_settings


def test_power_spec_rejects_unsupported_design_families():
    with pytest.raises(ValueError, match="POWER_DESIGN_NOT_SUPPORTED"):
        PowerAnalysisSpec(
            analysis_id="test",
            name="test",
            family="power_analysis",
            design_family="mediation",
            solve_for="sample_size",
            effect_size=EffectSize(metric="cohens_f", value=0.25),
        )


def test_power_spec_rejects_one_sided_for_f_tests():
    with pytest.raises(ValueError, match="不支持单侧检验"):
        PowerAnalysisSpec(
            analysis_id="test",
            name="test",
            family="power_analysis",
            design_family="regression",
            alternative="one_sided",
            solve_for="sample_size",
            effect_size=EffectSize(metric="cohens_f2", value=0.15),
            predictors=3,
        )


def test_power_spec_validates_regression():
    spec = PowerAnalysisSpec(
        analysis_id="test",
        name="test",
        family="power_analysis",
        design_family="regression",
        solve_for="sample_size",
        effect_size=EffectSize(metric="cohens_f2", value=0.15),
        predictors=3,
        target_power=0.8,
    )
    assert spec.design_family == "regression"
    assert spec.alternative == "two_sided"


def test_power_spec_validates_factorial_anova():
    spec = PowerAnalysisSpec(
        analysis_id="test",
        name="test",
        family="power_analysis",
        design_family="factorial_anova",
        solve_for="sample_size",
        effect_size=EffectSize(metric="cohens_f", value=0.25),
        groups=3,
        target_power=0.8,
    )
    assert spec.groups == 3


def test_power_spec_validates_two_sample_t_test():
    spec = PowerAnalysisSpec(
        analysis_id="t-test",
        name="t-test",
        family="power_analysis",
        design_family="t_test",
        solve_for="sample_size",
        effect_size=EffectSize(metric="cohens_d", value=0.5),
        groups=2,
        target_power=0.8,
    )
    assert spec.design_family == "t_test"

    with pytest.raises(ValueError, match="POWER_T_TEST_DIRECTION_REQUIRED"):
        PowerAnalysisSpec(
            analysis_id="t-test-one-sided",
            name="t-test-one-sided",
            family="power_analysis",
            design_family="t_test",
            alternative="one_sided",
            solve_for="sample_size",
            effect_size=EffectSize(metric="cohens_d", value=0.5),
            groups=2,
        )

    with pytest.raises(ValueError, match="POWER_SAMPLE_SIZE_NOT_DIVISIBLE_BY_GROUPS"):
        PowerAnalysisSpec(
            analysis_id="t-test-unequal-total-n",
            name="t-test unequal total n",
            family="power_analysis",
            design_family="t_test",
            solve_for="power",
            sample_size=101,
            effect_size=EffectSize(metric="cohens_d", value=0.5),
            groups=2,
        )


def test_power_spec_rejects_single_group_anova():
    with pytest.raises(ValueError, match="POWER_GROUP_COUNT_INVALID"):
        PowerAnalysisSpec(
            analysis_id="test",
            name="test",
            family="power_analysis",
            design_family="factorial_anova",
            solve_for="sample_size",
            effect_size=EffectSize(metric="cohens_f", value=0.25),
            groups=1,
        )


def test_power_spec_rejects_mismatched_effect_metric():
    with pytest.raises(ValueError, match="POWER_EFFECT_METRIC_NOT_SUPPORTED"):
        PowerAnalysisSpec(
            analysis_id="test",
            name="test",
            family="power_analysis",
            design_family="regression",
            solve_for="sample_size",
            effect_size=EffectSize(metric="cohens_f", value=0.25),
            predictors=3,
        )


def test_power_spec_rejects_non_divisible_anova_sample_size():
    with pytest.raises(ValueError, match="POWER_SAMPLE_SIZE_NOT_DIVISIBLE_BY_GROUPS"):
        PowerAnalysisSpec(
            analysis_id="test",
            name="test",
            family="power_analysis",
            design_family="factorial_anova",
            solve_for="power",
            sample_size=100,
            effect_size=EffectSize(metric="cohens_f", value=0.25),
            groups=3,
        )


def test_power_spec_rejects_unsupported_allocation_ratio():
    with pytest.raises(ValueError, match="POWER_ALLOCATION_NOT_SUPPORTED"):
        PowerAnalysisSpec(
            analysis_id="test",
            name="test",
            family="power_analysis",
            design_family="regression",
            solve_for="sample_size",
            effect_size=EffectSize(metric="cohens_f2", value=0.15),
            predictors=3,
            allocation_ratio=1.5,
        )


def test_power_sensitivity_requires_and_accepts_requested_effect_metric():
    with pytest.raises(ValueError, match="POWER_EFFECT_METRIC_REQUIRED"):
        PowerAnalysisSpec(
            analysis_id="test",
            name="test",
            family="power_analysis",
            design_family="regression",
            solve_for="effect_size",
            sample_size=100,
            predictors=3,
        )

    spec = PowerAnalysisSpec(
        analysis_id="test",
        name="test",
        family="power_analysis",
        design_family="regression",
        solve_for="effect_size",
        sample_size=100,
        predictors=3,
        effect_size_metric="r_squared_change",
    )
    assert spec.effect_size_metric == "r_squared_change"


def test_power_t_test_runner_returns_noncentral_t_backcheck() -> None:
    settings = get_settings()
    root = settings.project_root
    spec = PowerAnalysisSpec(
        analysis_id="t-test-runner",
        name="t-test runner",
        family="power_analysis",
        design_family="t_test",
        solve_for="sample_size",
        effect_size=EffectSize(metric="cohens_d", value=0.5),
        groups=2,
        target_power=0.8,
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
                    "dataPath": None,
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
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    assert result["familyResult"]["achievedPower"] >= 0.8
    assert result["provenance"]["degreesOfFreedomMethod"] == "noncentral t"
    assert result["familyResult"]["parameters"]["effectSizeMetric"] == "cohens_d"


def test_power_sensitivity_rejects_an_effect_size_value():
    with pytest.raises(ValueError, match="POWER_EFFECT_SIZE_VALUE_NOT_APPLICABLE"):
        PowerAnalysisSpec(
            analysis_id="test",
            name="test",
            family="power_analysis",
            design_family="regression",
            solve_for="effect_size",
            sample_size=100,
            predictors=3,
            effect_size_metric="cohens_f2",
            effect_size=EffectSize(metric="cohens_f2", value=0.15),
        )


def test_power_spec_rejects_invalid_r_squared_change():
    with pytest.raises(ValueError, match="POWER_R_SQUARED_CHANGE_INVALID"):
        PowerAnalysisSpec(
            analysis_id="test",
            name="test",
            family="power_analysis",
            design_family="regression",
            solve_for="sample_size",
            effect_size=EffectSize(metric="r_squared_change", value=1.0),
            predictors=3,
        )


def test_power_spec_rejects_monte_carlo_until_a_real_dgp_is_reachable():
    with pytest.raises(ValueError, match="POWER_MONTE_CARLO_NOT_SUPPORTED"):
        PowerAnalysisSpec(
            analysis_id="test",
            name="test",
            family="power_analysis",
            design_family="mediation",
            method="monte_carlo",
            solve_for="sample_size",
            effect_size=EffectSize(metric="indirect_effect", value=0.15),
            monte_carlo_parameters=MonteCarloParameters(
                data_generation={"aPath": 0.2, "bPath": 0.3},
                estimand_target="indirect",
            ),
        )


def test_power_spec_accepts_explicit_regression_monte_carlo_dgp() -> None:
    spec = PowerAnalysisSpec(
        analysis_id="mc-regression",
        name="mc-regression",
        family="power_analysis",
        design_family="regression",
        method="monte_carlo",
        solve_for="power",
        sample_size=80,
        effect_size=EffectSize(metric="cohens_f2", value=0.15),
        predictors=3,
        simulations=1000,
        monte_carlo_parameters=MonteCarloParameters(
            data_generation={"errorSd": 1.0, "predictorCorrelation": 0.0},
            estimand_target="overall",
        ),
    )
    assert spec.method == "monte_carlo"


def test_power_monte_carlo_runner_reports_mcse_and_failures() -> None:
    settings = get_settings()
    root = settings.project_root
    fixture = root / "apps/api/tests/fixtures/advanced/power/regression-monte-carlo.json"
    runner = root / "engine/R/run_advanced_analysis.R"
    spec = json.loads(fixture.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        input_path = work / "input.json"
        output_path = work / "output.json"
        input_path.write_text(
            json.dumps({"spec": spec, "dataPath": None, "artifactDirectory": str(work)}),
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
            timeout=120,
        )
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    family_result = result["familyResult"]
    assert family_result["method"] == "monte_carlo"
    assert family_result["simulationCount"] == 1000
    assert family_result["validSimulations"] == 1000
    assert family_result["failureCount"] == 0
    assert family_result["monteCarloStandardError"] >= 0


def test_power_anova_monte_carlo_runner_reports_omnibus_power() -> None:
    settings = get_settings()
    root = settings.project_root
    fixture = root / "apps/api/tests/fixtures/advanced/power/anova-monte-carlo.json"
    runner = root / "engine/R/run_advanced_analysis.R"
    spec = json.loads(fixture.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        input_path = work / "input.json"
        output_path = work / "output.json"
        input_path.write_text(
            json.dumps({"spec": spec, "dataPath": None, "artifactDirectory": str(work)}),
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
            timeout=120,
        )
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    family_result = result["familyResult"]
    assert 0 <= family_result["achievedPower"] <= 1
    assert family_result["validSimulations"] == 1000
