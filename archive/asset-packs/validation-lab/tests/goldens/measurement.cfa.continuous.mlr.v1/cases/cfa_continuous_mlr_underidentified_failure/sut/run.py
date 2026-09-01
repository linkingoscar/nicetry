import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "UNDERIDENTIFIED_MODEL", "message": "CFA model is underidentified; requires at least 3 indicators per factor"}}, indent=2), encoding="utf-8")
