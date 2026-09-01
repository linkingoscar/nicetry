import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "MISSING_PERSON_VARIABLE", "message": "ESM diary AR(1) model requires at least 2 distinct subjects"}}, indent=2), encoding="utf-8")
