from pathlib import Path
import os, sys

sys.path.insert(0, os.environ["RESEARCHPATH_PROJECT_ROOT"])
from tools.goldens.production_adapter import run_case

run_case(Path(__file__).resolve().parents[1])
