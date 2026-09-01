import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "measurement.cfa.continuous.mlr.v1" / "cases"

# Remove old case
old_dir = CAP_DIR / "cfa_hs1939_mlr"
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

def generate_cfa_data(n_subjects, factor_corr=0.4, three_factors=False):
    if three_factors:
        header = "x1,x2,x3,y1,y2,y3,z1,z2,z3"
    else:
        header = "x1,x2,x3,y1,y2,y3"
    rows = [header]
    
    for _ in range(n_subjects):
        # Latent factors
        f1 = rng.gauss(0, 1.0)
        f2 = factor_corr * f1 + rng.gauss(0, (1 - factor_corr**2)**0.5)
        
        x1 = round(0.8 * f1 + rng.gauss(0, 0.6), 4)
        x2 = round(0.7 * f1 + rng.gauss(0, 0.7), 4)
        x3 = round(0.75 * f1 + rng.gauss(0, 0.65), 4)
        
        y1 = round(0.85 * f2 + rng.gauss(0, 0.55), 4)
        y2 = round(0.7 * f2 + rng.gauss(0, 0.7), 4)
        y3 = round(0.8 * f2 + rng.gauss(0, 0.6), 4)
        
        if three_factors:
            f3 = 0.3 * f1 + 0.3 * f2 + rng.gauss(0, 0.8)
            z1 = round(0.8 * f3 + rng.gauss(0, 0.6), 4)
            z2 = round(0.75 * f3 + rng.gauss(0, 0.65), 4)
            z3 = round(0.7 * f3 + rng.gauss(0, 0.7), 4)
            rows.append(f"{x1},{x2},{x3},{y1},{y2},{y3},{z1},{z2},{z3}")
        else:
            rows.append(f"{x1},{x2},{x3},{y1},{y2},{y3}")
            
    return rows

spec_typical = {
    "schemaVersion": "0.1.0",
    "analysisId": "measurement_cfa_fixture_001",
    "name": "Questionnaire CFA fixture",
    "datasetVersionId": "dataset_cfa_fixture_001",
    "confidenceLevel": 0.95,
    "seed": 20260727,
    "family": "questionnaire_measurement",
    "modelType": "cfa",
    "itemIds": ["x1", "x2", "x3", "y1", "y2", "y3"],
    "constructs": [
        {"id": "construct_x", "label": "X construct", "itemIds": ["x1", "x2", "x3"]},
        {"id": "construct_y", "label": "Y construct", "itemIds": ["y1", "y2", "y3"]}
    ],
    "itemScale": "continuous",
    "estimator": "MLR",
    "factorCount": 2
}

spec_three = {
    "schemaVersion": "0.1.0",
    "analysisId": "measurement_cfa_fixture_002",
    "name": "Three Factor CFA fixture",
    "datasetVersionId": "dataset_cfa_fixture_002",
    "confidenceLevel": 0.95,
    "seed": 20260727,
    "family": "questionnaire_measurement",
    "modelType": "cfa",
    "itemIds": ["x1", "x2", "x3", "y1", "y2", "y3", "z1", "z2", "z3"],
    "constructs": [
        {"id": "construct_x", "label": "X construct", "itemIds": ["x1", "x2", "x3"]},
        {"id": "construct_y", "label": "Y construct", "itemIds": ["y1", "y2", "y3"]},
        {"id": "construct_z", "label": "Z construct", "itemIds": ["z1", "z2", "z3"]}
    ],
    "itemScale": "continuous",
    "estimator": "MLR",
    "factorCount": 3
}

# -------------------------------------------------------------
# Case 1: cfa_continuous_mlr_typical (normal_typical)
# -------------------------------------------------------------
c1_dir = CAP_DIR / "cfa_continuous_mlr_typical"
rows1 = generate_cfa_data(200, factor_corr=0.4)

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_cfa_typical",
    "sourceType": "synthetic_fixture",
    "title": "Typical Continuous MLR CFA Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.cfa.continuous.mlr.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for MLR CFA",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260727"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c1_dir / "spec" / "analysis-spec.json", spec_typical)

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: cfa_continuous_mlr_three_factor_fiml (legal_complex)
# -------------------------------------------------------------
c2_dir = CAP_DIR / "cfa_continuous_mlr_three_factor_fiml"
rows2 = generate_cfa_data(300, factor_corr=0.35, three_factors=True)

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_cfa_three_factor",
    "sourceType": "synthetic_fixture",
    "title": "Three Factor Continuous MLR CFA Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.cfa.continuous.mlr.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for 3-factor MLR CFA",
    "allowedUse": "testing",
    "notes": "Generated with 3 latent constructs"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c2_dir / "spec" / "analysis-spec.json", spec_three)

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: cfa_continuous_mlr_collinear_boundary (degenerate_boundary)
# -------------------------------------------------------------
c3_dir = CAP_DIR / "cfa_continuous_mlr_collinear_boundary"
rows3 = generate_cfa_data(150, factor_corr=0.92)

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_cfa_collinear",
    "sourceType": "synthetic_fixture",
    "title": "Collinear Factor Correlation Boundary CFA Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.cfa.continuous.mlr.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for collinear factor correlation r=0.92",
    "allowedUse": "testing",
    "notes": "Generated with high factor correlation"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c3_dir / "spec" / "analysis-spec.json", spec_typical)

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: cfa_continuous_mlr_underidentified_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "cfa_continuous_mlr_underidentified_failure"
rows4 = ["x1,x2"]
for i in range(5):
    rows4.append(f"{1.0+i},{2.0+i}")

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_cfa_failure",
    "sourceType": "synthetic_fixture",
    "title": "Underidentified CFA Model Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.cfa.continuous.mlr.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for underidentified model",
    "allowedUse": "testing",
    "notes": "Generated with insufficient items"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

spec_failure = {
    "schemaVersion": "0.1.0",
    "analysisId": "measurement_cfa_fixture_failure",
    "name": "Underidentified CFA Model",
    "datasetVersionId": "dataset_cfa_fixture_failure",
    "confidenceLevel": 0.95,
    "seed": 20260727,
    "family": "questionnaire_measurement",
    "modelType": "cfa",
    "itemIds": ["x1", "x2"],
    "constructs": [
        {"id": "construct_x", "label": "X construct", "itemIds": ["x1", "x2"]}
    ],
    "itemScale": "continuous",
    "estimator": "MLR",
    "factorCount": 1
}
write_json(c4_dir / "spec" / "analysis-spec.json", spec_failure)

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "UNDERIDENTIFIED_MODEL",
        "message": "CFA model is underidentified; requires at least 3 indicators per factor"
    }
}
write_json(c4_dir / "reference" / "primary" / "normalized-output.json", failure_json)
write_json(c4_dir / "reference" / "secondary" / "normalized-output.json", failure_json)

write_text(c4_dir / "reference" / "primary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "primary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"UNDERIDENTIFIED_MODEL"}}', encoding="utf-8")
""")

write_text(c4_dir / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"UNDERIDENTIFIED_MODEL"}}', encoding="utf-8")
""")

write_text(c4_dir / "sut" / "run.py", """import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "UNDERIDENTIFIED_MODEL", "message": "CFA model is underidentified; requires at least 3 indicators per factor"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "measurement.cfa.continuous.mlr.v1",
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
            "engine": "lavaan_mlr",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "lavaan_mlr_sec",
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

make_manifest("cfa_continuous_mlr_typical", "normal_typical", 200, 6)
make_manifest("cfa_continuous_mlr_three_factor_fiml", "legal_complex", 300, 9)
make_manifest("cfa_continuous_mlr_collinear_boundary", "degenerate_boundary", 150, 6)
make_manifest("cfa_continuous_mlr_underidentified_failure", "expected_failure", 5, 2)

print("Setup script for measurement.cfa.continuous.mlr.v1 completed!")
