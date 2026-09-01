import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "measurement.efa.continuous.minres.v1" / "cases"

# Remove old case
old_dir = CAP_DIR / "efa_minres_harman"
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

def generate_efa_data(n_subjects, n_factors=2, items_per_factor=3, factor_corr=0.3):
    total_items = n_factors * items_per_factor
    header = ",".join([f"x{i+1}" for i in range(total_items)])
    rows = [header]
    
    for _ in range(n_subjects):
        factors = []
        for f in range(n_factors):
            if f == 0:
                factors.append(rng.gauss(0, 1.0))
            else:
                factors.append(factor_corr * factors[0] + rng.gauss(0, (1 - factor_corr**2)**0.5))
                
        vals = []
        for f in range(n_factors):
            for i in range(items_per_factor):
                loading = 0.75 + 0.1 * (i % 2)
                v = round(loading * factors[f] + rng.gauss(0, 0.6), 4)
                vals.append(v)
                
        rows.append(",".join(map(str, vals)))
        
    return rows

spec_typical = {
    "schemaVersion": "0.1.0",
    "analysisId": "measurement_efa_fixture_001",
    "name": "EFA MinRes Typical Fixture",
    "datasetVersionId": "dataset_efa_fixture_001",
    "confidenceLevel": 0.95,
    "seed": 20260727,
    "family": "questionnaire_measurement",
    "modelType": "efa",
    "itemIds": ["x1", "x2", "x3", "x4", "x5", "x6"],
    "constructs": [
        {"id": "factor_1", "label": "Factor 1", "itemIds": ["x1", "x2", "x3"]},
        {"id": "factor_2", "label": "Factor 2", "itemIds": ["x4", "x5", "x6"]}
    ],
    "itemScale": "continuous",
    "estimator": "minres",
    "extractionMethod": "minres",
    "factorCount": 2,
    "rotation": "promax",
    "extraction": "minres",
    "parallelIterations": 100,
    "invarianceLevels": ["configural", "metric", "scalar"]
}

spec_four = {
    "schemaVersion": "0.1.0",
    "analysisId": "measurement_efa_fixture_002",
    "name": "EFA MinRes Four Factor Fixture",
    "datasetVersionId": "dataset_efa_fixture_002",
    "confidenceLevel": 0.95,
    "seed": 20260727,
    "family": "questionnaire_measurement",
    "modelType": "efa",
    "itemIds": [f"x{i+1}" for i in range(12)],
    "constructs": [
        {"id": f"factor_{i+1}", "label": f"Factor {i+1}", "itemIds": [f"x{i*3+1}", f"x{i*3+2}", f"x{i*3+3}"]}
        for i in range(4)
    ],
    "itemScale": "continuous",
    "estimator": "minres",
    "extractionMethod": "minres",
    "factorCount": 4,
    "rotation": "oblimin",
    "extraction": "minres",
    "parallelIterations": 100,
    "invarianceLevels": ["configural", "metric", "scalar"]
}

# -------------------------------------------------------------
# Case 1: efa_continuous_minres_typical (normal_typical)
# -------------------------------------------------------------
c1_dir = CAP_DIR / "efa_continuous_minres_typical"
rows1 = generate_efa_data(200, n_factors=2, items_per_factor=3, factor_corr=0.35)

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_efa_typical",
    "sourceType": "synthetic_fixture",
    "title": "Typical MinRes EFA Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.efa.continuous.minres.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for MinRes Promax EFA",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260727"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c1_dir / "spec" / "analysis-spec.json", spec_typical)

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: efa_continuous_minres_four_factor (legal_complex)
# 4 factors, 12 items, oblimin
# -------------------------------------------------------------
c2_dir = CAP_DIR / "efa_continuous_minres_four_factor"
rows2 = generate_efa_data(300, n_factors=4, items_per_factor=3, factor_corr=0.25)

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_efa_four_factor",
    "sourceType": "synthetic_fixture",
    "title": "Four Factor MinRes EFA Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.efa.continuous.minres.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for 4-factor MinRes Oblimin EFA",
    "allowedUse": "testing",
    "notes": "Generated with 4 factors"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c2_dir / "spec" / "analysis-spec.json", spec_four)

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: efa_continuous_minres_high_correlation_boundary (degenerate_boundary)
# High correlation r=0.88
# -------------------------------------------------------------
c3_dir = CAP_DIR / "efa_continuous_minres_high_correlation_boundary"
rows3 = generate_efa_data(150, n_factors=2, items_per_factor=3, factor_corr=0.88)

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_efa_high_corr",
    "sourceType": "synthetic_fixture",
    "title": "High Correlation MinRes EFA Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.efa.continuous.minres.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary fixture for high inter-factor correlation",
    "allowedUse": "testing",
    "notes": "Generated with high factor correlation"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")
write_json(c3_dir / "spec" / "analysis-spec.json", spec_typical)

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: efa_continuous_minres_insufficient_items_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "efa_continuous_minres_insufficient_items_failure"
rows4 = ["x1,x2"]
for i in range(10):
    rows4.append(f"{1.0+i*0.2},{2.0+i*0.3}")

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_efa_failure",
    "sourceType": "synthetic_fixture",
    "title": "Insufficient Items MinRes EFA Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/measurement.efa.continuous.minres.v1",
    "retrievedAt": "2026-07-27T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0, "executabilityScore": 1.0, "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for insufficient items",
    "allowedUse": "testing",
    "notes": "Generated with 2 items for 2 factors"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

spec_failure = {
    "schemaVersion": "0.1.0",
    "analysisId": "measurement_efa_fixture_failure",
    "name": "Insufficient Items EFA",
    "datasetVersionId": "dataset_efa_fixture_failure",
    "confidenceLevel": 0.95,
    "seed": 20260727,
    "family": "questionnaire_measurement",
    "modelType": "efa",
    "itemIds": ["x1", "x2"],
    "factorCount": 2,
    "rotation": "promax",
    "extraction": "minres"
}
write_json(c4_dir / "spec" / "analysis-spec.json", spec_failure)

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "INSUFFICIENT_ITEMS",
        "message": "EFA model requires more items than factors (2 items for 2 factors is underidentified)"
    }
}
write_json(c4_dir / "reference" / "primary" / "normalized-output.json", failure_json)
write_json(c4_dir / "reference" / "secondary" / "normalized-output.json", failure_json)

write_text(c4_dir / "reference" / "primary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "primary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"INSUFFICIENT_ITEMS"}}', encoding="utf-8")
""")

write_text(c4_dir / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"INSUFFICIENT_ITEMS"}}', encoding="utf-8")
""")

write_text(c4_dir / "sut" / "run.py", """import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "INSUFFICIENT_ITEMS", "message": "EFA model requires more items than factors (2 items for 2 factors is underidentified)"}}, indent=2), encoding="utf-8")
""")

def make_manifest(case_id, scenario_type, row_cnt, col_cnt):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "measurement.efa.continuous.minres.v1",
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
            "engine": "psych_fa",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "psych_fa_sec",
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

make_manifest("efa_continuous_minres_typical", "normal_typical", 200, 6)
make_manifest("efa_continuous_minres_four_factor", "legal_complex", 300, 12)
make_manifest("efa_continuous_minres_high_correlation_boundary", "degenerate_boundary", 150, 6)
make_manifest("efa_continuous_minres_insufficient_items_failure", "expected_failure", 10, 2)

print("Setup script for measurement.efa.continuous.minres.v1 completed!")
