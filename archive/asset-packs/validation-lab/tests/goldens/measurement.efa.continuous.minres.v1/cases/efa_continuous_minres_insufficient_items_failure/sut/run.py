import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "INSUFFICIENT_ITEMS", "message": "EFA model requires more items than factors (2 items for 2 factors is underidentified)"}}, indent=2), encoding="utf-8")
