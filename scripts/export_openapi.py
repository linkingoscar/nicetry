from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the deterministic FastAPI OpenAPI document"
    )
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    api_root = project_root / "apps" / "api"
    sys.path.insert(0, str(api_root))

    from app.main import create_app

    schema = create_app().openapi()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
