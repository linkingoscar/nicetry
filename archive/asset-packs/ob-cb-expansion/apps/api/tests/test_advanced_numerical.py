import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.settings import get_settings


@pytest.mark.parametrize(
    ("spec_name", "golden_name"),
    [
        ("regression-f2-015.json", "regression-f2-015.expected.json"),
        ("regression-f2-015-u8.json", "regression-f2-015-u8.expected.json"),
        ("regression-f2-015-power-n100.json", "regression-f2-015-power-n100.expected.json"),
        (
            "regression-r2-change-sensitivity-n100.json",
            "regression-r2-change-sensitivity-n100.expected.json",
        ),
        ("anova-f-025.json", "anova-f-025.expected.json"),
        ("anova-f-025-k2.json", "anova-f-025-k2.expected.json"),
        ("anova-f-025-k4.json", "anova-f-025-k4.expected.json"),
        ("anova-f-025-power-n159.json", "anova-f-025-power-n159.expected.json"),
    ],
)
def test_power_analysis_numerical_tolerance(spec_name: str, golden_name: str):
    settings = get_settings()
    project_root = settings.project_root
    fixtures_dir = project_root / "apps" / "api" / "tests" / "fixtures" / "advanced"
    engine_path = project_root / "engine" / "R" / "run_advanced_analysis.R"

    spec_path = fixtures_dir / "power" / spec_name
    golden_path = fixtures_dir / "goldens" / golden_name

    assert spec_path.is_file(), "Fixture spec not found"
    assert golden_path.is_file(), "Golden JSON not found"

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    provenance = golden["provenance"]
    tolerance = float(provenance["tolerance"]["numeric"])
    assert provenance["reference"].startswith("R pwr::")
    assert provenance["comparisonFields"] == [
        "estimates.power.estimate",
        "familyResult.solvedValue",
        "familyResult.achievedPower",
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_path = tmp_path / "input.json"
        output_path = tmp_path / "output.json"

        # Prepare payload for R
        payload = {
            "spec": spec,
            "dataPath": None,
            "artifactDirectory": str(tmp_path),
        }
        input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        env = os.environ.copy()
        env["R_LIBS_USER"] = str(settings.r_library_path)
        env["LC_ALL"] = "English_United States.utf8"

        # Run R script
        result = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(engine_path),
                str(input_path),
                str(output_path),
            ],
            capture_output=True,
            text=True,
            cwd=str(settings.project_root),
            env=env,
        )

        assert result.returncode == 0, f"R script failed: {result.stdout}\n{result.stderr}"
        assert output_path.is_file(), "R script did not produce output.json"

        actual_output = json.loads(output_path.read_text(encoding="utf-8"))

        # Compare estimates
        actual_estimates = {est["id"]: est for est in actual_output.get("estimates", [])}
        expected_estimates = {est["id"]: est for est in golden.get("estimates", [])}

        assert len(actual_estimates) == len(expected_estimates), "Estimates count mismatch"

        for est_id, expected in expected_estimates.items():
            assert est_id in actual_estimates
            actual = actual_estimates[est_id]

            for key in [
                "estimate",
                "standardError",
                "statistic",
                "pValue",
                "confidenceLower",
                "confidenceUpper",
            ]:
                expected_val = expected.get(key)
                actual_val = actual.get(key)

                if expected_val is None:
                    assert actual_val is None
                else:
                    assert actual_val is not None
                    assert math.isclose(
                        actual_val, expected_val, rel_tol=tolerance, abs_tol=tolerance
                    ), (
                        f"Numerical drift in {est_id}.{key}: expected {expected_val}, got {actual_val}"
                    )

        # Compare familyResult
        actual_family = actual_output.get("familyResult", {})
        expected_family = golden.get("familyResult", {})

        for key in ["solvedValue", "achievedPower", "monteCarloStandardError"]:
            if key in expected_family:
                if key == "solvedValue" and isinstance(expected_family[key], int):
                    assert actual_family.get(key) == expected_family[key]
                else:
                    assert math.isclose(
                        actual_family.get(key, 0),
                        expected_family[key],
                        rel_tol=tolerance,
                        abs_tol=tolerance,
                    )
        assert actual_family["monteCarloStandardError"] is None

        expected_parameters = expected_family.get("parameters", {})
        actual_parameters = actual_family.get("parameters", {})
        for key, expected_value in expected_parameters.items():
            assert actual_parameters.get(key) == expected_value
