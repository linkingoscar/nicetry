"""Containerized & Isolated Reference Runner CLI tool (Specification 28, Section 8, 10.1 & 22.4).

Executes primary and secondary reference scripts for Golden Cases:
- If Docker daemon is available, runs reference code inside isolated unprivileged container (image@sha256:<digest>).
- If Docker is not installed/running, logs [WARNING] and falls back to isolated Subprocess execution.
- Captures stdout.log, stderr.log, session-info.txt, raw-output.json, and normalized-output.json.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDENS_DIR = PROJECT_ROOT / "tests" / "goldens"


def is_docker_available() -> bool:
    """Checks whether Docker CLI executable and daemon are available."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return False
    try:
        res = subprocess.run(
            [docker_bin, "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        return res.returncode == 0
    except Exception:
        return False


def run_reference_cmd_subprocess(
    command_str: str,
    case_dir: Path,
    output_dir: Path,
) -> Tuple[bool, str, str]:
    """Runs reference runner command via isolated Subprocess as fallback."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "stdout.log"
    stderr_path = output_dir / "stderr.log"

    env = copy_sanitized_env()
    env["RESEARCHPATH_PROJECT_ROOT"] = str(PROJECT_ROOT)

    try:
        res = subprocess.run(
            command_str,
            shell=True,
            cwd=str(case_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            env=env,
        )
        stdout_path.write_text(res.stdout, encoding="utf-8")
        stderr_path.write_text(res.stderr, encoding="utf-8")

        # Save session info
        session_info = f"Engine Execution Fallback: Subprocess\nCommand: {command_str}\nReturn Code: {res.returncode}\nPython: {sys.version}\nPlatform: {sys.platform}\n"
        (output_dir / "session-info.txt").write_text(session_info, encoding="utf-8")

        return res.returncode == 0, res.stdout, res.stderr
    except Exception as exc:
        stderr_path.write_text(str(exc), encoding="utf-8")
        return False, "", str(exc)


def run_reference_cmd_docker(
    command_str: str,
    case_dir: Path,
    output_dir: Path,
    container_digest: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """Runs reference runner command inside isolated unprivileged Docker container."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "stdout.log"
    stderr_path = output_dir / "stderr.log"

    image_tag = container_digest if container_digest else "r-base:latest"
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--user",
        "1000:1000",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid",
        "-v",
        f"{case_dir.resolve()}:/workspace/case:rw",
        "-w",
        "/workspace/case",
        image_tag,
        "sh",
        "-c",
        command_str,
    ]

    try:
        res = subprocess.run(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )
        stdout_path.write_text(res.stdout, encoding="utf-8")
        stderr_path.write_text(res.stderr, encoding="utf-8")

        session_info = f"Engine Execution: Docker Container\nImage: {image_tag}\nCommand: {command_str}\nReturn Code: {res.returncode}\n"
        (output_dir / "session-info.txt").write_text(session_info, encoding="utf-8")

        return res.returncode == 0, res.stdout, res.stderr
    except Exception as exc:
        stderr_path.write_text(str(exc), encoding="utf-8")
        return False, "", str(exc)


def copy_sanitized_env() -> Dict[str, str]:
    """Prepares sanitized environment variables for process isolation."""
    env = os.environ.copy()
    # Remove sensitive env vars if present
    for k in list(env.keys()):
        if any(token in k.upper() for token in ("SECRET", "TOKEN", "KEY", "PASSWORD", "AUTH")):
            del env[k]
    return env


def build_references_for_case(case_dir: Path, use_docker_if_avail: bool = True) -> Dict[str, Any]:
    manifest_path = case_dir / "manifest.yaml"
    if not manifest_path.exists():
        return {"caseId": case_dir.name, "passed": False, "reason": "Manifest missing"}

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    docker_avail = is_docker_available() if use_docker_if_avail else False
    if not docker_avail:
        print(
            f" [WARNING] Docker is not installed/running locally. Falling back to Subprocess execution for {case_dir.name}."
        )

    primary_ref = manifest.get("primaryReference", {})
    primary_cmd = primary_ref.get("command")
    primary_out_rel = primary_ref.get(
        "normalizedOutput", "reference/primary/normalized-output.json"
    )
    primary_out_dir = case_dir / Path(primary_out_rel).parent

    primary_passed = True
    primary_executed = bool(primary_cmd)
    if primary_cmd:
        if docker_avail:
            ok, out, err = run_reference_cmd_docker(
                primary_cmd, case_dir, primary_out_dir, primary_ref.get("containerDigest")
            )
        else:
            ok, out, err = run_reference_cmd_subprocess(primary_cmd, case_dir, primary_out_dir)
        primary_passed = ok
    else:
        primary_passed = False

    secondary_ref = manifest.get("secondaryReference")
    secondary_passed = True
    if secondary_ref and secondary_ref.get("command"):
        sec_cmd = secondary_ref.get("command")
        sec_out_rel = secondary_ref.get(
            "normalizedOutput", "reference/secondary/normalized-output.json"
        )
        sec_out_dir = case_dir / Path(sec_out_rel).parent

        if docker_avail:
            ok, out, err = run_reference_cmd_docker(
                sec_cmd, case_dir, sec_out_dir, secondary_ref.get("containerDigest")
            )
        else:
            ok, out, err = run_reference_cmd_subprocess(sec_cmd, case_dir, sec_out_dir)
        secondary_passed = ok

    passed = primary_executed and primary_passed and secondary_passed
    return {
        "caseId": case_dir.name,
        "passed": passed,
        "dockerUsed": docker_avail,
        "primaryPassed": primary_passed,
        "primaryExecuted": primary_executed,
        "secondaryPassed": secondary_passed,
        "reason": None if primary_executed else "Primary reference command is missing",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Containerized & Isolated Reference Runner")
    parser.add_argument("--case", type=str, help="Specific Case ID to run references for")
    parser.add_argument("--capability", type=str, help="Capability ID to run references for")
    parser.add_argument(
        "--all", action="store_true", help="Run reference runners for all golden cases"
    )
    parser.add_argument(
        "--no-docker", action="store_true", help="Use the isolated local subprocess runner"
    )
    args = parser.parse_args()

    cases: List[Path] = []
    if args.capability:
        cap_dir = GOLDENS_DIR / args.capability
        if cap_dir.exists():
            cases.extend([d for d in (cap_dir / "cases").iterdir() if d.is_dir()])
    elif args.case:
        for p in GOLDENS_DIR.glob(f"**/cases/{args.case}"):
            if p.is_dir():
                cases.append(p)
    elif args.all:
        cases.extend(
            [
                p
                for p in GOLDENS_DIR.glob("**/cases/*")
                if p.is_dir() and (p / "manifest.yaml").exists()
            ]
        )

    if not cases:
        print("No cases found to build references for.")
        return 1

    print(f"Building references for {len(cases)} case(s)...")
    all_passed = True

    for case_dir in cases:
        res = build_references_for_case(case_dir, use_docker_if_avail=not args.no_docker)
        tag = "[PASS]" if res["passed"] else "[FAIL]"
        mode_str = "Docker" if res["dockerUsed"] else "Subprocess Fallback"
        print(f" {tag} {res['caseId']} ({mode_str})")
        if not res["passed"]:
            all_passed = False
            if res.get("reason"):
                print(f"    - {res['reason']}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
