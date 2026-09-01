"""Launch the independent closed-form R reference for the current case."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml


def main() -> None:
    root = Path(os.environ["RESEARCHPATH_PROJECT_ROOT"]).resolve()
    case_dir = Path.cwd()
    rscript = root / ".runtime" / "R" / "bin" / "Rscript.exe"
    manifest = yaml.safe_load((case_dir / "manifest.yaml").read_text(encoding="utf-8"))
    capability = manifest["identity"]["capabilityId"]
    remaining = {
        "imputation.mice.chain_diagnostics.v1", "longitudinal.esm.diary_ar1.v1",
        "longitudinal.ri_clpm.four_wave.v1", "multilevel.mediation.two_level.v1",
        "multilevel.se.cluster_robust.v1", "robustness.specification_curve.matrix.v1",
        "experiment.between.factorial.gaussian.v1", "experiment.emmeans.planned_contrast.v1",
        "experiment.repeated.one_within.v1", "multilevel.lmm.two_level.gaussian.random_slope.v1",
        "multilevel.icc.two_level.v1", "multilevel.lmm.within_between.v1",
    }
    foundation = {
        "imputation.pooling.linear.rubin.v1", "power.regression.f2.analytic.v1",
        "equivalence.tost.two_sample.v1", "experiment.randomization.inference.v1",
        "experiment.posthoc.games_howell.v1",
    }
    if capability in foundation:
        script_name = "run_foundation_reference.R"
    elif capability in remaining:
        script_name = "run_remaining_reference.R"
    elif capability.startswith("measurement."):
        script_name = "run_measurement_reference.R"
    else:
        script_name = "run_statistical_reference.R"
    script = root / "reference" / "generators" / "r" / script_name
    output = case_dir / "reference" / "primary" / "normalized-output.json"
    environment = os.environ.copy()
    environment["R_LIBS_USER"] = str(root / ".runtime" / "R-library")
    completed = subprocess.run(
        [str(rscript), "--vanilla", str(script), str(case_dir), str(output)],
        cwd=str(case_dir),
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip())


if __name__ == "__main__":
    main()
