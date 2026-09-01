import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "INSUFFICIENT_WAVES", "message": "Four-wave RI-CLPM requires exactly 4 distinct waves of measurements"}}, indent=2), encoding="utf-8")
