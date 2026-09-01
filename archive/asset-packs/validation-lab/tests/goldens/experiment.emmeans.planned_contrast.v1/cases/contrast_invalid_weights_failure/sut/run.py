import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "INVALID_CONTRAST_WEIGHTS", "message": "Factor has fewer than 2 levels; cannot compute contrasts"}}, indent=2), encoding="utf-8")
