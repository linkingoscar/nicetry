import json
from pathlib import Path
sut_out = Path.cwd() / "sut" / "normalized-output.json"
sut_out.parent.mkdir(parents=True, exist_ok=True)
sut_out.write_text(json.dumps({"status": "failed", "failure": {"reasonCode": "RANK_DEFICIENT_DESIGN", "message": "Factorial design contains empty cells or rank deficient matrix"}}, indent=2), encoding="utf-8")
