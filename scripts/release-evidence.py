from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_FILES = (
    "apps/api/requirements.lock",
    "package-lock.json",
    "renv.lock",
    "specs/openapi.json",
    "docs/debt-register.json",
    "output/performance/r-runtime-baseline.json",
)


def command_output(*arguments: str) -> str | None:
    try:
        result = subprocess.run(
            arguments,
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect(
    test_status: str,
    *,
    mode: str = "Release",
    run_id: str | None = None,
    duration_seconds: float | None = None,
    required_steps: list[str] | None = None,
    completed_steps: list[str] | None = None,
    skipped_steps: list[str] | None = None,
) -> dict[str, object]:
    required = sorted(set(required_steps or []))
    completed = sorted(set(completed_steps or []))
    skipped = sorted(set(skipped_steps or []))
    normalized_status = "incomplete" if test_status == "passed" and skipped else test_status
    missing_required = sorted(set(required) - set(completed))
    rscript = ROOT / ".runtime" / "R" / "bin" / "Rscript.exe"
    hashes = {
        relative: sha256(ROOT / relative)
        for relative in EVIDENCE_FILES
        if (ROOT / relative).is_file()
    }
    git_status = command_output("git", "status", "--porcelain")
    return {
        "schemaVersion": "1.0.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "testStatus": normalized_status,
        "mode": mode,
        "runId": run_id,
        "durationSeconds": duration_seconds,
        "evidenceComplete": normalized_status == "passed" and not missing_required and not skipped,
        "steps": {
            "required": required,
            "completed": completed,
            "skipped": skipped,
            "missing": missing_required,
        },
        "source": {
            "commit": command_output("git", "rev-parse", "HEAD"),
            "branch": command_output("git", "branch", "--show-current"),
            "dirty": bool(git_status),
        },
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "node": command_output("node", "--version"),
            "npm": command_output(
                "npm.cmd" if platform.system() == "Windows" else "npm", "--version"
            ),
            "r": command_output(str(rscript), "--version") if rscript.is_file() else None,
        },
        "sha256": hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create ResearchPath release evidence.")
    parser.add_argument("--test-status", choices=("passed", "failed", "incomplete"), required=True)
    parser.add_argument("--mode", choices=("Quick", "Full", "Release"), default="Release")
    parser.add_argument("--run-id")
    parser.add_argument("--duration-seconds", type=float)
    parser.add_argument("--required-step", action="append", default=[])
    parser.add_argument("--completed-step", action="append", default=[])
    parser.add_argument("--skipped-step", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    target = args.output if args.output.is_absolute() else ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            collect(
                args.test_status,
                mode=args.mode,
                run_id=args.run_id,
                duration_seconds=args.duration_seconds,
                required_steps=args.required_step,
                completed_steps=args.completed_step,
                skipped_steps=args.skipped_step,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote release evidence to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
