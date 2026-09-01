import json
import yaml
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "measurement.efa.continuous.minres.v1" / "cases"

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

cases = ["efa_continuous_minres_typical", "efa_continuous_minres_four_factor", "efa_continuous_minres_high_correlation_boundary"]

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
                rules.append({"path": path, "comparator": "absolute_relative", "absTolerance": 1e-3, "relTolerance": 1e-2})
        else:
            rules.append({"path": path, "comparator": "exact"})
            
    manifest_path = case_dir / "manifest.yaml"
    m = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    m["comparisonRules"] = rules
    manifest_path.write_text(yaml.dump(m, sort_keys=False, allow_unicode=True), encoding="utf-8")

c4_dir = CAP_DIR / "efa_continuous_minres_insufficient_items_failure"
m4_path = c4_dir / "manifest.yaml"
m4 = yaml.safe_load(m4_path.read_text(encoding="utf-8"))
m4["comparisonRules"] = [
    {"path": "status", "comparator": "exact"},
    {"path": "failure.reasonCode", "comparator": "exact"},
    {"path": "failure.message", "comparator": "exact"}
]
m4_path.write_text(yaml.dump(m4, sort_keys=False, allow_unicode=True), encoding="utf-8")

print("Comparison rules for measurement.efa.continuous.minres.v1 generated!")
