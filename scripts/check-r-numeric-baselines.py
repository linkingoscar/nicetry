#!/usr/bin/env python3
"""Verify the independently generated R reference goldens without touching fixtures.

This is deliberately stricter than a smoke test: it detects package-version
changes, JSON-shape changes, and numeric drift at each reference fixture's
declared tolerance.  Regenerating a checked-in golden remains a reviewed
change, never an automatic update during CI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CACHE_SCHEMA_VERSION = "1.0.0"


class BaselineDriftError(AssertionError):
    """Raised when an independently recalculated reference differs from its golden."""


def _maximum_declared_tolerance(value: Any) -> float:
    if not isinstance(value, dict) or not value:
        raise BaselineDriftError("Golden provenance is missing a numeric tolerance declaration.")
    tolerances = [
        float(item)
        for item in value.values()
        if isinstance(item, (int, float)) and not isinstance(item, bool)
    ]
    if not tolerances or any(item <= 0 for item in tolerances):
        raise BaselineDriftError("Golden provenance must declare positive numeric tolerances.")
    return max(tolerances)


def _compare(expected: Any, actual: Any, *, path: str, tolerance: float) -> list[str]:
    if isinstance(expected, bool) or expected is None:
        return [] if expected is actual else [f"{path}: expected {expected!r}, got {actual!r}"]
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return [f"{path}: expected numeric {expected!r}, got {actual!r}"]
        if not math.isfinite(float(expected)) or not math.isfinite(float(actual)):
            return (
                []
                if float(expected) == float(actual)
                else [f"{path}: expected {expected!r}, got {actual!r}"]
            )
        if not math.isclose(float(expected), float(actual), rel_tol=0.0, abs_tol=tolerance):
            return [
                f"{path}: expected {expected:.12g}, got {actual:.12g} "
                f"(|delta|={abs(float(expected) - float(actual)):.3g}; tolerance={tolerance:.3g})"
            ]
        return []
    if isinstance(expected, str):
        return [] if expected == actual else [f"{path}: expected {expected!r}, got {actual!r}"]
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{path}: expected a list, got {type(actual).__name__}"]
        if len(expected) != len(actual):
            return [f"{path}: expected {len(expected)} entries, got {len(actual)}"]
        differences: list[str] = []
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual, strict=True)):
            differences.extend(
                _compare(expected_item, actual_item, path=f"{path}[{index}]", tolerance=tolerance)
            )
        return differences
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected an object, got {type(actual).__name__}"]
        expected_keys, actual_keys = set(expected), set(actual)
        if expected_keys != actual_keys:
            return [
                f"{path}: key drift; missing={sorted(expected_keys - actual_keys)}, extra={sorted(actual_keys - expected_keys)}"
            ]
        differences = []
        for key in sorted(expected):
            differences.extend(
                _compare(expected[key], actual[key], path=f"{path}.{key}", tolerance=tolerance)
            )
        return differences
    return [] if expected == actual else [f"{path}: expected {expected!r}, got {actual!r}"]


def _content_identity(root: Path, rscript: Path, input_paths: list[Path]) -> dict[str, Any]:
    digest = hashlib.sha256()
    for path in sorted(set(input_paths)):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(path.read_bytes())
    runtime = subprocess.run(
        [str(rscript), "--version"], text=True, capture_output=True, check=False
    )
    if runtime.returncode:
        raise RuntimeError("Unable to identify the project-locked R runtime.")
    runtime_version = (runtime.stdout or runtime.stderr).strip()
    digest.update(runtime_version.encode("utf-8"))
    return {
        "schemaVersion": CACHE_SCHEMA_VERSION,
        "sha256": digest.hexdigest(),
        "rRuntime": runtime_version,
    }


def _cache_matches(cache_path: Path, identity: dict[str, Any]) -> bool:
    try:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False
    return cached.get("identity") == identity and cached.get("status") == "passed"


def _write_cache(cache_path: Path, identity: dict[str, Any], baseline_count: int) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "identity": identity,
        "status": "passed",
        "baselineCount": baseline_count,
    }
    temporary = cache_path.with_suffix(cache_path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(cache_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--cache-path", type=Path)
    arguments = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    reference_dir = root / "apps" / "api" / "tests" / "fixtures" / "advanced" / "reference"
    golden_dir = reference_dir.parent / "goldens"
    rscript = root / ".runtime" / "R" / "bin" / "Rscript.exe"
    r_library = root / ".runtime" / "R-library"
    generator = reference_dir / "generate-goldens.R"
    cache_path = arguments.cache_path or root / ".pytest-tmp" / "r-numeric-baseline-cache.json"

    if not rscript.exists():
        raise FileNotFoundError(f"Project-locked R runtime was not found: {rscript}")

    all_expected_paths = sorted(golden_dir.glob("*.expected.json"))
    expected_paths = [
        path
        for path in all_expected_paths
        if not str(
            json.loads(path.read_text(encoding="utf-8")).get("provenance", {}).get("reference", "")
        ).startswith("R pwr::")
    ]
    if not expected_paths:
        raise FileNotFoundError(f"No checked-in R numeric baselines found in {golden_dir}")

    identity_inputs = [
        Path(__file__).resolve(),
        root / "renv.lock",
        *reference_dir.glob("*"),
        *golden_dir.glob("*.expected.json"),
        *(root / "engine" / "R").rglob("*.R"),
    ]
    identity = _content_identity(
        root,
        rscript,
        [path for path in identity_inputs if path.is_file()],
    )
    if not arguments.no_cache and _cache_matches(cache_path, identity):
        print(
            f"R numeric baseline check cache hit ({len(expected_paths)} goldens; "
            f"identity={identity['sha256'][:12]})."
        )
        return 0

    with tempfile.TemporaryDirectory(prefix="researchpath-r-baseline-") as temporary_directory:
        temporary = Path(temporary_directory)
        fixture_output = temporary / "fixtures"
        generated_goldens = temporary / "goldens"
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(r_library)
        environment["RESEARCHPATH_REFERENCE_FIXTURE_OUTPUT_DIR"] = str(fixture_output)
        environment["RESEARCHPATH_GOLDEN_OUTPUT_DIR"] = str(generated_goldens)
        completed = subprocess.run(
            [str(rscript), "--vanilla", str(generator)],
            cwd=root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode:
            sys.stderr.write(completed.stdout)
            sys.stderr.write(completed.stderr)
            raise RuntimeError(
                f"Independent R reference generator failed with exit code {completed.returncode}."
            )

        differences: list[str] = []
        for expected_path in expected_paths:
            actual_path = generated_goldens / expected_path.name
            if not actual_path.exists():
                differences.append(
                    f"{expected_path.name}: generator did not produce this baseline."
                )
                continue
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            actual = json.loads(actual_path.read_text(encoding="utf-8"))
            tolerance = _maximum_declared_tolerance(expected.get("provenance", {}).get("tolerance"))
            differences.extend(
                _compare(expected, actual, path=expected_path.name, tolerance=tolerance)
            )

        generated_names = {path.name for path in generated_goldens.glob("*.expected.json")}
        expected_names = {path.name for path in expected_paths}
        if generated_names != expected_names:
            differences.append(
                "Baseline file-set drift; "
                f"missing={sorted(expected_names - generated_names)}, extra={sorted(generated_names - expected_names)}"
            )

        if differences:
            preview = "\n".join(f"- {item}" for item in differences[:40])
            remaining = len(differences) - min(len(differences), 40)
            if remaining:
                preview += f"\n- … {remaining} additional differences"
            raise BaselineDriftError(
                "R numeric baseline drift detected. Review the package upgrade and application results before "
                "intentionally regenerating a golden; do not widen its tolerance to silence drift.\n"
                + preview
            )

    if not arguments.no_cache:
        _write_cache(cache_path, identity, len(expected_paths))
    print(
        f"R numeric baseline check passed ({len(expected_paths)} independently generated goldens; "
        f"identity={identity['sha256'][:12]}; cache={'bypassed' if arguments.no_cache else 'updated'})."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BaselineDriftError, FileNotFoundError, RuntimeError) as error:
        print(f"R numeric baseline check failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
