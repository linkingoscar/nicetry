import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "MISSING_GROUP_VARIABLE", "message": "Group variable 'group' contains fewer than 2 distinct groups"}}, indent=2), encoding="utf-8")
