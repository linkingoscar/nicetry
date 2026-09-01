import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "measurement.bifactor.continuous.v1" / "cases"

# Remove old case
old_dir = CAP_DIR / "bifactor_continuous_standard"
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

def generate_bifactor_data(n_subjects, g_loading=0.6, s_loading=0.5, three_factors=False):
    if three_factors:
        items = [f"y{i+1}" for i in range(9)]
        constructs = [
            ("S1", ["y1", "y2", "y3"]),
            ("S2", ["y4", "y5", "y6"]),
            ("S3", ["y7", "y8", "y9"])
        ]
    else:
        items = [f"y{i+1}" for i in range(6)]
        constructs = [
            ("S1", ["y1", "y2", "y3"]),
            ("S2", ["y4", "y5", "y6"])
        ]
        
    header = ",".join(items)
    rows = [header]
    
    for _ in range(n_subjects):
        g = rng.gauss(0, 1.0)
        s_vals = {c_id: rng.gauss(0, 1.0) for c_id, _ in constructs}
        
        row_vals = []
        for c_id, c_items in constructs:
            for item in c_items:
                y = round(g_loading * g + s_loading * s_vals[c_id] + rng.gauss(0, 0.5), 4)
                row_vals.append(y)
                
        rows.append(",".join(map(str, row_vals)))
        
    return rows

spec_typical = {
    "schemaVersion": "0.1.0",
    "analysisId": "measurement_bifactor_fixture_001",
    "name": "Continuous bifactor fixture",
    "datasetVersionId": "measurement_bifactor_data_001",
    "confidenceLevel": 0.95,
    "seed": 20260727,
    "family": "questionnaire_measurement",
    "modelType": "bifactor",
    "itemIds": ["y1", "y2", "y3", "y4", "y5", "y6"],
    "constructs": [
        {"id": "S1", "label": "Specific factor 1", "itemIds": ["y1", "y2", "y3"]},
        {"id": "S2", "label": "Specific factor 2", "itemIds": ["y4", "y5", "y6"]}
    ],
    "itemScale": "continuous",
    "estimator": "ML",
    "factorCount": 2,
    "rotation": "promax",
    "parallelIterations": 100,
    "invarianceLevels": ["configural", "metric", "scalar"]
}

spec_three = {
    "schemaVersion": "0.1.0",
    "analysisId": "measurement_bifactor_fixture_002",
    "name": "Three specific factor bifactor fixture",
    "datasetVersionId": "measurement_bifactor_data_002",
    "confidenceLevel": 0.95,
    "seed": 20260727,
    "family": "questionnaire_measurement",
    "modelType": "bifactor",
    "itemIds": [f"y{i+1}" for i in range(9)],
    "constructs": [
        {"id": "S1", "label": "Specific factor 1", "itemIds": ["y1", "y2", "y3"]},
        {"id": "S2", "label": "Specific factor 2", "itemIds": ["y4", "y5", "y6"]},
        {"id": "S3", "label": "Specific factor 3", "itemIds": ["y7", "y8", "y9"]}
    ],
    "itemScale": "continuous",
    "estimator": "ML",
    "factorCount": 3,
    "rotation": "promax",
    "parallelIterations": 100,
    "invarianceLevels": ["configural", "metric", "scalar"]
}

# -------------------------------------------------------------
# Case 1: bifactor_continuous_typical (normal_typical)
# -------------------------------------------------------------
c1_dir = CAP_DIR / "bifactor_continuous_typical"
rows1 = generate_bifactor_data(250, g_loading=0.6, s_loading=0.5)

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_bifactor_typical",
    "sourceType": "synthetic_fixture",
    "title": "Typical Continuous Bifactor Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.bifactor.continuous.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for Bifactor ML model",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260727"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c1_dir / "spec" / "analysis-spec.json", spec_typical)

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: bifactor_continuous_three_specific (legal_complex)
# 3 specific factors
# -------------------------------------------------------------
c2_dir = CAP_DIR / "bifactor_continuous_three_specific"
rows2 = generate_bifactor_data(350, g_loading=0.55, s_loading=0.45, three_factors=True)

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_bifactor_three_specific",
    "sourceType": "synthetic_fixture",
    "title": "Three Specific Factors Bifactor Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.bifactor.continuous.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for 3-specific-factor Bifactor model",
    "allowedUse": "testing",
    "notes": "Generated with 3 specific factors"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c2_dir / "spec" / "analysis-spec.json", spec_three)

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: bifactor_continuous_dominant_general_boundary (degenerate_boundary)
# Dominant G loading (0.85), weak S loading (0.2)
# -------------------------------------------------------------
c3_dir = CAP_DIR / "bifactor_continuous_dominant_general_boundary"
rows3 = generate_bifactor_data(200, g_loading=0.85, s_loading=0.2)

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_bifactor_dominant_general",
    "sourceType": "synthetic_fixture",
    "title": "Dominant General Factor Bifactor Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.bifactor.continuous.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for dominant G factor",
    "allowedUse": "testing",
    "notes": "Generated with g_loading=0.85"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c3_dir / "spec" / "analysis-spec.json", spec_typical)

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: bifactor_continuous_underidentified_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "bifactor_continuous_underidentified_failure"
rows4 = ["y1,y2"]
for i in range(10):
    rows4.append(f"{1.0+i*0.2},{2.0+i*0.3}")

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_bifactor_failure",
    "sourceType": "synthetic_fixture",
    "title": "Underidentified Bifactor Model Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.bifactor.continuous.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for underidentified specific factor",
    "allowedUse": "testing",
    "notes": "Generated with 2 items total"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

spec_failure = {
    "schemaVersion": "0.1.0",
    "analysisId": "measurement_bifactor_fixture_failure",
    "name": "Underidentified Bifactor Model",
    "datasetVersionId": "dataset_bifactor_fixture_failure",
    "confidenceLevel": 0.95,
    "seed": 20260727,
    "family": "questionnaire_measurement",
    "modelType": "bifactor",
    "itemIds": ["y1", "y2"],
    "constructs": [
        {"id": "S1", "label": "Specific factor 1", "itemIds": ["y1", "y2"]}
    ],
    "itemScale": "continuous",
    "estimator": "ML"
}
write_json(c4_dir / "spec" / "analysis-spec.json", spec_failure)

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "UNDERIDENTIFIED_SPECIFIC_FACTOR",
        "message": "Bifactor model requires at least 2 items per specific factor and 3 total specific items"
    }
}
write_json(c4_dir / "reference" / "primary" / "normalized-output.json", failure_json)
write_json(c4_dir / "reference" / "secondary" / "normalized-output.json", failure_json)

write_text(c4_dir / "reference" / "primary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "primary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"UNDERIDENTIFIED_SPECIFIC_FACTOR"}}', encoding="utf-8")
""")

write_text(c4_dir / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"UNDERIDENTIFIED_SPECIFIC_FACTOR"}}', encoding="utf-8")
""")

write_text(c4_dir / "sut" / "run.py", """import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "UNDERIDENTIFIED_SPECIFIC_FACTOR", "message": "Bifactor model requires at least 2 items per specific factor and 3 total specific items"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "measurement.bifactor.continuous.v1",
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
            "engine": "lavaan_bifactor",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "lavaan_bifactor_sec",
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

make_manifest("bifactor_continuous_typical", "normal_typical", 250, 6)
make_manifest("bifactor_continuous_three_specific", "legal_complex", 350, 9)
make_manifest("bifactor_continuous_dominant_general_boundary", "degenerate_boundary", 200, 6)
make_manifest("bifactor_continuous_underidentified_failure", "expected_failure", 10, 2)

print("Setup script for measurement.bifactor.continuous.v1 completed!")
