import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "imputation.mice.chain_diagnostics.v1" / "cases"

# Clean up old case if exists
old_dir = CAP_DIR / "mice_chain_diagnostics"
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

# -------------------------------------------------------------
# Case 1: mice_stable_chains (normal_typical)
# -------------------------------------------------------------
c1_dir = CAP_DIR / "mice_stable_chains"
csv1 = """x1,x2,interaction
1.0,2.0,2.0
2.0,,
,4.0,
4.0,5.0,20.0
5.0,6.0,30.0
6.0,,
,8.0,
8.0,9.0,72.0
9.0,10.0,90.0
10.0,11.0,110.0
"""
write_text(c1_dir / "data" / "input.csv", csv1)
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_mice_stable",
    "sourceType": "synthetic_fixture",
    "title": "MICE Stable Chain Diagnostics Synthetic Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/imputation.mice.chain_diagnostics.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for MICE chain diagnostics",
    "allowedUse": "testing",
    "notes": "Generated with partial missingness in x1 and x2"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c1_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "mice_stable_chains",
    "name": "MICE Stable Chain Diagnostics",
    "datasetVersionId": "synthetic_mice_stable",
    "confidenceLevel": 0.95,
    "seed": 42,
    "family": "multiple_imputation",
    "method": "mice_fcs",
    "imputations": 5,
    "iterations": 10,
    "variables": [
        {"variableId": "x1", "method": "pmm", "predictorIds": ["x2"]},
        {"variableId": "x2", "method": "pmm", "predictorIds": ["x1"]}
    ],
    "passiveRules": [
        {"targetVariableId": "interaction", "expression": "x1 * x2"}
    ],
    "pooling": "none",
    "diagnostics": ["trace", "distribution"]
})

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: mice_multivariate_passive (legal_complex)
# -------------------------------------------------------------
c2_dir = CAP_DIR / "mice_multivariate_passive"
csv2 = """x1,x2,interaction
1.5,3.0,4.5
2.5,,
,5.0,
4.5,6.0,27.0
,7.5,
6.5,8.0,52.0
7.5,,
8.5,10.0,85.0
,11.0,
10.5,12.0,126.0
"""
write_text(c2_dir / "data" / "input.csv", csv2)
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_mice_multivariate",
    "sourceType": "synthetic_fixture",
    "title": "MICE Multivariate Passive Expression Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/imputation.mice.chain_diagnostics.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for multivariate missingness and passive rules",
    "allowedUse": "testing",
    "notes": "Generated with complex multivariate missingness"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c2_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "mice_multivariate_passive",
    "name": "MICE Multivariate Passive Diagnostics",
    "datasetVersionId": "synthetic_mice_multivariate",
    "confidenceLevel": 0.95,
    "seed": 42,
    "family": "multiple_imputation",
    "method": "mice_fcs",
    "imputations": 5,
    "iterations": 10,
    "variables": [
        {"variableId": "x1", "method": "pmm", "predictorIds": ["x2"]},
        {"variableId": "x2", "method": "pmm", "predictorIds": ["x1"]}
    ],
    "passiveRules": [
        {"targetVariableId": "interaction", "expression": "x1 * x2"}
    ],
    "pooling": "none",
    "diagnostics": ["trace", "distribution"]
})

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: mice_no_missing_boundary (degenerate_boundary)
# -------------------------------------------------------------
c3_dir = CAP_DIR / "mice_no_missing_boundary"
csv3 = """x1,x2,interaction
1.0,2.0,2.0
2.0,3.0,6.0
3.0,4.0,12.0
4.0,5.0,20.0
5.0,6.0,30.0
6.0,7.0,42.0
7.0,8.0,56.0
8.0,9.0,72.0
9.0,10.0,90.0
10.0,11.0,110.0
"""
write_text(c3_dir / "data" / "input.csv", csv3)
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_mice_no_missing",
    "sourceType": "synthetic_fixture",
    "title": "MICE Zero Missing Data Boundary Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/imputation.mice.chain_diagnostics.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for zero missing data",
    "allowedUse": "testing",
    "notes": "Generated with complete data"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c3_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "mice_no_missing_boundary",
    "name": "Zero Missing Data Boundary Case",
    "datasetVersionId": "synthetic_no_missing",
    "confidenceLevel": 0.95,
    "seed": 42,
    "family": "multiple_imputation",
    "method": "mice_fcs",
    "imputations": 5,
    "iterations": 10,
    "variables": [
        {"variableId": "x1", "method": "pmm", "predictorIds": ["x2"]},
        {"variableId": "x2", "method": "pmm", "predictorIds": ["x1"]}
    ],
    "passiveRules": [
        {"targetVariableId": "interaction", "expression": "x1 * x2"}
    ],
    "pooling": "none",
    "diagnostics": ["trace", "distribution"]
})

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: mice_unsupported_type_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "mice_unsupported_type_failure"
csv4 = """x1,x2,interaction
INVALID_TEXT,2.0,2.0
TEXT_DATA,,
,4.0,
"""
write_text(c4_dir / "data" / "input.csv", csv4)
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_mice_failure",
    "sourceType": "synthetic_fixture",
    "title": "Unsupported Variable Type MICE Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/imputation.mice.chain_diagnostics.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for unsupported text column in MICE",
    "allowedUse": "testing",
    "notes": "Generated with text in numeric column"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c4_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "mice_unsupported_type_failure",
    "name": "Unsupported Variable Type Failure Case",
    "datasetVersionId": "synthetic_invalid_text",
    "confidenceLevel": 0.95,
    "seed": 42,
    "family": "multiple_imputation",
    "method": "mice_fcs",
    "imputations": 5,
    "iterations": 10,
    "variables": [
        {"variableId": "x1", "method": "pmm", "predictorIds": ["x2"]},
        {"variableId": "x2", "method": "pmm", "predictorIds": ["x1"]}
    ],
    "passiveRules": [
        {"targetVariableId": "interaction", "expression": "x1 * x2"}
    ],
    "pooling": "none",
    "diagnostics": ["trace", "distribution"]
})

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "UNSUPPORTED_VARIABLE_TYPE",
        "message": "Column x1 contains non-numeric text values unsupported by PMM"
    }
}
write_json(c4_dir / "reference" / "primary" / "normalized-output.json", failure_json)
write_json(c4_dir / "reference" / "secondary" / "normalized-output.json", failure_json)

write_text(c4_dir / "reference" / "primary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "primary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"UNSUPPORTED_VARIABLE_TYPE"}}', encoding="utf-8")
""")

write_text(c4_dir / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"UNSUPPORTED_VARIABLE_TYPE"}}', encoding="utf-8")
""")

write_text(c4_dir / "sut" / "run.py", """import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "UNSUPPORTED_VARIABLE_TYPE", "message": "Column x1 contains non-numeric text values unsupported by PMM"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "imputation.mice.chain_diagnostics.v1",
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
            "engine": "mice",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "mice_sec",
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

make_manifest("mice_stable_chains", "normal_typical", 10, 3)
make_manifest("mice_multivariate_passive", "legal_complex", 10, 3)
make_manifest("mice_no_missing_boundary", "degenerate_boundary", 10, 3)
make_manifest("mice_unsupported_type_failure", "expected_failure", 3, 3)

print("Setup script for imputation.mice.chain_diagnostics.v1 completed!")
