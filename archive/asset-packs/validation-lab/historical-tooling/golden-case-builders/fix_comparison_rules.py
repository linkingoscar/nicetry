import json
import yaml
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "experiment.between.factorial.gaussian.v1" / "cases"

def flatten_paths(data, prefix=""):
    paths = []
    if isinstance(data, dict):
        for k, v in data.items():
            p = f"{prefix}.{k}" if prefix else k
            paths.extend(flatten_paths(v, p))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            p = f"{prefix}[{i}]"
            paths.extend(flatten_paths(v, p))
    else:
        paths.append((prefix, data))
    return paths

cases = ["factorial_2x2_balanced", "factorial_unbalanced_interaction", "factorial_zero_residual"]

for case_name in cases:
    case_dir = CAP_DIR / case_name
    primary_out = case_dir / "reference" / "primary" / "normalized-output.json"
    if not primary_out.exists():
        continue
    data = json.loads(primary_out.read_text(encoding="utf-8"))
    leafs = flatten_paths(data)
    
    rules = []
    for path, val in leafs:
        if isinstance(val, (float, int)) and not isinstance(val, bool):
            if isinstance(val, int):
                rules.append({"path": path, "comparator": "exact"})
            else:
                rules.append({"path": path, "comparator": "absolute_relative", "absTolerance": 1e-4, "relTolerance": 1e-3})
        else:
            rules.append({"path": path, "comparator": "exact"})
            
    manifest_path = case_dir / "manifest.yaml"
    m = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    m["comparisonRules"] = rules
    manifest_path.write_text(yaml.dump(m, sort_keys=False, allow_unicode=True), encoding="utf-8")

print("Generated precise comparison rules for all cases!")
