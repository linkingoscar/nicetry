import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "robustness.specification_curve.matrix.v1" / "cases"

# Remove old case
old_dir = CAP_DIR / "specification_curve_multiverse"
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

# -------------------------------------------------------------
# Case 1: sca_multiverse_typical (normal_typical)
# -------------------------------------------------------------
c1_dir = CAP_DIR / "sca_multiverse_typical"
rows1 = ["x,y,cov1,cov2"]
for i in range(80):
    x_val = round(rng.gauss(10, 2), 4)
    cov1_val = round(rng.gauss(5, 1), 4)
    cov2_val = round(rng.gauss(0, 1), 4)
    # y = 1.5 * x + 0.8 * cov1 + noise
    y_val = round(3.0 + 1.5 * x_val + 0.8 * cov1_val + rng.gauss(0, 1.5), 4)
    rows1.append(f"{x_val},{y_val},{cov1_val},{cov2_val}")

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_sca_typical",
    "sourceType": "synthetic_fixture",
    "title": "Typical Specification Curve Multiverse Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/robustness.specification_curve.matrix.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for SCA multiverse",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260727"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c1_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "robustness.specification_curve.matrix.v1",
    "data": {
        "x": "x",
        "y": "y",
        "covariates": ["cov1", "cov2"]
    },
    "parameters": {
        "modelTypes": ["ols", "robust"],
        "subsets": ["full", "trimmed"]
    }
})

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: sca_high_dimensional_complex (legal_complex)
# -------------------------------------------------------------
c2_dir = CAP_DIR / "sca_high_dimensional_complex"
rows2 = ["x,y,cov1,cov2,cov3"]
for i in range(120):
    x_val = round(rng.gauss(12, 3), 4)
    cov1_val = round(rng.gauss(4, 1), 4)
    cov2_val = round(rng.gauss(2, 1), 4)
    cov3_val = round(rng.gauss(0, 1), 4)
    y_val = round(5.0 + 2.0 * x_val + 1.1 * cov1_val - 0.5 * cov2_val + rng.gauss(0, 2.0), 4)
    rows2.append(f"{x_val},{y_val},{cov1_val},{cov2_val},{cov3_val}")

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_sca_complex",
    "sourceType": "synthetic_fixture",
    "title": "High Dimensional Specification Curve Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/robustness.specification_curve.matrix.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for high dimensional SCA",
    "allowedUse": "testing",
    "notes": "Generated with 3 covariates"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c2_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "robustness.specification_curve.matrix.v1",
    "data": {
        "x": "x",
        "y": "y",
        "covariates": ["cov1", "cov2", "cov3"]
    },
    "parameters": {
        "modelTypes": ["ols", "robust"],
        "subsets": ["full", "trimmed"]
    }
})

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: sca_single_spec_boundary (degenerate_boundary)
# -------------------------------------------------------------
c3_dir = CAP_DIR / "sca_single_spec_boundary"
rows3 = ["x,y"]
for i in range(60):
    x_val = round(rng.gauss(10, 2), 4)
    y_val = round(2.0 + 1.0 * x_val + rng.gauss(0, 1.0), 4)
    rows3.append(f"{x_val},{y_val}")

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_sca_boundary",
    "sourceType": "synthetic_fixture",
    "title": "Single Specification Boundary SCA Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/robustness.specification_curve.matrix.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for single specification SCA",
    "allowedUse": "testing",
    "notes": "Generated with no covariates and single model/subset"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c3_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "robustness.specification_curve.matrix.v1",
    "data": {
        "x": "x",
        "y": "y",
        "covariates": []
    },
    "parameters": {
        "modelTypes": ["ols"],
        "subsets": ["full"]
    }
})

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: sca_missing_predictor_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "sca_missing_predictor_failure"
rows4 = ["y,cov1"]
for i in range(5):
    rows4.append(f"{10.0+i},1.0")

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_sca_failure",
    "sourceType": "synthetic_fixture",
    "title": "Missing Predictor SCA Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/robustness.specification_curve.matrix.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for missing predictor variable",
    "allowedUse": "testing",
    "notes": "Generated with missing predictor x"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c4_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "robustness.specification_curve.matrix.v1",
    "data": {
        "x": "x",
        "y": "y",
        "covariates": ["cov1"]
    },
    "parameters": {
        "modelTypes": ["ols"],
        "subsets": ["full"]
    }
})

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "MISSING_PREDICTOR_VARIABLE",
        "message": "Predictor variable 'x' is missing from input dataset"
    }
}
write_json(c4_dir / "reference" / "primary" / "normalized-output.json", failure_json)
write_json(c4_dir / "reference" / "secondary" / "normalized-output.json", failure_json)

write_text(c4_dir / "reference" / "primary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "primary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"MISSING_PREDICTOR_VARIABLE"}}', encoding="utf-8")
""")

write_text(c4_dir / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"MISSING_PREDICTOR_VARIABLE"}}', encoding="utf-8")
""")

write_text(c4_dir / "sut" / "run.py", """import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "MISSING_PREDICTOR_VARIABLE", "message": "Predictor variable 'x' is missing from input dataset"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "robustness.specification_curve.matrix.v1",
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
            "engine": "python_sca",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "python_sca_sec",
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

make_manifest("sca_multiverse_typical", "normal_typical", 80, 4)
make_manifest("sca_high_dimensional_complex", "legal_complex", 120, 5)
make_manifest("sca_single_spec_boundary", "degenerate_boundary", 60, 2)
make_manifest("sca_missing_predictor_failure", "expected_failure", 5, 2)

print("Setup script for robustness.specification_curve.matrix.v1 completed!")
