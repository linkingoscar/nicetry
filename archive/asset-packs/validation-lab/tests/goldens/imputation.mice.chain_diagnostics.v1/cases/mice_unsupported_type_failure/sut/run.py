import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "UNSUPPORTED_VARIABLE_TYPE", "message": "Column x1 contains non-numeric text values unsupported by PMM"}}, indent=2), encoding="utf-8")
