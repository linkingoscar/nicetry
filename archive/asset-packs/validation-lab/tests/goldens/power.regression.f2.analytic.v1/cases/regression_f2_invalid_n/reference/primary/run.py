import os, runpy
from pathlib import Path

runpy.run_path(
    str(Path(os.environ["RESEARCHPATH_PROJECT_ROOT"]) / "reference" / "generators" / "python" / "run_statistical_reference.py"),
    run_name="__main__",
)
