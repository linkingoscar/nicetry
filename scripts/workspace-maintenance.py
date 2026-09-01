from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.services.workspace_maintenance import (  # noqa: E402
    WorkspaceMaintenanceError,
    audit_workspace,
    clean_audited_orphan_datasets,
)


def _write(document: dict[str, object], output: Path | None) -> None:
    rendered = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if output is None:
        print(rendered, end="")
        return
    target = output if output.is_absolute() else ROOT / output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    print(f"Wrote {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and safely clean ResearchPath state.")
    parser.add_argument(
        "--state-root",
        type=Path,
        default=ROOT / ".researchpath" / "workspace",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--output", type=Path)
    clean_parser = subparsers.add_parser("clean-orphan-datasets")
    clean_parser.add_argument("--audit", type=Path, required=True)
    clean_parser.add_argument("--backup", type=Path, required=True)
    clean_parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "audit":
            result = audit_workspace(args.state_root)
        else:
            result = clean_audited_orphan_datasets(args.state_root, args.audit, args.backup)
        _write(result, args.output)
    except (OSError, json.JSONDecodeError, WorkspaceMaintenanceError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
