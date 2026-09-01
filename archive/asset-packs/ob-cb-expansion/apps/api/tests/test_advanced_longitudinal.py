import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Literal, cast

import pytest

from app.advanced_contracts import LongitudinalModelSpec, LongitudinalWave
from app.settings import get_settings

LongitudinalModelType = Literal[
    "growth_curve",
    "cross_lagged_panel",
    "ri_clpm",
    "latent_growth",
    "longitudinal_invariance",
]


def _growth_spec(
    *,
    model_type: LongitudinalModelType = "growth_curve",
    missing: Literal["fiml", "complete_cases", "available_rows_ml"] = "complete_cases",
) -> LongitudinalModelSpec:
    variables = {"x": "x1", "y": "y1"} if model_type == "ri_clpm" else {"outcome": "y1"}
    waves = [
        LongitudinalWave(wave="T1", time_value=0, variables=variables),
        LongitudinalWave(
            wave="T2",
            time_value=1,
            variables=({"x": "x2", "y": "y2"} if model_type == "ri_clpm" else {"outcome": "y2"}),
        ),
        LongitudinalWave(
            wave="T3",
            time_value=2,
            variables=({"x": "x3", "y": "y3"} if model_type == "ri_clpm" else {"outcome": "y3"}),
        ),
    ]
    return LongitudinalModelSpec(
        analysis_id="longitudinal-test",
        name="longitudinal-test",
        dataset_version_id="dataset1",
        family="longitudinal_model",
        model_type=model_type,
        subject_id="subject",
        group_variable_id="group" if model_type == "longitudinal_invariance" else None,
        waves=waves,
        estimator="MLR",
        missing=missing,
    )


def test_observed_growth_does_not_claim_fiml_when_runner_uses_complete_cases() -> None:
    with pytest.raises(ValueError, match="LONGITUDINAL_FIML_NOT_SUPPORTED_FOR_OBSERVED_GROWTH"):
        _growth_spec(missing="fiml")


def test_observed_growth_explicitly_accepts_available_rows_ml() -> None:
    spec = _growth_spec(missing="available_rows_ml")
    assert spec.missing == "available_rows_ml"


def test_clpm_rejects_available_rows_ml() -> None:
    with pytest.raises(ValueError, match="LONGITUDINAL_AVAILABLE_ROWS_ONLY_FOR_OBSERVED_GROWTH"):
        _growth_spec(model_type="cross_lagged_panel", missing="available_rows_ml")


def test_ri_clpm_fiml_reports_model_sample_size_and_missing_patterns() -> None:
    settings = get_settings()
    root = settings.project_root
    spec = LongitudinalModelSpec.model_validate(
        json.loads(
            (
                root / "apps/api/tests/fixtures/advanced/longitudinal/ri-clpm-three-wave.spec.json"
            ).read_text(encoding="utf-8")
        )
    )
    source_data = root / "apps/api/tests/fixtures/advanced/longitudinal/clpm-three-wave.csv"
    lines = source_data.read_text(encoding="utf-8").splitlines()
    lines[1] = lines[1].replace(",6.753341621104532,", ",,")
    runner = root / "engine/R/run_advanced_analysis.R"
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        data_path = work / "ri-clpm-missing.csv"
        data_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
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
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    assert result["sampleFlow"]["missingMethod"] == "fiml"
    assert result["sampleFlow"]["original"] == 100
    assert result["sampleFlow"]["included"] == 100
    assert result["familyResult"]["missingPatterns"]
    assert result["familyResult"]["waveSampleFlow"][1]["observed"] == 99


@pytest.mark.parametrize("model_type", ["ri_clpm", "latent_growth", "longitudinal_invariance"])
def test_longitudinal_model_contracts_have_explicit_three_wave_inputs(model_type: str) -> None:
    spec = _growth_spec(model_type=cast(LongitudinalModelType, model_type))

    assert spec.model_type == model_type
    assert len(spec.waves) == 3
