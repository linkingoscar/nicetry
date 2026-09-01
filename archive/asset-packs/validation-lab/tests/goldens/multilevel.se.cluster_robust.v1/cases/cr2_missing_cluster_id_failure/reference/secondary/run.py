from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

root = Path(os.environ["RESEARCHPATH_PROJECT_ROOT"]).resolve()
case_dir = Path.cwd()
generator = root / "reference" / "generators" / "python" / "run_independent_secondary.py"
output = case_dir / "reference" / "secondary" / "normalized-output.json"
completed = subprocess.run(
    [sys.executable, str(generator), str(case_dir), str(output)],
    cwd=str(case_dir),
    capture_output=True,
    text=True,
    timeout=120,
)
if completed.returncode != 0:
    raise RuntimeError((completed.stderr or completed.stdout).strip())