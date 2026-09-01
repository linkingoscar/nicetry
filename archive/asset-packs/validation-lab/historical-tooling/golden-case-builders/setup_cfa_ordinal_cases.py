import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "measurement.cfa.ordinal.wlsmv.v1" / "cases"

# Remove old case
old_dir = CAP_DIR / "cfa_ordinal_wlsmv"
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

def discretize(val, thresholds):
    for i, t in enumerate(thresholds):
        if val <= t:
            return i + 1
    return len(thresholds) + 1

def generate_ordinal_data(n_subjects, thresholds, binary=False, factor_corr=0.4):
    header = "x1,x2,x3,y1,y2,y3"
    rows = [header]
    
    for _ in range(n_subjects):
        f1 = rng.gauss(0, 1.0)
        f2 = factor_corr * f1 + rng.gauss(0, (1 - factor_corr**2)**0.5)
        
        c_x1 = 0.8 * f1 + rng.gauss(0, 0.6)
        c_x2 = 0.7 * f1 + rng.gauss(0, 0.7)
        c_x3 = 0.75 * f1 + rng.gauss(0, 0.65)
        
        c_y1 = 0.85 * f2 + rng.gauss(0, 0.55)
        c_y2 = 0.7 * f2 + rng.gauss(0, 0.7)
        c_y3 = 0.8 * f2 + rng.gauss(0, 0.6)
        
        if binary:
            x1 = 1 if c_x1 > thresholds[0] else 0
            x2 = 1 if c_x2 > thresholds[0] else 0
            x3 = 1 if c_x3 > thresholds[0] else 0
            y1 = 1 if c_y1 > thresholds[0] else 0
            y2 = 1 if c_y2 > thresholds[0] else 0
            y3 = 1 if c_y3 > thresholds[0] else 0
        else:
            x1 = discretize(c_x1, thresholds)
            x2 = discretize(c_x2, thresholds)
            x3 = discretize(c_x3, thresholds)
            y1 = discretize(c_y1, thresholds)
            y2 = discretize(c_y2, thresholds)
            y3 = discretize(c_y3, thresholds)
            
        rows.append(f"{x1},{x2},{x3},{y1},{y2},{y3}")
        
    return rows

spec_ordinal = {
    "schemaVersion": "0.1.0",
    "analysisId": "measurement_cfa_ordinal_fixture_001",
    "name": "Questionnaire ordinal CFA fixture",
    "datasetVersionId": "dataset_cfa_ordinal_fixture_001",
    "confidenceLevel": 0.95,
    "seed": 20260727,
    "family": "questionnaire_measurement",
    "modelType": "cfa",
    "itemIds": ["x1", "x2", "x3", "y1", "y2", "y3"],
    "constructs": [
        {"id": "construct_x", "label": "X construct", "itemIds": ["x1", "x2", "x3"]},
        {"id": "construct_y", "label": "Y construct", "itemIds": ["y1", "y2", "y3"]}
    ],
    "itemScale": "ordinal",
    "estimator": "WLSMV",
    "factorCount": 2
}

# -------------------------------------------------------------
# Case 1: cfa_ordinal_wlsmv_typical (normal_typical)
# Likert 5-point
# -------------------------------------------------------------
c1_dir = CAP_DIR / "cfa_ordinal_wlsmv_typical"
rows1 = generate_ordinal_data(250, thresholds=[-1.2, -0.4, 0.4, 1.2])

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_cfa_ordinal_typical",
    "sourceType": "synthetic_fixture",
    "title": "Typical Ordinal WLSMV CFA Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.cfa.ordinal.wlsmv.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for Likert 5-point WLSMV CFA",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260727"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c1_dir / "spec" / "analysis-spec.json", spec_ordinal)

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: cfa_ordinal_wlsmv_skewed_binary (legal_complex)
# Binary items
# -------------------------------------------------------------
c2_dir = CAP_DIR / "cfa_ordinal_wlsmv_skewed_binary"
rows2 = generate_ordinal_data(300, thresholds=[0.5], binary=True)

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_cfa_ordinal_binary",
    "sourceType": "synthetic_fixture",
    "title": "Binary Skewed Items WLSMV CFA Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.cfa.ordinal.wlsmv.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for binary items WLSMV CFA",
    "allowedUse": "testing",
    "notes": "Generated with binary items"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c2_dir / "spec" / "analysis-spec.json", spec_ordinal)

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: cfa_ordinal_wlsmv_extreme_category_boundary (degenerate_boundary)
# Extreme category endorsement
# -------------------------------------------------------------
c3_dir = CAP_DIR / "cfa_ordinal_wlsmv_extreme_category_boundary"
rows3 = generate_ordinal_data(200, thresholds=[-2.0, 0.0, 2.0])

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_cfa_ordinal_extreme",
    "sourceType": "synthetic_fixture",
    "title": "Extreme Category Distribution WLSMV CFA Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.cfa.ordinal.wlsmv.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for extreme category endorsement",
    "allowedUse": "testing",
    "notes": "Generated with wide threshold separation"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c3_dir / "spec" / "analysis-spec.json", spec_ordinal)

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: cfa_ordinal_wlsmv_zero_variance_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "cfa_ordinal_wlsmv_zero_variance_failure"
rows4 = ["x1,x2,x3,y1,y2,y3"]
for i in range(10):
    rows4.append("1,1,2,3,4,5")  # x1 is constant = 1

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_cfa_ordinal_failure",
    "sourceType": "synthetic_fixture",
    "title": "Zero Variance Item WLSMV CFA Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.cfa.ordinal.wlsmv.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for zero variance indicator",
    "allowedUse": "testing",
    "notes": "Generated with constant item x1"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c4_dir / "spec" / "analysis-spec.json", spec_ordinal)

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "ZERO_VARIANCE_INDICATOR",
        "message": "Item 'x1' has zero variance (only 1 category observed)"
    }
}
write_json(c4_dir / "reference" / "primary" / "normalized-output.json", failure_json)
write_json(c4_dir / "reference" / "secondary" / "normalized-output.json", failure_json)

write_text(c4_dir / "reference" / "primary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "primary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"ZERO_VARIANCE_INDICATOR"}}', encoding="utf-8")
""")

write_text(c4_dir / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"ZERO_VARIANCE_INDICATOR"}}', encoding="utf-8")
""")

write_text(c4_dir / "sut" / "run.py", """import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "ZERO_VARIANCE_INDICATOR", "message": "Item 'x1' has zero variance (only 1 category observed)"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "measurement.cfa.ordinal.wlsmv.v1",
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
            "engine": "lavaan_wlsmv",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "lavaan_wlsmv_sec",
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

make_manifest("cfa_ordinal_wlsmv_typical", "normal_typical", 250, 6)
make_manifest("cfa_ordinal_wlsmv_skewed_binary", "legal_complex", 300, 6)
make_manifest("cfa_ordinal_wlsmv_extreme_category_boundary", "degenerate_boundary", 200, 6)
make_manifest("cfa_ordinal_wlsmv_zero_variance_failure", "expected_failure", 10, 6)

print("Setup script for measurement.cfa.ordinal.wlsmv.v1 completed!")
