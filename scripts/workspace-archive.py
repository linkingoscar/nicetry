from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.workspace_archive import (  # noqa: E402
    create_workspace_backup,
    drill_workspace_backup,
    restore_workspace_backup,
    verify_workspace_backup,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="ResearchPath workspace backup tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="create a verified backup")
    create.add_argument("archive", type=Path)
    create.add_argument("--state-root", type=Path, default=PROJECT_ROOT / ".researchpath/workspace")

    verify = subparsers.add_parser("verify", help="verify archive CRC and SHA-256")
    verify.add_argument("archive", type=Path)

    restore = subparsers.add_parser("restore", help="restore into a new directory")
    restore.add_argument("archive", type=Path)
    restore.add_argument("target", type=Path)

    drill = subparsers.add_parser("drill", help="restore temporarily and check integrity")
    drill.add_argument("archive", type=Path)

    args = parser.parse_args()
    if args.command == "create":
        result = create_workspace_backup(args.state_root, args.archive)
    elif args.command == "verify":
        result = verify_workspace_backup(args.archive)
    elif args.command == "restore":
        result = restore_workspace_backup(args.archive, args.target)
    else:
        result = drill_workspace_backup(args.archive)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
