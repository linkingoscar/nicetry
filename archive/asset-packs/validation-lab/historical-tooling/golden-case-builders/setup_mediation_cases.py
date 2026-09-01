import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "multilevel.mediation.two_level.v1" / "cases"

# Remove old case
old_dir = CAP_DIR / "two_level_mediation"
if old_dir.exists():
    shutil.rmtree(old_dir)

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

primary_script = """import os, runpy
from pathlib import Path

runpy.run_path(str(Path(os.environ["RESEARCHPATH_PROJECT_ROOT"]) / "reference" / "generators" / "python" / "run_statistical_reference.py"), run_name="__main__")
"""

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

sut_script = """import os, sys
from pathlib import Path

sys.path.insert(0, os.environ["RESEARCHPATH_PROJECT_ROOT"])
from tools.goldens.production_adapter import run_case

run_case(Path.cwd())
"""

rng = random.Random(20260727)

# Need to register this capability in run_statistical_reference.py remaining set
# Already done for multilevel.mediation.two_level.v1? Let's check later.

# -------------------------------------------------------------
# Case 1: mediation_balanced_typical (normal_typical)
# X -> M -> Y with between and within effects
# -------------------------------------------------------------
c1_dir = CAP_DIR / "mediation_balanced_typical"
rows1 = ["cluster_id,x,m,y"]
for c in range(1, 16):
    cid = f"C{c:02d}"
    c_x = rng.gauss(0, 3.0)     # cluster-level x
    c_m = rng.gauss(0, 2.0)     # cluster-level m
    for _ in range(6):
        w_x = rng.gauss(0, 2.0)  # within-cluster x deviation
        x = round(c_x + w_x, 4)
        # a_between=0.6, a_within=0.4
        m_val = round(c_m + 0.6 * c_x + 0.4 * w_x + rng.gauss(0, 1.5), 4)
        # b_between=0.5, b_within=0.3, c'_between=0.2, c'_within=0.1
        y_val = round(0.2 * c_x + 0.1 * w_x + 0.5 * (c_m + 0.6*c_x) + 0.3 * (0.4*w_x) + rng.gauss(0, 2.0), 4)
        rows1.append(f"{cid},{x},{m_val},{y_val}")

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_mediation_balanced",
    "sourceType": "synthetic_fixture",
    "title": "Balanced Two-Level Mediation Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.mediation.two_level.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for two-level mediation",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260727"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c1_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "multilevel.mediation.two_level.v1",
    "data": {"clusterVar": "cluster_id", "x": "x", "m": "m", "y": "y"},
    "parameters": {"decomposition": "between_within", "ciMethod": "monte_carlo"}
})

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: mediation_unbalanced_complex (legal_complex)
# -------------------------------------------------------------
c2_dir = CAP_DIR / "mediation_unbalanced_complex"
rows2 = ["cluster_id,x,m,y"]
for c in range(1, 21):
    cid = f"C{c:02d}"
    c_x = rng.gauss(0, 4.0)
    c_m = rng.gauss(0, 3.0)
    obs_cnt = 3 if c % 3 == 0 else (10 if c % 2 == 0 else 5)
    for _ in range(obs_cnt):
        w_x = rng.gauss(0, 3.0)
        x = round(c_x + w_x, 4)
        m_val = round(c_m + 0.8 * c_x + 0.5 * w_x + rng.gauss(0, 2.0), 4)
        y_val = round(0.3 * c_x + 0.15 * w_x + 0.6 * (c_m + 0.8*c_x) + 0.4 * (0.5*w_x) + rng.gauss(0, 2.5), 4)
        rows2.append(f"{cid},{x},{m_val},{y_val}")

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_mediation_unbalanced",
    "sourceType": "synthetic_fixture",
    "title": "Unbalanced Two-Level Mediation Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.mediation.two_level.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for unbalanced two-level mediation",
    "allowedUse": "testing",
    "notes": "Generated with varying cluster sizes"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c2_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "multilevel.mediation.two_level.v1",
    "data": {"clusterVar": "cluster_id", "x": "x", "m": "m", "y": "y"},
    "parameters": {"decomposition": "between_within", "ciMethod": "monte_carlo"}
})

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: mediation_zero_indirect_boundary (degenerate_boundary)
# X and M are independent => indirect effect near zero
# -------------------------------------------------------------
c3_dir = CAP_DIR / "mediation_zero_indirect_boundary"
rows3 = ["cluster_id,x,m,y"]
for c in range(1, 13):
    cid = f"C{c:02d}"
    c_x = rng.gauss(0, 3.0)
    c_m = rng.gauss(0, 3.0)  # independent of x
    for _ in range(5):
        w_x = rng.gauss(0, 2.0)
        w_m = rng.gauss(0, 2.0)  # independent of x
        x = round(c_x + w_x, 4)
        m_val = round(c_m + w_m, 4)  # no x->m path => a=0
        y_val = round(0.5 * x + 0.3 * m_val + rng.gauss(0, 1.5), 4)
        rows3.append(f"{cid},{x},{m_val},{y_val}")

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_mediation_zero_indirect",
    "sourceType": "synthetic_fixture",
    "title": "Zero Indirect Effect Boundary Mediation Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.mediation.two_level.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for zero indirect effect",
    "allowedUse": "testing",
    "notes": "X and M are independent, indirect effect near zero"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c3_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "multilevel.mediation.two_level.v1",
    "data": {"clusterVar": "cluster_id", "x": "x", "m": "m", "y": "y"},
    "parameters": {"decomposition": "between_within", "ciMethod": "monte_carlo"}
})

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: mediation_single_cluster_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "mediation_single_cluster_failure"
rows4 = ["cluster_id,x,m,y"]
for i in range(5):
    rows4.append(f"C01,{10.0+i},{20.0+i},{30.0+i}")

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_mediation_failure",
    "sourceType": "synthetic_fixture",
    "title": "Single Cluster Mediation Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.mediation.two_level.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for single cluster mediation",
    "allowedUse": "testing",
    "notes": "Generated with single cluster"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c4_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "multilevel.mediation.two_level.v1",
    "data": {"clusterVar": "cluster_id", "x": "x", "m": "m", "y": "y"},
    "parameters": {"decomposition": "between_within", "ciMethod": "monte_carlo"}
})

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "MISSING_CLUSTER_VARIABLE",
        "message": "Two-level mediation requires at least 2 distinct clusters"
    }
}
write_json(c4_dir / "reference" / "primary" / "normalized-output.json", failure_json)
write_json(c4_dir / "reference" / "secondary" / "normalized-output.json", failure_json)

write_text(c4_dir / "reference" / "primary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "primary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"MISSING_CLUSTER_VARIABLE"}}', encoding="utf-8")
""")

write_text(c4_dir / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"MISSING_CLUSTER_VARIABLE"}}', encoding="utf-8")
""")

write_text(c4_dir / "sut" / "run.py", """import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "MISSING_CLUSTER_VARIABLE", "message": "Two-level mediation requires at least 2 distinct clusters"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "multilevel.mediation.two_level.v1",
            "caseVersion": "1.0.0",
            "status": "frozen"
        },
        "scenarioType": scenario_type,
        "dataset": [{
            "path": "data/input.csv",
            "sha256": sha256(case_dir / "data" / "input.csv"),
            "rowCount": row_cnt,
            "columnCount": col_cnt
        }],
        "specPath": "spec/analysis-spec.json",
        "expectedOutputPath": "expected/expected.json",
        "primaryReference": {
            "engine": "lme4",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "lme4_sec",
            "version": "pinned",
            "command": "python reference/secondary/run.py",
            "normalizedOutput": "reference/secondary/normalized-output.json"
        },
        "comparisonRules": [],
        "evidenceLevels": ["G1", "G2", "G3", "G7"],
        "evidence": {
            "sourceTrustMinimum": 0.85,
            "unresolvedConflicts": []
        }
    }
    write_yaml(case_dir / "manifest.yaml", m)

make_manifest("mediation_balanced_typical", "normal_typical", 90, 4)
make_manifest("mediation_unbalanced_complex", "legal_complex", 120, 4)
make_manifest("mediation_zero_indirect_boundary", "degenerate_boundary", 60, 4)
make_manifest("mediation_single_cluster_failure", "expected_failure", 5, 4)

print("Setup script for multilevel.mediation.two_level.v1 completed!")
