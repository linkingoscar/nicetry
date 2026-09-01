"""A fresh, disposable API workspace for first-use browser verification."""
from dataclasses import replace
from pathlib import Path
import sys

import uvicorn

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "apps" / "api"))

from app.main import create_app  # noqa: E402
from app.settings import get_settings  # noqa: E402

state_root = Path(sys.argv[1]).resolve()
if not state_root.is_relative_to(root / "output" / "playwright"):
    raise ValueError("Isolated E2E workspace must be below output/playwright")
settings = replace(get_settings(), state_root=state_root, session_token=sys.argv[3], r_parallel_workers=1)
uvicorn.run(create_app(settings), host="127.0.0.1", port=int(sys.argv[2]))
