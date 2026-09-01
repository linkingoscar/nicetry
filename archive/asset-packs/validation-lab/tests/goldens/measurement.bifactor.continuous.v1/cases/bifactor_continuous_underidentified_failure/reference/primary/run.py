from __future__ import annotations

import os
import subprocess
from pathlib import Path

root = Path(os.environ["RESEARCHPATH_PROJECT_ROOT"]).resolve()
case_dir = Path.cwd()
rscript = root / ".runtime" / "R" / "bin" / "Rscript.exe"
generator = root / "reference" / "generators" / "r" / "run_failure_reference.R"
output = case_dir / "reference" / "primary" / "normalized-output.json"
environment = os.environ.copy()
environment["R_LIBS_USER"] = str(root / ".runtime" / "R-library")
completed = subprocess.run(
    [str(rscript), "--vanilla", str(generator), str(case_dir), str(output)],
    cwd=str(case_dir),
    env=environment,
    capture_output=True,
    text=True,
    timeout=120,
)
if completed.returncode != 0:
    raise RuntimeError((completed.stderr or completed.stdout).strip())