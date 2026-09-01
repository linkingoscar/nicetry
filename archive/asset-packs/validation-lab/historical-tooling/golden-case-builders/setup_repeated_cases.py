import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "experiment.repeated.one_within.v1" / "cases"

# Clean up old case if exists
old_dir = CAP_DIR / "obrien_kaiser_repeated"
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
# Case 1: repeated_balanced_one_within (normal_typical)
# -------------------------------------------------------------
c1_dir = CAP_DIR / "repeated_balanced_one_within"
rows1 = ["id,treatment,phase,value"]
treatments = ["control", "drug"]
phases = ["pre", "post", "fup"]
means1 = {
    ("control", "pre"): 10.0, ("control", "post"): 11.0, ("control", "fup"): 10.5,
    ("drug", "pre"): 10.0, ("drug", "post"): 18.0, ("drug", "fup"): 22.0
}
sub_idx = 1
for tr in treatments:
    for _ in range(8):
        sid = f"S{sub_idx:02d}"
        sub_effect = rng.gauss(0, 1.5)
        for ph in phases:
            val = round(means1[(tr, ph)] + sub_effect + rng.gauss(0, 1.0), 4)
            rows1.append(f"{sid},{tr},{ph},{val}")
        sub_idx += 1

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_repeated_balanced",
    "sourceType": "synthetic_fixture",
    "title": "Balanced One-Within Repeated Measures Design Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/experiment.repeated.one_within.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for repeated measures ANOVA",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260726"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c1_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "repeated_balanced_one_within",
    "name": "Balanced One-Within Repeated Measures ANOVA",
    "datasetVersionId": "synthetic_repeated_balanced",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "experimental_design",
    "designType": "mixed_design",
    "dataLayout": "long",
    "outcomeIds": ["value"],
    "betweenFactors": [
        {"variableId": "treatment", "coding": "sum", "referenceLevel": None}
    ],
    "withinFactors": [
        {"id": "phase", "name": "Phase", "levels": ["fup", "post", "pre"], "columns": {}}
    ],
    "subjectId": "id",
    "covariateIds": [],
    "sumOfSquares": "III",
    "sphericityCorrection": "greenhouse_geisser",
    "postHocAdjustment": "holm",
    "covariateCentering": "grand_mean",
    "homogeneityOfSlopes": "check_and_warn"
})

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: repeated_sphericity_violation (legal_complex)
# -------------------------------------------------------------
c2_dir = CAP_DIR / "repeated_sphericity_violation"
rows2 = ["id,treatment,phase,value"]
sub_idx = 1
for tr in treatments:
    for _ in range(8):
        sid = f"S{sub_idx:02d}"
        e1 = rng.gauss(0, 0.5)
        e2 = rng.gauss(0, 5.0)  # Extreme variance inflation for phase 2
        e3 = rng.gauss(0, 0.5)
        vals = {"pre": round(10.0 + e1, 4), "post": round(15.0 + e2, 4), "fup": round(20.0 + e3, 4)}
        for ph in phases:
            rows2.append(f"{sid},{tr},{ph},{vals[ph]}")
        sub_idx += 1

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_repeated_sphericity_violation",
    "sourceType": "synthetic_fixture",
    "title": "Sphericity Violation Repeated Measures Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/experiment.repeated.one_within.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for GG/HF epsilon correction under sphericity violation",
    "allowedUse": "testing",
    "notes": "Generated with unequal covariance matrix across time"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c2_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "repeated_sphericity_violation",
    "name": "Sphericity Violation Repeated Measures ANOVA",
    "datasetVersionId": "synthetic_repeated_sphericity",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "experimental_design",
    "designType": "mixed_design",
    "dataLayout": "long",
    "outcomeIds": ["value"],
    "betweenFactors": [
        {"variableId": "treatment", "coding": "sum", "referenceLevel": None}
    ],
    "withinFactors": [
        {"id": "phase", "name": "Phase", "levels": ["fup", "post", "pre"], "columns": {}}
    ],
    "subjectId": "id",
    "covariateIds": [],
    "sumOfSquares": "III",
    "sphericityCorrection": "greenhouse_geisser",
    "postHocAdjustment": "holm",
    "covariateCentering": "grand_mean",
    "homogeneityOfSlopes": "check_and_warn"
})

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: repeated_near_perfect_correlation_boundary (degenerate_boundary)
# -------------------------------------------------------------
c3_dir = CAP_DIR / "repeated_near_perfect_correlation_boundary"
rows3 = ["id,treatment,phase,value"]
sub_idx = 1
for tr in treatments:
    for _ in range(8):
        sid = f"S{sub_idx:02d}"
        sub_effect = rng.gauss(0, 5.0)  # High subject variance
        for ph in phases:
            val = round(10.0 + sub_effect + rng.gauss(0, 0.01), 4)  # Tiny within-subject noise
            rows3.append(f"{sid},{tr},{ph},{val}")
        sub_idx += 1

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_repeated_high_correlation",
    "sourceType": "synthetic_fixture",
    "title": "Near Perfect Correlation Repeated Measures Boundary Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/experiment.repeated.one_within.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary synthetic fixture for near-perfect correlation across waves",
    "allowedUse": "testing",
    "notes": "Generated with high subject random effect and tiny noise"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c3_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "repeated_near_perfect_correlation_boundary",
    "name": "High Correlation Boundary Repeated Measures ANOVA",
    "datasetVersionId": "synthetic_repeated_high_corr",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "experimental_design",
    "designType": "mixed_design",
    "dataLayout": "long",
    "outcomeIds": ["value"],
    "betweenFactors": [
        {"variableId": "treatment", "coding": "sum", "referenceLevel": None}
    ],
    "withinFactors": [
        {"id": "phase", "name": "Phase", "levels": ["fup", "post", "pre"], "columns": {}}
    ],
    "subjectId": "id",
    "covariateIds": [],
    "sumOfSquares": "III",
    "sphericityCorrection": "greenhouse_geisser",
    "postHocAdjustment": "holm",
    "covariateCentering": "grand_mean",
    "homogeneityOfSlopes": "check_and_warn"
})

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: repeated_missing_cell_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "repeated_missing_cell_failure"
rows4 = ["id,treatment,phase,value"]
# Omitting S01's 'fup' timepoint => missing cell in repeated design
sub_idx = 1
for tr in treatments:
    for _ in range(8):
        sid = f"S{sub_idx:02d}"
        for ph in phases:
            if sid == "S01" and ph == "fup":
                continue
            rows4.append(f"{sid},{tr},{ph},10.0")
        sub_idx += 1

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_repeated_missing_cell",
    "sourceType": "synthetic_fixture",
    "title": "Missing Repeated Measurement Cell Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/experiment.repeated.one_within.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for missing cell in repeated ANOVA",
    "allowedUse": "testing",
    "notes": "Generated with omitted timepoint for S01"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c4_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "repeated_missing_cell_failure",
    "name": "Missing Repeated Measurement Cell Failure Case",
    "datasetVersionId": "synthetic_repeated_missing",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "experimental_design",
    "designType": "mixed_design",
    "dataLayout": "long",
    "outcomeIds": ["value"],
    "betweenFactors": [
        {"variableId": "treatment", "coding": "sum", "referenceLevel": None}
    ],
    "withinFactors": [
        {"id": "phase", "name": "Phase", "levels": ["fup", "post", "pre"], "columns": {}}
    ],
    "subjectId": "id",
    "covariateIds": [],
    "sumOfSquares": "III",
    "sphericityCorrection": "greenhouse_geisser",
    "postHocAdjustment": "holm",
    "covariateCentering": "grand_mean",
    "homogeneityOfSlopes": "check_and_warn"
})

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "MISSING_REPEATED_MEASUREMENT",
        "message": "Repeated measures design contains missing cells or incomplete subject observations"
    }
}
write_json(c4_dir / "reference" / "primary" / "normalized-output.json", failure_json)
write_json(c4_dir / "reference" / "secondary" / "normalized-output.json", failure_json)

write_text(c4_dir / "reference" / "primary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "primary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"MISSING_REPEATED_MEASUREMENT"}}', encoding="utf-8")
""")

write_text(c4_dir / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"MISSING_REPEATED_MEASUREMENT"}}', encoding="utf-8")
""")

write_text(c4_dir / "sut" / "run.py", """import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "MISSING_REPEATED_MEASUREMENT", "message": "Repeated measures design contains missing cells or incomplete subject observations"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "experiment.repeated.one_within.v1",
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
            "engine": "afex_car",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "afex_car_sec",
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

make_manifest("repeated_balanced_one_within", "normal_typical", 48, 4)
make_manifest("repeated_sphericity_violation", "legal_complex", 48, 4)
make_manifest("repeated_near_perfect_correlation_boundary", "degenerate_boundary", 48, 4)
make_manifest("repeated_missing_cell_failure", "expected_failure", 47, 4)

print("Setup script for experiment.repeated.one_within.v1 completed!")
