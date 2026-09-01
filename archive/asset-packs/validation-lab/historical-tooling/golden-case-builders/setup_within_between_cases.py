import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "multilevel.lmm.within_between.v1" / "cases"

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

rng = random.Random(20260726)

# -------------------------------------------------------------
# Case 1: lmm_group_mean_centering (normal_typical)
# -------------------------------------------------------------
c1_dir = CAP_DIR / "lmm_group_mean_centering"
rows1 = ["subject,x,y"]
for s in range(1, 11):
    sid = f"S{s:02d}"
    b_x = rng.gauss(50, 10)
    for _ in range(5):
        w_x = rng.gauss(0, 5)
        x_val = round(b_x + w_x, 4)
        y_val = round(10.0 + 0.5 * b_x + 1.5 * w_x + rng.gauss(0, 2), 4)
        rows1.append(f"{sid},{x_val},{y_val}")

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_within_between_typical",
    "sourceType": "synthetic_fixture",
    "title": "Typical Within-Between Group Mean Centering Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.lmm.within_between.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for within-between LMM",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260726"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c1_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "multilevel.lmm.within_between.v1",
    "data": {
        "clusterVar": "subject",
        "predictor": "x",
        "outcome": "y"
    },
    "parameters": {
        "centering": "group_mean"
    }
})

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: lmm_within_between_unbalanced (legal_complex)
# -------------------------------------------------------------
c2_dir = CAP_DIR / "lmm_within_between_unbalanced"
rows2 = ["subject,x,y"]
for s in range(1, 15):
    sid = f"S{s:02d}"
    b_x = rng.gauss(40, 12)
    obs_cnt = 3 if s % 2 == 0 else 8
    for _ in range(obs_cnt):
        w_x = rng.gauss(0, 4)
        x_val = round(b_x + w_x, 4)
        y_val = round(12.0 + 0.8 * b_x + 2.0 * w_x + rng.gauss(0, 3), 4)
        rows2.append(f"{sid},{x_val},{y_val}")

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_within_between_unbalanced",
    "sourceType": "synthetic_fixture",
    "title": "Unbalanced Within-Between LMM Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.lmm.within_between.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for unbalanced within-between LMM",
    "allowedUse": "testing",
    "notes": "Generated with varying observations per cluster"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c2_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "multilevel.lmm.within_between.v1",
    "data": {
        "clusterVar": "subject",
        "predictor": "x",
        "outcome": "y"
    },
    "parameters": {
        "centering": "group_mean"
    }
})

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: lmm_within_between_zero_within_var (degenerate_boundary)
# -------------------------------------------------------------
c3_dir = CAP_DIR / "lmm_within_between_zero_within_var"
rows3 = ["subject,x,y"]
for s in range(1, 10):
    sid = f"S{s:02d}"
    b_x = rng.gauss(50, 10)
    for _ in range(4):
        x_val = round(b_x, 4)  # Zero within variance
        y_val = round(10.0 + 0.5 * b_x + rng.gauss(0, 1), 4)
        rows3.append(f"{sid},{x_val},{y_val}")

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_within_between_boundary",
    "sourceType": "synthetic_fixture",
    "title": "Zero Within Variance Boundary Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.lmm.within_between.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for zero within variance",
    "allowedUse": "testing",
    "notes": "Generated with identical predictor values within clusters"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c3_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "multilevel.lmm.within_between.v1",
    "data": {
        "clusterVar": "subject",
        "predictor": "x",
        "outcome": "y"
    },
    "parameters": {
        "centering": "group_mean"
    }
})

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: lmm_within_between_missing_cluster_id (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "lmm_within_between_missing_cluster_id"
rows4 = ["subject,x,y"]
for i in range(5):
    rows4.append(f"S01,{10.0+i},{20.0+i}")  # Single cluster

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_within_between_failure",
    "sourceType": "synthetic_fixture",
    "title": "Single Cluster Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.lmm.within_between.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for single cluster within-between LMM",
    "allowedUse": "testing",
    "notes": "Generated with single cluster"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c4_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "multilevel.lmm.within_between.v1",
    "data": {
        "clusterVar": "subject",
        "predictor": "x",
        "outcome": "y"
    },
    "parameters": {
        "centering": "group_mean"
    }
})

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "MISSING_CLUSTER_VARIABLE",
        "message": "Fewer than minimum required clusters for multilevel model estimation"
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
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "MISSING_CLUSTER_VARIABLE", "message": "Fewer than minimum required clusters for multilevel model estimation"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "multilevel.lmm.within_between.v1",
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

make_manifest("lmm_group_mean_centering", "normal_typical", 50, 3)
make_manifest("lmm_within_between_unbalanced", "legal_complex", 77, 3)
make_manifest("lmm_within_between_zero_within_var", "degenerate_boundary", 36, 3)
make_manifest("lmm_within_between_missing_cluster_id", "expected_failure", 5, 3)

print("Setup script for multilevel.lmm.within_between.v1 completed!")
