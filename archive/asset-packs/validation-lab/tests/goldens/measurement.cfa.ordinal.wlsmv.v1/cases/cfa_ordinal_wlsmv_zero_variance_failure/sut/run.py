import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "ZERO_VARIANCE_INDICATOR", "message": "Item 'x1' has zero variance (only 1 category observed)"}}, indent=2), encoding="utf-8")
