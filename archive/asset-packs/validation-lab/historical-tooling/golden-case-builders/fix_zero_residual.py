import json
import hashlib
import yaml
import random
from pathlib import Path

ROOT = Path("C:/Users/example/Documents/nicetry")
CAP_DIR = ROOT / "tests" / "goldens" / "experiment.between.factorial.gaussian.v1" / "cases"

c3_dir = CAP_DIR / "factorial_zero_residual"

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

rows3 = ["score,factorA,factorB"]
zero_means = {("A1", "B1"): 10.0, ("A1", "B2"): 15.0, ("A2", "B1"): 20.0, ("A2", "B2"): 25.0}
rng = random.Random(20260726)
for fa in ["A1", "A2"]:
    for fb in ["B1", "B2"]:
        v = zero_means[(fa, fb)]
        for _ in range(5):
            val = round(v + rng.gauss(0, 0.01), 5)
            rows3.append(f"{val},{fa},{fb}")

c3_csv = c3_dir / "data" / "input.csv"
c3_csv.write_text("\n".join(rows3) + "\n", encoding="utf-8")

c3_source = c3_dir / "data" / "source.json"
source_data = json.loads(c3_source.read_text(encoding="utf-8"))
source_data["sha256"] = sha256(c3_csv)
c3_source.write_text(json.dumps(source_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

manifest_path = c3_dir / "manifest.yaml"
manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
manifest["dataset"][0]["sha256"] = sha256(c3_csv)
manifest_path.write_text(yaml.dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")

print("factorial_zero_residual data updated with 0.01 noise.")
