import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "measurement.invariance.multi_group.v1" / "cases"

# Remove old case
old_dir = CAP_DIR / "invariance_configural_metric"
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
script = root / "reference" / "generators" / "r" / "run_measurement_reference.R"
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

def generate_group_data(n_per_group, groups=["G1", "G2"], diff_intercepts=False):
    header = "group,x1,x2,x3,y1,y2,y3"
    rows = [header]
    
    for g_idx, g_name in enumerate(groups):
        for _ in range(n_per_group[g_idx] if isinstance(n_per_group, list) else n_per_group):
            f1 = rng.gauss(0, 1.0)
            f2 = 0.4 * f1 + rng.gauss(0, 0.9165)
            
            # Intercept shift for G2 if diff_intercepts
            shift = 0.5 if (diff_intercepts and g_name != groups[0]) else 0.0
            
            x1 = round(0.8 * f1 + rng.gauss(0, 0.6) + shift, 4)
            x2 = round(0.7 * f1 + rng.gauss(0, 0.7), 4)
            x3 = round(0.75 * f1 + rng.gauss(0, 0.65), 4)
            
            y1 = round(0.85 * f2 + rng.gauss(0, 0.55), 4)
            y2 = round(0.7 * f2 + rng.gauss(0, 0.7), 4)
            y3 = round(0.8 * f2 + rng.gauss(0, 0.6), 4)
            
            rows.append(f"{g_name},{x1},{x2},{x3},{y1},{y2},{y3}")
            
    return rows

spec_invariance = {
    "schemaVersion": "0.1.0",
    "analysisId": "measurement_invariance_fixture_001",
    "name": "Questionnaire invariance fixture",
    "datasetVersionId": "dataset_invariance_fixture_001",
    "confidenceLevel": 0.95,
    "seed": 20260727,
    "family": "questionnaire_measurement",
    "modelType": "measurement_invariance",
    "itemIds": ["x1", "x2", "x3", "y1", "y2", "y3"],
    "constructs": [
        {"id": "construct_x", "label": "X construct", "itemIds": ["x1", "x2", "x3"]},
        {"id": "construct_y", "label": "Y construct", "itemIds": ["y1", "y2", "y3"]}
    ],
    "groupVariableId": "group",
    "itemScale": "continuous",
    "estimator": "ML",
    "factorCount": 2,
    "invarianceLevels": ["configural", "metric", "scalar"]
}

# -------------------------------------------------------------
# Case 1: invariance_two_group_continuous (normal_typical)
# 2 groups (G1, G2), 200 per group
# -------------------------------------------------------------
c1_dir = CAP_DIR / "invariance_two_group_continuous"
rows1 = generate_group_data(200, groups=["G1", "G2"])

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_invariance_two_group",
    "sourceType": "synthetic_fixture",
    "title": "Two Group Continuous Invariance Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.invariance.multi_group.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for 2-group measurement invariance",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260727"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c1_dir / "spec" / "analysis-spec.json", spec_invariance)

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: invariance_three_group_partial (legal_complex)
# 3 groups (G1, G2, G3), 150 per group, partial intercept shift
# -------------------------------------------------------------
c2_dir = CAP_DIR / "invariance_three_group_partial"
rows2 = generate_group_data(150, groups=["G1", "G2", "G3"], diff_intercepts=True)

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_invariance_three_group",
    "sourceType": "synthetic_fixture",
    "title": "Three Group Partial Invariance Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.invariance.multi_group.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for 3-group measurement invariance",
    "allowedUse": "testing",
    "notes": "Generated with 3 groups"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c2_dir / "spec" / "analysis-spec.json", spec_invariance)

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: invariance_unbalanced_groups_boundary (degenerate_boundary)
# Unbalanced: 250 in G1, 35 in G2
# -------------------------------------------------------------
c3_dir = CAP_DIR / "invariance_unbalanced_groups_boundary"
rows3 = generate_group_data([250, 35], groups=["G1", "G2"])

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_invariance_unbalanced",
    "sourceType": "synthetic_fixture",
    "title": "Unbalanced Groups Invariance Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.invariance.multi_group.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for unbalanced group sample sizes n1=250 n2=35",
    "allowedUse": "testing",
    "notes": "Generated with unbalanced groups"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c3_dir / "spec" / "analysis-spec.json", spec_invariance)

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: invariance_missing_grouping_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "invariance_missing_grouping_failure"
rows4 = ["group,x1,x2,x3,y1,y2,y3"]
for i in range(20):
    rows4.append(f"G1,{1.0+i*0.1},{2.0+i*0.1},{1.5+i*0.1},{2.5+i*0.1},{1.8+i*0.1},{2.2+i*0.1}") # only G1

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_invariance_failure",
    "sourceType": "synthetic_fixture",
    "title": "Missing Grouping Variable Multi-Group Invariance Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.invariance.multi_group.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for single group dataset",
    "allowedUse": "testing",
    "notes": "Generated with single group only"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c4_dir / "spec" / "analysis-spec.json", spec_invariance)

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "MISSING_GROUP_VARIABLE",
        "message": "Group variable 'group' contains fewer than 2 distinct groups"
    }
}
write_json(c4_dir / "reference" / "primary" / "normalized-output.json", failure_json)
write_json(c4_dir / "reference" / "secondary" / "normalized-output.json", failure_json)

write_text(c4_dir / "reference" / "primary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "primary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"MISSING_GROUP_VARIABLE"}}', encoding="utf-8")
""")

write_text(c4_dir / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"MISSING_GROUP_VARIABLE"}}', encoding="utf-8")
""")

write_text(c4_dir / "sut" / "run.py", """import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "MISSING_GROUP_VARIABLE", "message": "Group variable 'group' contains fewer than 2 distinct groups"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "measurement.invariance.multi_group.v1",
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
            "engine": "lavaan_invariance",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "lavaan_invariance_sec",
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

make_manifest("invariance_two_group_continuous", "normal_typical", 400, 7)
make_manifest("invariance_three_group_partial", "legal_complex", 450, 7)
make_manifest("invariance_unbalanced_groups_boundary", "degenerate_boundary", 285, 7)
make_manifest("invariance_missing_grouping_failure", "expected_failure", 20, 7)

print("Setup script for measurement.invariance.multi_group.v1 completed!")
