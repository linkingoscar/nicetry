import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "longitudinal.ri_clpm.four_wave.v1" / "cases"

# Remove old case
old_dir = CAP_DIR / "ri_clpm_four_wave_standard"
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

def generate_riclpm_data(n_subjects, ri_var=0.5, missing_prob=0.0):
    rows = ["subject_id,x1,y1,x2,y2,x3,y3,x4,y4"]
    for s in range(1, n_subjects + 1):
        sid = f"S{s:04d}"
        # Trait random intercepts
        ri_x = rng.gauss(0, ri_var ** 0.5)
        ri_y = 0.4 * ri_x + rng.gauss(0, (ri_var * 0.84) ** 0.5)
        
        # Within-person initial states at t=1
        wx1 = rng.gauss(0, 1.0)
        wy1 = rng.gauss(0, 1.0)
        
        # t=2
        wx2 = 0.4 * wx1 + 0.15 * wy1 + rng.gauss(0, 0.8)
        wy2 = 0.2 * wx1 + 0.4 * wy1 + rng.gauss(0, 0.8)
        
        # t=3
        wx3 = 0.4 * wx2 + 0.15 * wy2 + rng.gauss(0, 0.8)
        wy3 = 0.2 * wx2 + 0.4 * wy2 + rng.gauss(0, 0.8)
        
        # t=4
        wx4 = 0.4 * wx3 + 0.15 * wy3 + rng.gauss(0, 0.8)
        wy4 = 0.2 * wx3 + 0.4 * wy3 + rng.gauss(0, 0.8)
        
        # Total observed = RI + wx/wy
        vals = [
            round(ri_x + wx1, 4), round(ri_y + wy1, 4),
            round(ri_x + wx2, 4), round(ri_y + wy2, 4),
            round(ri_x + wx3, 4), round(ri_y + wy3, 4),
            round(ri_x + wx4, 4), round(ri_y + wy4, 4)
        ]
        
        if missing_prob > 0.0:
            str_vals = []
            for idx, v in enumerate(vals):
                # Only inject missingness in wave 3/4
                if idx >= 4 and rng.random() < missing_prob:
                    str_vals.append("")
                else:
                    str_vals.append(str(v))
            rows.append(f"{sid}," + ",".join(str_vals))
        else:
            rows.append(f"{sid}," + ",".join(map(str, vals)))
            
    return rows

spec_dict = {
    "schemaVersion": "0.1.0",
    "analysisId": "ri_clpm_four_wave_001",
    "name": "Four-wave random-intercept cross-lagged panel model",
    "datasetVersionId": "riclpm_fixture_001",
    "confidenceLevel": 0.95,
    "seed": 20260727,
    "family": "longitudinal_model",
    "modelType": "ri_clpm",
    "subjectId": "subject_id",
    "waves": [
        {"wave": "wave1", "timeValue": 0, "variables": {"x": "x1", "y": "y1"}},
        {"wave": "wave2", "timeValue": 1, "variables": {"x": "x2", "y": "y2"}},
        {"wave": "wave3", "timeValue": 2, "variables": {"x": "x3", "y": "y3"}},
        {"wave": "wave4", "timeValue": 3, "variables": {"x": "x4", "y": "y4"}}
    ],
    "estimator": "MLR",
    "missing": "fiml",
    "invarianceLevels": []
}

# -------------------------------------------------------------
# Case 1: ri_clpm_four_wave_typical (normal_typical)
# -------------------------------------------------------------
c1_dir = CAP_DIR / "ri_clpm_four_wave_typical"
rows1 = generate_riclpm_data(250, ri_var=0.5, missing_prob=0.0)

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_ri_clpm_typical",
    "sourceType": "synthetic_fixture",
    "title": "Typical Four-Wave RI-CLPM Longitudinal Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/longitudinal.ri_clpm.four_wave.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for four-wave RI-CLPM",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260727"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c1_dir / "spec" / "analysis-spec.json", spec_dict)

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: ri_clpm_four_wave_unbalanced_missing (legal_complex)
# -------------------------------------------------------------
c2_dir = CAP_DIR / "ri_clpm_four_wave_unbalanced_missing"
rows2 = generate_riclpm_data(300, ri_var=0.6, missing_prob=0.08)

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_ri_clpm_missing",
    "sourceType": "synthetic_fixture",
    "title": "Four-Wave RI-CLPM with FIML Missingness Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/longitudinal.ri_clpm.four_wave.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for RI-CLPM with missing values",
    "allowedUse": "testing",
    "notes": "Generated with 8% missingness in wave 3/4"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c2_dir / "spec" / "analysis-spec.json", spec_dict)

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: ri_clpm_four_wave_zero_ri_var_boundary (degenerate_boundary)
# -------------------------------------------------------------
c3_dir = CAP_DIR / "ri_clpm_four_wave_zero_ri_var_boundary"
rows3 = generate_riclpm_data(200, ri_var=0.01, missing_prob=0.0)

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_ri_clpm_zero_ri_var",
    "sourceType": "synthetic_fixture",
    "title": "Zero Random Intercept Variance Boundary RI-CLPM Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/longitudinal.ri_clpm.four_wave.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for zero RI variance",
    "allowedUse": "testing",
    "notes": "Generated with random intercept variance near zero"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c3_dir / "spec" / "analysis-spec.json", spec_dict)

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: ri_clpm_four_wave_insufficient_waves_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "ri_clpm_four_wave_insufficient_waves_failure"
rows4 = ["subject_id,x1,y1,x2,y2"]
for s in range(1, 10):
    rows4.append(f"S{s:04d},1.0,2.0,1.5,2.5")  # Only 2 waves

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_ri_clpm_failure",
    "sourceType": "synthetic_fixture",
    "title": "Insufficient Waves RI-CLPM Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/longitudinal.ri_clpm.four_wave.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for insufficient waves",
    "allowedUse": "testing",
    "notes": "Generated with 2 waves instead of 4"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c4_dir / "spec" / "analysis-spec.json", spec_dict)

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "INSUFFICIENT_WAVES",
        "message": "Four-wave RI-CLPM requires exactly 4 distinct waves of measurements"
    }
}
write_json(c4_dir / "reference" / "primary" / "normalized-output.json", failure_json)
write_json(c4_dir / "reference" / "secondary" / "normalized-output.json", failure_json)

write_text(c4_dir / "reference" / "primary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "primary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"INSUFFICIENT_WAVES"}}', encoding="utf-8")
""")

write_text(c4_dir / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"INSUFFICIENT_WAVES"}}', encoding="utf-8")
""")

write_text(c4_dir / "sut" / "run.py", """import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "INSUFFICIENT_WAVES", "message": "Four-wave RI-CLPM requires exactly 4 distinct waves of measurements"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "longitudinal.ri_clpm.four_wave.v1",
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
            "engine": "lavaan",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "lavaan_sec",
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

make_manifest("ri_clpm_four_wave_typical", "normal_typical", 250, 9)
make_manifest("ri_clpm_four_wave_unbalanced_missing", "legal_complex", 300, 9)
make_manifest("ri_clpm_four_wave_zero_ri_var_boundary", "degenerate_boundary", 200, 9)
make_manifest("ri_clpm_four_wave_insufficient_waves_failure", "expected_failure", 9, 5)

print("Setup script for longitudinal.ri_clpm.four_wave.v1 completed!")
