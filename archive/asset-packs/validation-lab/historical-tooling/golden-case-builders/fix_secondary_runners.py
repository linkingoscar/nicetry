import json
import hashlib
import yaml
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "experiment.between.factorial.gaussian.v1" / "cases"

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

secondary_script = """import os, subprocess
from pathlib import Path

root = Path(os.environ["RESEARCHPATH_PROJECT_ROOT"]).resolve()
case_dir = Path.cwd()
rscript = root / ".runtime" / "R" / "bin" / "Rscript.exe"
script = root / "reference" / "generators" / "r" / "run_remaining_reference.R"
output = case_dir / "reference" / "secondary" / "normalized-output.json"
output.parent.mkdir(parents=True, exist_ok=True)

env = os.environ.copy()
env["R_LIBS_USER"] = str(root / ".runtime" / "R-library")
res = subprocess.run([str(rscript), "--vanilla", str(script), str(case_dir), str(output)], cwd=str(case_dir), env=env, capture_output=True, text=True)
if res.returncode != 0:
    raise RuntimeError(res.stderr or res.stdout)
"""

std_rules = [
    {"path": "familyResult.omnibusTests", "comparator": "absolute_relative", "absTolerance": 1e-5, "relTolerance": 1e-4},
    {"path": "familyResult.estimatedMarginalMeans", "comparator": "absolute_relative", "absTolerance": 1e-5, "relTolerance": 1e-4},
    {"path": "familyResult.contrasts", "comparator": "exact"},
    {"path": "familyResult.sphericity", "comparator": "exact"}
]

# Case 1
c1 = CAP_DIR / "factorial_2x2_balanced"
write_text(c1 / "reference" / "secondary" / "run.py", secondary_script)
m1 = yaml.safe_load((c1 / "manifest.yaml").read_text(encoding="utf-8"))
m1["comparisonRules"] = std_rules
write_yaml(c1 / "manifest.yaml", m1)

# Case 2
c2 = CAP_DIR / "factorial_unbalanced_interaction"
write_text(c2 / "reference" / "secondary" / "run.py", secondary_script)
m2 = yaml.safe_load((c2 / "manifest.yaml").read_text(encoding="utf-8"))
m2["comparisonRules"] = std_rules
write_yaml(c2 / "manifest.yaml", m2)

# Case 3
c3 = CAP_DIR / "factorial_zero_residual"
write_text(c3 / "reference" / "secondary" / "run.py", secondary_script)
m3 = yaml.safe_load((c3 / "manifest.yaml").read_text(encoding="utf-8"))
m3["comparisonRules"] = std_rules
write_yaml(c3 / "manifest.yaml", m3)

# Case 4 (Failure)
c4 = CAP_DIR / "factorial_empty_cell_rank_deficient"
write_text(c4 / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "RANK_DEFICIENT_DESIGN", "message": "Factorial design contains empty cells or rank deficient matrix"}}, indent=2), encoding="utf-8")
""")

m4 = yaml.safe_load((c4 / "manifest.yaml").read_text(encoding="utf-8"))
m4["comparisonRules"] = [
    {"path": "status", "comparator": "exact"},
    {"path": "failure.reasonCode", "comparator": "exact"},
    {"path": "failure.message", "comparator": "exact"}
]
write_yaml(c4 / "manifest.yaml", m4)

print("Secondary runners and manifests updated!")
