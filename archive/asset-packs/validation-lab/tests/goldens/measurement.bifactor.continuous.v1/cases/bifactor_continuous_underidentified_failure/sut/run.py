import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "UNDERIDENTIFIED_SPECIFIC_FACTOR", "message": "Bifactor model requires at least 2 items per specific factor and 3 total specific items"}}, indent=2), encoding="utf-8")
