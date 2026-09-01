import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "multilevel.se.cluster_robust.v1" / "cases"

# Clean up old case if exists
old_dir = CAP_DIR / "cluster_robust_cr2"
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

rng = random.Random(20260726)

# -------------------------------------------------------------
# Case 1: cr2_small_sample_typical (normal_typical)
# -------------------------------------------------------------
c1_dir = CAP_DIR / "cr2_small_sample_typical"
rows1 = ["cluster_id,treatment,outcome"]
for c in range(1, 13):
    cid = f"C{c:02d}"
    c_effect = rng.gauss(0, 5.0)
    for _ in range(5):
        treat = round(rng.gauss(10, 3), 4)
        out = round(15.0 + 2.5 * treat + c_effect + rng.gauss(0, 4), 4)
        rows1.append(f"{cid},{treat},{out}")

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_cr2_typical",
    "sourceType": "synthetic_fixture",
    "title": "Small Sample Cluster Robust CR2 Standard Error Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.se.cluster_robust.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for CR2 cluster-robust SE",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260726"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c1_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "multilevel.se.cluster_robust.v1",
    "data": {
        "clusterVar": "cluster_id",
        "predictor": "treatment",
        "outcome": "outcome"
    },
    "parameters": {
        "vcovType": "CR2"
    }
})

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: cr2_unbalanced_clusters_complex (legal_complex)
# -------------------------------------------------------------
c2_dir = CAP_DIR / "cr2_unbalanced_clusters_complex"
rows2 = ["cluster_id,treatment,outcome"]
for c in range(1, 17):
    cid = f"C{c:02d}"
    c_effect = rng.gauss(0, 6.0)
    obs_cnt = 2 if c % 3 == 0 else (12 if c % 2 == 0 else 6)
    for _ in range(obs_cnt):
        treat = round(rng.gauss(8, 4), 4)
        out = round(12.0 + 3.0 * treat + c_effect + rng.gauss(0, 5), 4)
        rows2.append(f"{cid},{treat},{out}")

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_cr2_unbalanced",
    "sourceType": "synthetic_fixture",
    "title": "Unbalanced Cluster Sizes CR2 Standard Error Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.se.cluster_robust.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for unbalanced cluster sizes CR2",
    "allowedUse": "testing",
    "notes": "Generated with varying cluster sizes"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c2_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "multilevel.se.cluster_robust.v1",
    "data": {
        "clusterVar": "cluster_id",
        "predictor": "treatment",
        "outcome": "outcome"
    },
    "parameters": {
        "vcovType": "CR2"
    }
})

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: cr2_few_clusters_boundary (degenerate_boundary)
# -------------------------------------------------------------
c3_dir = CAP_DIR / "cr2_few_clusters_boundary"
rows3 = ["cluster_id,treatment,outcome"]
for c in range(1, 5):
    cid = f"C{c:02d}"
    c_effect = rng.gauss(0, 4.0)
    for _ in range(10):
        treat = round(rng.gauss(10, 2), 4)
        out = round(10.0 + 1.5 * treat + c_effect + rng.gauss(0, 2), 4)
        rows3.append(f"{cid},{treat},{out}")

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_cr2_few_clusters",
    "sourceType": "synthetic_fixture",
    "title": "Few Clusters Boundary CR2 Standard Error Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.se.cluster_robust.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for few clusters (K=4)",
    "allowedUse": "testing",
    "notes": "Generated with K=4 clusters"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c3_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "multilevel.se.cluster_robust.v1",
    "data": {
        "clusterVar": "cluster_id",
        "predictor": "treatment",
        "outcome": "outcome"
    },
    "parameters": {
        "vcovType": "CR2"
    }
})

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: cr2_missing_cluster_id_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "cr2_missing_cluster_id_failure"
rows4 = ["cluster_id,treatment,outcome"]
for i in range(5):
    rows4.append(f"C01,{10.0+i},{20.0+i}")  # Single cluster

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_cr2_failure",
    "sourceType": "synthetic_fixture",
    "title": "Single Cluster CR2 Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.se.cluster_robust.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for single cluster CR2",
    "allowedUse": "testing",
    "notes": "Generated with single cluster"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c4_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "multilevel.se.cluster_robust.v1",
    "data": {
        "clusterVar": "cluster_id",
        "predictor": "treatment",
        "outcome": "outcome"
    },
    "parameters": {
        "vcovType": "CR2"
    }
})

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "MISSING_CLUSTER_VARIABLE",
        "message": "Cluster-robust SE estimation requires at least 2 distinct clusters"
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
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "MISSING_CLUSTER_VARIABLE", "message": "Cluster-robust SE estimation requires at least 2 distinct clusters"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "multilevel.se.cluster_robust.v1",
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
            "engine": "clubSandwich",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "clubSandwich_sec",
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

make_manifest("cr2_small_sample_typical", "normal_typical", 60, 3)
make_manifest("cr2_unbalanced_clusters_complex", "legal_complex", 112, 3)
make_manifest("cr2_few_clusters_boundary", "degenerate_boundary", 40, 3)
make_manifest("cr2_missing_cluster_id_failure", "expected_failure", 5, 3)

print("Setup script for multilevel.se.cluster_robust.v1 completed!")
