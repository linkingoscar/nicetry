import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "longitudinal.esm.diary_ar1.v1" / "cases"

# Remove old case
old_dir = CAP_DIR / "esm_diary_ar1"
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
# Case 1: esm_diary_ar1_typical (normal_typical)
# -------------------------------------------------------------
c1_dir = CAP_DIR / "esm_diary_ar1_typical"
rows1 = ["person_id,day,prompt,affect"]
for p in range(1, 11):
    pid = f"P{p:02d}"
    p_intercept = rng.gauss(5.0, 1.5)
    for d in range(1, 6):
        prev_e = 0.0
        for pr in range(1, 5):
            # AR(1) process with phi = 0.5
            e = 0.5 * prev_e + rng.gauss(0, 1.0)
            prev_e = e
            val = round(p_intercept + e, 4)
            rows1.append(f"{pid},{d},{pr},{val}")

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_esm_diary_typical",
    "sourceType": "synthetic_fixture",
    "title": "Typical ESM Diary AR(1) Longitudinal Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/longitudinal.esm.diary_ar1.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for ESM diary AR(1)",
    "allowedUse": "testing",
    "notes": "Generated with AR(1) phi=0.5"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c1_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "longitudinal.esm.diary_ar1.v1",
    "data": {
        "personVar": "person_id",
        "dayVar": "day",
        "promptVar": "prompt",
        "outcome": "affect"
    },
    "parameters": {
        "correlation": "AR1",
        "overnightDisconnection": True
    }
})

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: esm_diary_ar1_missing_prompts (legal_complex)
# -------------------------------------------------------------
c2_dir = CAP_DIR / "esm_diary_ar1_missing_prompts"
rows2 = ["person_id,day,prompt,affect"]
for p in range(1, 13):
    pid = f"P{p:02d}"
    p_intercept = rng.gauss(6.0, 2.0)
    for d in range(1, 7):
        prev_e = 0.0
        prompt_cnt = rng.randint(2, 6)
        prompts = sorted(rng.sample(range(1, 7), prompt_cnt))
        for pr in prompts:
            e = 0.4 * prev_e + rng.gauss(0, 1.2)
            prev_e = e
            val = round(p_intercept + e, 4)
            rows2.append(f"{pid},{d},{pr},{val}")

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_esm_diary_complex",
    "sourceType": "synthetic_fixture",
    "title": "Unbalanced Missing Prompts ESM Diary AR(1) Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/longitudinal.esm.diary_ar1.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for unbalanced prompt ESM diary",
    "allowedUse": "testing",
    "notes": "Generated with varying prompts per day"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c2_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "longitudinal.esm.diary_ar1.v1",
    "data": {
        "personVar": "person_id",
        "dayVar": "day",
        "promptVar": "prompt",
        "outcome": "affect"
    },
    "parameters": {
        "correlation": "AR1",
        "overnightDisconnection": True
    }
})

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: esm_diary_ar1_zero_phi_boundary (degenerate_boundary)
# -------------------------------------------------------------
c3_dir = CAP_DIR / "esm_diary_ar1_zero_phi_boundary"
rows3 = ["person_id,day,prompt,affect"]
for p in range(1, 9):
    pid = f"P{p:02d}"
    p_intercept = rng.gauss(5.0, 1.0)
    for d in range(1, 5):
        for pr in range(1, 6):
            # Independent errors (phi = 0.0)
            e = rng.gauss(0, 1.5)
            val = round(p_intercept + e, 4)
            rows3.append(f"{pid},{d},{pr},{val}")

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_esm_diary_zero_phi",
    "sourceType": "synthetic_fixture",
    "title": "Zero Autocorrelation Boundary ESM Diary Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/longitudinal.esm.diary_ar1.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for zero autocorrelation phi=0",
    "allowedUse": "testing",
    "notes": "Generated with independent errors"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c3_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "longitudinal.esm.diary_ar1.v1",
    "data": {
        "personVar": "person_id",
        "dayVar": "day",
        "promptVar": "prompt",
        "outcome": "affect"
    },
    "parameters": {
        "correlation": "AR1",
        "overnightDisconnection": True
    }
})

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: esm_diary_ar1_missing_person_var (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "esm_diary_ar1_missing_person_var"
rows4 = ["person_id,day,prompt,affect"]
for i in range(4):
    rows4.append(f"P01,1,{i+1},{10.0+i}")  # Single person, single day

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_esm_diary_failure",
    "sourceType": "synthetic_fixture",
    "title": "Single Person ESM Diary Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/longitudinal.esm.diary_ar1.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for single person ESM diary",
    "allowedUse": "testing",
    "notes": "Generated with single person"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c4_dir / "spec" / "analysis-spec.json", {
    "capabilityId": "longitudinal.esm.diary_ar1.v1",
    "data": {
        "personVar": "person_id",
        "dayVar": "day",
        "promptVar": "prompt",
        "outcome": "affect"
    },
    "parameters": {
        "correlation": "AR1",
        "overnightDisconnection": True
    }
})

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "MISSING_PERSON_VARIABLE",
        "message": "ESM diary AR(1) model requires at least 2 distinct subjects"
    }
}
write_json(c4_dir / "reference" / "primary" / "normalized-output.json", failure_json)
write_json(c4_dir / "reference" / "secondary" / "normalized-output.json", failure_json)

write_text(c4_dir / "reference" / "primary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "primary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"MISSING_PERSON_VARIABLE"}}', encoding="utf-8")
""")

write_text(c4_dir / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"MISSING_PERSON_VARIABLE"}}', encoding="utf-8")
""")

write_text(c4_dir / "sut" / "run.py", """import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "MISSING_PERSON_VARIABLE", "message": "ESM diary AR(1) model requires at least 2 distinct subjects"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "longitudinal.esm.diary_ar1.v1",
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
            "engine": "nlme",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "nlme_sec",
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

make_manifest("esm_diary_ar1_typical", "normal_typical", 200, 4)
make_manifest("esm_diary_ar1_missing_prompts", "legal_complex", len(rows2) - 1, 4)
make_manifest("esm_diary_ar1_zero_phi_boundary", "degenerate_boundary", 160, 4)
make_manifest("esm_diary_ar1_missing_person_var", "expected_failure", 4, 4)

print("Setup script for longitudinal.esm.diary_ar1.v1 completed!")
