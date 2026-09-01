from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.settings import get_settings

_FIXTURES = (
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
)


def _normalized_version(value: object) -> str:
    """Compare R package versions independently of CRAN's '-' vs '.' notation."""
    return str(value).replace("-", ".")


@pytest.mark.parametrize(("spec_name", "golden_name"), _FIXTURES)
def test_analytic_power_product_runner_matches_frozen_pwr_baseline(
    spec_name: str,
    golden_name: str,
) -> None:
    settings = get_settings()
    root = settings.project_root
    fixture_root = root / "apps/api/tests/fixtures/advanced"
    spec = json.loads((fixture_root / "power" / spec_name).read_text(encoding="utf-8"))
    golden = json.loads((fixture_root / "goldens" / golden_name).read_text(encoding="utf-8"))
    tolerance = float(golden["provenance"]["tolerance"]["numeric"])

    with tempfile.TemporaryDirectory(prefix="researchpath-power-golden-") as temporary:
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
                str(root / "engine/R/run_advanced_analysis.R"),
                str(input_path),
                str(output_path),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        result = json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    expected_power = golden["estimates"][0]["estimate"]
    actual_power = next(estimate for estimate in result["estimates"] if estimate["id"] == "power")[
        "estimate"
    ]
    assert math.isclose(actual_power, expected_power, rel_tol=0.0, abs_tol=tolerance)
    assert result["familyResult"]["solvedValue"] == golden["familyResult"]["solvedValue"]
    assert math.isclose(
        result["familyResult"]["achievedPower"],
        golden["familyResult"]["achievedPower"],
        rel_tol=0.0,
        abs_tol=tolerance,
    )
    assert _normalized_version(result["provenance"]["softwareVersions"]["pwr"]) == _normalized_version(
        golden["provenance"]["packages"]["pwr"]
    )
