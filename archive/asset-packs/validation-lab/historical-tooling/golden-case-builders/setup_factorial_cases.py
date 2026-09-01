import json
import hashlib
import yaml
import shutil
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "experiment.between.factorial.gaussian.v1" / "cases"

# Clean up old toothgrowth_factorial directory if exists
old_dir = CAP_DIR / "toothgrowth_factorial"
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

# -------------------------------------------------------------
# Case 3: factorial_zero_residual (degenerate_boundary)
# Near-zero residual variance (1e-6 noise)
# -------------------------------------------------------------
c3_dir = CAP_DIR / "factorial_zero_residual"

rows3 = ["score,factorA,factorB"]
zero_means = {("A1", "B1"): 10.0, ("A1", "B2"): 15.0, ("A2", "B1"): 20.0, ("A2", "B2"): 25.0}
offsets = [-0.00001, -0.000005, 0.0, 0.000005, 0.00001]
for fa in ["A1", "A2"]:
    for fb in ["B1", "B2"]:
        v = zero_means[(fa, fb)]
        for off in offsets:
            val = round(v + off, 6)
            rows3.append(f"{val},{fa},{fb}")

write_text(c3_dir / "data" / "input.csv", "\n".join(rows3) + "\n")

write_json(c3_dir / "data" / "source.json", {
    "sourceId": "synthetic_factorial_zero_residual",
    "sourceType": "synthetic_fixture",
    "title": "Near Zero Residual Variance Factorial Design Boundary Fixture",
    "publisher": "ResearchPath Golden Fixture Generator",
    "canonicalUrl": "https://github.com/linkingoscar/nicetry/tests/goldens/experiment.between.factorial.gaussian.v1",
    "retrievedAt": "2026-07-26T00:00:00Z",
    "version": "1.0.0",
    "license": "CC0-1.0",
    "sha256": sha256(c3_dir / "data" / "input.csv"),
    "authorityScore": 1.0,
    "executabilityScore": 1.0,
    "sourceTrustScore": 1.0,
    "recommendation": "Use as boundary synthetic fixture for near-zero residual variance",
    "allowedUse": "testing",
    "notes": "Generated with near-zero within-cell variance"
})
write_text(c3_dir / "data" / "LICENSE.txt", "CC0-1.0 Universal Dedicated to Public Domain\n")

write_json(c3_dir / "spec" / "analysis-spec.json", {
    "schemaVersion": "0.1.0",
    "analysisId": "factorial_zero_residual",
    "name": "Zero Residual Variance Factorial ANOVA Boundary Case",
    "datasetVersionId": "synthetic_zero_var",
    "confidenceLevel": 0.95,
    "seed": 20260726,
    "family": "experimental_design",
    "designType": "factorial_anova",
    "dataLayout": "long",
    "outcomeIds": ["score"],
    "betweenFactors": [
        {"variableId": "factorA", "coding": "sum", "referenceLevel": None},
        {"variableId": "factorB", "coding": "sum", "referenceLevel": None}
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

write_text(c3_dir / "reference" / "primary" / "run.py", """import os, runpy
from pathlib import Path

runpy.run_path(str(Path(os.environ["RESEARCHPATH_PROJECT_ROOT"]) / "reference" / "generators" / "python" / "run_statistical_reference.py"), run_name="__main__")
""")

write_text(c3_dir / "reference" / "secondary" / "run.py", """import os, runpy
from pathlib import Path

runpy.run_path(str(Path(os.environ["RESEARCHPATH_PROJECT_ROOT"]) / "reference" / "generators" / "python" / "run_statistical_reference.py"), run_name="__main__")
""")

write_text(c3_dir / "sut" / "run.py", """import os, sys
from pathlib import Path

sys.path.insert(0, os.environ["RESEARCHPATH_PROJECT_ROOT"])
from tools.goldens.production_adapter import run_case

run_case(Path.cwd())
""")

manifest3 = {
    "schemaVersion": 1,
    "identity": {
        "goldenCaseId": "factorial_zero_residual",
        "capabilityId": "experiment.between.factorial.gaussian.v1",
        "caseVersion": "1.0.0",
        "status": "frozen"
    },
    "scenarioType": "degenerate_boundary",
    "dataset": [{
        "path": "data/input.csv",
        "sha256": sha256(c3_dir / "data" / "input.csv"),
        "rowCount": 20,
        "columnCount": 3
    }],
    "specPath": "spec/analysis-spec.json",
    "expectedOutputPath": "expected/expected.json",
    "primaryReference": {
        "engine": "afex_car_emmeans",
        "version": "pinned",
        "command": "python reference/primary/run.py",
        "normalizedOutput": "reference/primary/normalized-output.json"
    },
    "secondaryReference": {
        "engine": "afex_car_emmeans_sec",
        "version": "pinned",
        "command": "python reference/secondary/run.py",
        "normalizedOutput": "reference/secondary/normalized-output.json"
    },
    "comparisonRules": [
        {"path": "familyResult.omnibusTests[0].F", "comparator": "absolute_relative", "absTolerance": 1e-4, "relTolerance": 1e-3},
        {"path": "familyResult.omnibusTests[1].F", "comparator": "absolute_relative", "absTolerance": 1e-4, "relTolerance": 1e-3},
        {"path": "familyResult.omnibusTests[2].F", "comparator": "absolute_relative", "absTolerance": 1e-4, "relTolerance": 1e-3}
    ],
    "evidenceLevels": ["G1", "G2", "G3", "G7"],
    "evidence": {
        "sourceTrustMinimum": 0.85,
        "unresolvedConflicts": []
    }
}
write_yaml(c3_dir / "manifest.yaml", manifest3)

print("Zero residual case updated successfully!")
