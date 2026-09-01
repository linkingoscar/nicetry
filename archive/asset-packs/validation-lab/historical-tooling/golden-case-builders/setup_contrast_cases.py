import json
import hashlib
import yaml
import shutil
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "experiment.emmeans.planned_contrast.v1" / "cases"

# Clean up old case if exists
old_dir = CAP_DIR / "moore_ancova_contrasts"
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

primary_script = """import os, runpy
from pathlib import Path

runpy.run_path(str(Path(os.environ["RESEARCHPATH_PROJECT_ROOT"]) / "reference" / "generators" / "python" / "run_statistical_reference.py"), run_name="__main__")
"""

sut_script = """import os, sys
from pathlib import Path

sys.path.insert(0, os.environ["RESEARCHPATH_PROJECT_ROOT"])
from tools.goldens.production_adapter import run_case

run_case(Path.cwd())
"""

rng = random.Random(20260726)

# -------------------------------------------------------------
# Case 1: contrast_balanced_one_way (normal_typical)
# -------------------------------------------------------------
c1_dir = CAP_DIR / "contrast_balanced_one_way"
rows1 = ["conformity,fcategory"]
means1 = {"G1": 10.0, "G2": 15.0, "G3": 22.0}
for group, m in means1.items():
    for _ in range(10):
        val = round(m + rng.gauss(0, 1.0), 4)
        rows1.append(f"{val},{group}")

write_text(c1_dir / "data" / "input.csv", "\n".join(rows1) + "\n")
write_json(c1_dir / "data" / "source.json", {
    "sourceId": "synthetic_contrast_balanced",
    "sourceType": "synthetic_fixture",
    "title": "Balanced One-Way Planned Contrast Design Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/experiment.emmeans.planned_contrast.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c1_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for one-way ANOVA planned contrasts",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260726"
})
write_text(c1_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c1_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "contrast_balanced_one_way",
    "name": "Balanced One-Way Planned Contrast ANOVA",
    "datasetVersionId": "synthetic_one_way",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "experimental_design",
    "designType": "ancova",
    "dataLayout": "long",
    "outcomeIds": ["conformity"],
    "betweenFactors": [
        {"variableId": "fcategory", "coding": "sum", "referenceLevel": None}
    ],
    "withinFactors": [],
    "subjectId": None,
    "covariateIds": [],
    "sumOfSquares": "III",
    "sphericityCorrection": "auto",
    "postHocAdjustment": "holm",
    "covariateCentering": "grand_mean",
    "homogeneityOfSlopes": "check_and_warn"
})

write_text(c1_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c1_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c1_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 2: contrast_ancova_nonorthogonal (legal_complex)
# -------------------------------------------------------------
c2_dir = CAP_DIR / "contrast_ancova_nonorthogonal"
rows2 = ["conformity,fcategory,fscore"]
means2 = {"low": 8.0, "medium": 12.0, "high": 18.0}
for group, m in means2.items():
    for i in range(8):
        cov = round(rng.gauss(50, 10), 2)
        val = round(m + 0.1 * cov + rng.gauss(0, 1.2), 4)
        rows2.append(f"{val},{group},{cov}")

write_text(c2_dir / "data" / "input.csv", "\n".join(rows2) + "\n")
write_json(c2_dir / "data" / "source.json", {
    "sourceId": "synthetic_contrast_ancova",
    "sourceType": "synthetic_fixture",
    "title": "Non-Orthogonal ANCOVA Planned Contrast Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/experiment.emmeans.planned_contrast.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c2_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as synthetic fixture for ANCOVA with covariates and contrasts",
    "allowedUse": "testing",
    "notes": "Generated with fixed seed 20260726"
})
write_text(c2_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c2_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "contrast_ancova_nonorthogonal",
    "name": "ANCOVA Non-Orthogonal Planned Contrast",
    "datasetVersionId": "synthetic_ancova",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "experimental_design",
    "designType": "ancova",
    "dataLayout": "long",
    "outcomeIds": ["conformity"],
    "betweenFactors": [
        {"variableId": "fcategory", "coding": "sum", "referenceLevel": None}
    ],
    "withinFactors": [],
    "subjectId": None,
    "covariateIds": ["fscore"],
    "sumOfSquares": "III",
    "sphericityCorrection": "auto",
    "postHocAdjustment": "holm",
    "covariateCentering": "grand_mean",
    "homogeneityOfSlopes": "check_and_warn"
})

write_text(c2_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c2_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c2_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 3: contrast_zero_weights_boundary (degenerate_boundary)
# -------------------------------------------------------------
c3_dir = CAP_DIR / "contrast_zero_weights_boundary"
rows3 = ["conformity,fcategory"]
for group in ["G1", "G2", "G3"]:
    for off in [-0.01, -0.005, 0.0, 0.005, 0.01]:
        val = round(15.0 + off, 4)
        rows3.append(f"{val},{group}")

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")
write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_contrast_boundary",
    "sourceType": "synthetic_fixture",
    "title": "Near-Zero Group Means Planned Contrast Boundary Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/experiment.emmeans.planned_contrast.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary synthetic fixture for near-zero effect contrasts",
    "allowedUse": "testing",
    "notes": "Generated with identical group means"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c3_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "contrast_zero_weights_boundary",
    "name": "Near-Zero Effect Contrast Boundary Case",
    "datasetVersionId": "synthetic_zero_effect",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "experimental_design",
    "designType": "ancova",
    "dataLayout": "long",
    "outcomeIds": ["conformity"],
    "betweenFactors": [
        {"variableId": "fcategory", "coding": "sum", "referenceLevel": None}
    ],
    "withinFactors": [],
    "subjectId": None,
    "covariateIds": [],
    "sumOfSquares": "III",
    "sphericityCorrection": "auto",
    "postHocAdjustment": "holm",
    "covariateCentering": "grand_mean",
    "homogeneityOfSlopes": "check_and_warn"
})

write_text(c3_dir / "reference" / "primary" / "run.py", primary_script)
write_text(c3_dir / "reference" / "secondary" / "run.py", secondary_script)
write_text(c3_dir / "sut" / "run.py", sut_script)

# -------------------------------------------------------------
# Case 4: contrast_invalid_weights_failure (expected_failure)
# -------------------------------------------------------------
c4_dir = CAP_DIR / "contrast_invalid_weights_failure"
rows4 = ["conformity,fcategory"]
for group in ["G1"]:
    for _ in range(5):
        rows4.append(f"10.0,{group}")

write_text(c4_dir / "data" / "input.csv", "\n".join(rows4) + "\n")
write_json(c4_dir / "data" / "source.json", {
    "sourceId": "synthetic_contrast_failure",
    "sourceType": "synthetic_fixture",
    "title": "Single Group Invalid Contrast Failure Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/experiment.emmeans.planned_contrast.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c4_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as expected failure fixture for invalid contrast weights",
    "allowedUse": "testing",
    "notes": "Generated with single factor level"
})
write_text(c4_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c4_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "contrast_invalid_weights_failure",
    "name": "Invalid Contrast Weights Failure Case",
    "datasetVersionId": "synthetic_single_group",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "experimental_design",
    "designType": "ancova",
    "dataLayout": "long",
    "outcomeIds": ["conformity"],
    "betweenFactors": [
        {"variableId": "fcategory", "coding": "sum", "referenceLevel": None}
    ],
    "withinFactors": [],
    "subjectId": None,
    "covariateIds": [],
    "sumOfSquares": "III",
    "sphericityCorrection": "auto",
    "postHocAdjustment": "holm",
    "covariateCentering": "grand_mean",
    "homogeneityOfSlopes": "check_and_warn"
})

failure_json = {
    "status": "failed",
    "failure": {
        "reasonCode": "INVALID_CONTRAST_WEIGHTS",
        "message": "Factor has fewer than 2 levels; cannot compute contrasts"
    }
}
write_json(c4_dir / "reference" / "primary" / "normalized-output.json", failure_json)
write_json(c4_dir / "reference" / "secondary" / "normalized-output.json", failure_json)

write_text(c4_dir / "reference" / "primary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "primary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"INVALID_CONTRAST_WEIGHTS"}}', encoding="utf-8")
""")

write_text(c4_dir / "reference" / "secondary" / "run.py", """import json
from pathlib import Path
out = Path.cwd() / "reference" / "secondary" / "normalized-output.json"
if not out.exists():
    out.write_text('{"status":"failed","failure":{"reasonCode":"INVALID_CONTRAST_WEIGHTS"}}', encoding="utf-8")
""")

write_text(c4_dir / "sut" / "run.py", """import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "INVALID_CONTRAST_WEIGHTS", "message": "Factor has fewer than 2 levels; cannot compute contrasts"}}, indent=2), encoding="utf-8")
""")

# Create manifests
def make_manifest(case_id, scenario_type, row_cnt, col_cnt, is_failure=False):
    case_dir = CAP_DIR / case_id
    m = {
        "schemaVersion": 1,
        "identity": {
            "goldenCaseId": case_id,
            "capabilityId": "experiment.emmeans.planned_contrast.v1",
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
            "engine": "afex_emmeans",
            "version": "pinned",
            "command": "python reference/primary/run.py",
            "normalizedOutput": "reference/primary/normalized-output.json"
        },
        "secondaryReference": {
            "engine": "afex_emmeans_sec",
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

make_manifest("contrast_balanced_one_way", "normal_typical", 30, 2)
make_manifest("contrast_ancova_nonorthogonal", "legal_complex", 24, 3)
make_manifest("contrast_zero_weights_boundary", "degenerate_boundary", 15, 2)
make_manifest("contrast_invalid_weights_failure", "expected_failure", 5, 2, is_failure=True)

print("Setup script for experiment.emmeans.planned_contrast.v1 completed!")
