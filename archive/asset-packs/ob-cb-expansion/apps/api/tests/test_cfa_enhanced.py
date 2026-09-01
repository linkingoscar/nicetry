from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from app.settings import get_settings


def test_cfa_enhanced_outputs_and_validity_bundle() -> None:
    settings = get_settings()
    root = settings.project_root
    spec_path = root / "apps/api/tests/fixtures/advanced/questionnaire-cfa-clpm.spec.json"
    source_data_path = root / "apps/api/tests/fixtures/advanced/longitudinal/clpm-three-wave.csv"
    runner = root / "engine/R/run_advanced_analysis.R"

    spec = json.loads(spec_path.read_text(encoding="utf-8"))

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

    cfa = result["familyResult"]["cfa"]
    assert cfa["available"] is True
    assert cfa["converged"] is True

    # Check unstandardized solution
    assert "unstandardizedLoadings" in cfa
    assert len(cfa["unstandardizedLoadings"]) > 0
    first_unstd = cfa["unstandardizedLoadings"][0]
    assert "estimate" in first_unstd
    assert "se" in first_unstd
    assert "pValue" in first_unstd

    # Check R-squared
    assert "rSquared" in cfa
    assert len(cfa["rSquared"]) > 0

    # Check residual correlation
    assert "residualCorrelation" in cfa

    # Check modification indices
    assert "modificationIndices" in cfa

    # Check validity bundle (CR, AVE, Fornell-Larcker, HTMT)
    assert "validity" in cfa
    validity = cfa["validity"]
    assert validity["available"] is True
    assert "compositeReliabilityAndAve" in validity
    cr_ave = validity["compositeReliabilityAndAve"]
    assert len(cr_ave) >= 2
    assert "compositeReliability" in cr_ave[0]
    assert "averageVarianceExtracted" in cr_ave[0]

    assert "fornellLarcker" in validity
    fl = validity["fornellLarcker"]
    assert fl["available"] is True
