import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "multilevel.lmm.two_level.gaussian.random_slope.v1" / "cases"

# Clean up old case if exists
old_dir = CAP_DIR / "sleepstudy_random_slope"
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
# Case 1: lmm_random_slope_typical (normal_typical)
# -------------------------------------------------------------
c1_dir = CAP_DIR / "lmm_random_slope_typical"
rows1 = ["Reaction,Days,Subject"]
for s in range(1, 19):
    sid = f"S{s:02d}"
    u0 = rng.gauss(0, 25.0)  # Random intercept
    u1 = rng.gauss(0, 5.0)   # Random slope
    for day in range(10):
        reaction = round(250.0 + u0 + (10.0 + u1) * day + rng.gauss(0, 15.0), 4)
        rows1.append(f"{reaction},{day},{sid}")

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_lmm_slope_typical",
    "sourceType": "synthetic_fixture",
    "title": "Typical Two-Level Random Slope LMM Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.lmm.two_level.gaussian.random_slope.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for two-level random slope LMM",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260726"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c1_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "lmm_random_slope_typical",
    "name": "Typical Two-Level Random Slope LMM",
    "datasetVersionId": "synthetic_lmm_typical",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "multilevel_model",
    "outcomeId": "Reaction",
    "distribution": "gaussian",
    "clusterVariableId": "Subject",
    "higherLevelClusterVariableId": None,
    "fixedEffectIds": ["Days"],
    "randomEffects": [
        {"groupingVariableId": "Subject", "intercept": True, "slopeVariableIds": ["Days"], "covariance": "correlated"}
    ],
    "centering": [],
    "estimator": "REML",
    "degreesOfFreedom": "satterthwaite",
    "minimumClusterCount": 15
})

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: lmm_random_slope_unbalanced (legal_complex)
# -------------------------------------------------------------
c2_dir = CAP_DIR / "lmm_random_slope_unbalanced"
rows2 = ["Reaction,Days,Subject"]
for s in range(1, 21):
    sid = f"S{s:02d}"
    u0 = rng.gauss(0, 30.0)
    u1 = rng.gauss(0, 6.0)
    obs_cnt = 5 if s % 2 == 0 else 12
    for day in range(obs_cnt):
        reaction = round(240.0 + u0 + (12.0 + u1) * day + rng.gauss(0, 18.0), 4)
        rows2.append(f"{reaction},{day},{sid}")

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_lmm_slope_unbalanced",
    "sourceType": "synthetic_fixture",
    "title": "Unbalanced Random Slope LMM Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.lmm.two_level.gaussian.random_slope.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for unbalanced random slope LMM",
    "allowedUse": "testing",
    "notes": "Generated with varying observations per subject"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c2_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "lmm_random_slope_unbalanced",
    "name": "Unbalanced Two-Level Random Slope LMM",
    "datasetVersionId": "synthetic_lmm_unbalanced",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "multilevel_model",
    "outcomeId": "Reaction",
    "distribution": "gaussian",
    "clusterVariableId": "Subject",
    "higherLevelClusterVariableId": None,
    "fixedEffectIds": ["Days"],
    "randomEffects": [
        {"groupingVariableId": "Subject", "intercept": True, "slopeVariableIds": ["Days"], "covariance": "correlated"}
    ],
    "centering": [],
    "estimator": "REML",
    "degreesOfFreedom": "satterthwaite",
    "minimumClusterCount": 15
})

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: lmm_singular_covariance_boundary (degenerate_boundary)
# -------------------------------------------------------------
c3_dir = CAP_DIR / "lmm_singular_covariance_boundary"
rows3 = ["Reaction,Days,Subject"]
for s in range(1, 16):
    sid = f"S{s:02d}"
    u0 = rng.gauss(0, 20.0)
    u1 = rng.gauss(0, 0.0001)  # Singular / near zero random slope variance
    for day in range(8):
        reaction = round(250.0 + u0 + (10.0 + u1) * day + rng.gauss(0, 10.0), 4)
        rows3.append(f"{reaction},{day},{sid}")

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_lmm_slope_boundary",
    "sourceType": "synthetic_fixture",
    "title": "Singular Covariance Random Slope LMM Boundary Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.lmm.two_level.gaussian.random_slope.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for near-zero random slope variance",
    "allowedUse": "testing",
    "notes": "Generated with near zero random slope SD"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c3_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "lmm_singular_covariance_boundary",
    "name": "Singular Covariance Boundary LMM",
    "datasetVersionId": "synthetic_lmm_singular",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "multilevel_model",
    "outcomeId": "Reaction",
    "distribution": "gaussian",
    "clusterVariableId": "Subject",
    "higherLevelClusterVariableId": None,
    "fixedEffectIds": ["Days"],
    "randomEffects": [
        {"groupingVariableId": "Subject", "intercept": True, "slopeVariableIds": ["Days"], "covariance": "correlated"}
    ],
    "centering": [],
    "estimator": "REML",
    "degreesOfFreedom": "satterthwaite",
    "minimumClusterCount": 10
})

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: lmm_missing_cluster_id_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "lmm_missing_cluster_id_failure"
rows4 = ["Reaction,Days,Subject"]
for day in range(10):
    rows4.append(f"{250.0 + 10.0*day},{day},S01")  # Single cluster

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_lmm_slope_failure",
    "sourceType": "synthetic_fixture",
    "title": "Single Cluster LMM Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/multilevel.lmm.two_level.gaussian.random_slope.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for single cluster LMM",
    "allowedUse": "testing",
    "notes": "Generated with only 1 cluster"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c4_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "lmm_missing_cluster_id_failure",
    "name": "Single Cluster Failure LMM",
    "datasetVersionId": "synthetic_single_cluster",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "multilevel_model",
    "outcomeId": "Reaction",
    "distribution": "gaussian",
    "clusterVariableId": "Subject",
    "higherLevelClusterVariableId": None,
    "fixedEffectIds": ["Days"],
    "randomEffects": [
        {"groupingVariableId": "Subject", "intercept": True, "slopeVariableIds": ["Days"], "covariance": "correlated"}
    ],
    "centering": [],
    "estimator": "REML",
    "degreesOfFreedom": "satterthwaite",
    "minimumClusterCount": 10
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
            "capabilityId": "multilevel.lmm.two_level.gaussian.random_slope.v1",
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
            "engine": "lmerTest",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "lmerTest_sec",
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

make_manifest("lmm_random_slope_typical", "normal_typical", 180, 3)
make_manifest("lmm_random_slope_unbalanced", "legal_complex", 170, 3)
make_manifest("lmm_singular_covariance_boundary", "degenerate_boundary", 120, 3)
make_manifest("lmm_missing_cluster_id_failure", "expected_failure", 10, 3)

print("Setup script for multilevel.lmm.two_level.gaussian.random_slope.v1 completed!")
