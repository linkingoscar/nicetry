"""Freeze tool for AI-Agent Gold Standard Bundle assets (Specification 28, Section 22.6).

Calculates SHA-256 hashes of input datasets, analysis specs, and expected outputs,
freezing the manifests and generating immutable provenance records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDENS_DIR = PROJECT_ROOT / "tests" / "goldens"


def compute_file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def resolve_case_asset(case_dir: Path, relative_path: str) -> Path:
    case_root = case_dir.resolve()
    candidate = (case_root / relative_path).resolve()
    if not candidate.is_relative_to(case_root):
        raise ValueError(f"Golden asset escapes case directory: {relative_path}")
    return candidate


def freeze_case(case_dir: Path, *, provenance_only: bool = False) -> Dict[str, Any]:
    manifest_path = case_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    unresolved = (manifest.get("evidence") or {}).get("unresolvedConflicts", [])
    reconciliation_path = case_dir / "expected" / "reconciliation.json"
    reconciliation = (
        json.loads(reconciliation_path.read_text(encoding="utf-8"))
        if reconciliation_path.is_file()
        else None
    )
    if not provenance_only and (
        unresolved
        or (
            isinstance(reconciliation, dict)
            and reconciliation.get("status") not in {"pass", "consensus"}
        )
    ):
        raise ValueError(
            "Golden case has unresolved reference conflicts and must remain quarantined"
        )

    provenance_dir = case_dir / "provenance"
    provenance_dir.mkdir(parents=True, exist_ok=True)

    hashes: Dict[str, str] = {}
    manifest_changed = False
    source_dataset_hash: str | None = None

    # Hash dataset files
    for ds_entry in manifest.get("dataset", []):
        ds_file = resolve_case_asset(case_dir, ds_entry["path"])
        if ds_file.exists():
            ds_hash = compute_file_sha256(ds_file)
            if ds_entry.get("sha256") != ds_hash:
                manifest_changed = True
            ds_entry["sha256"] = ds_hash
            hashes[ds_entry["path"]] = ds_hash
            if (
                source_dataset_hash is None
                and ds_file.parent == (case_dir / "data").resolve()
                and ds_file.name.startswith("input.")
            ):
                source_dataset_hash = ds_hash

    # Keep the auditable source record synchronized with the governed input.
    source_path = case_dir / "data" / "source.json"
    if source_dataset_hash is not None and source_path.is_file():
        source_record = json.loads(source_path.read_text(encoding="utf-8"))
        if (
            isinstance(source_record, dict)
            and source_record.get("sha256") != source_dataset_hash
        ):
            source_record["sha256"] = source_dataset_hash
            with open(source_path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(source_record, f, indent=2, ensure_ascii=False)
                f.write("\n")

    # Hash specifications, evidence, independent references and expected assets.
    governed_paths = {
        manifest.get("specPath", "spec/analysis-spec.json"),
        manifest.get("estimandPath"),
        manifest.get("expectedOutputPath", "expected/expected.json"),
        "data/source.json",
        "data/LICENSE.txt",
        "expected/reconciliation.json",
        "expected/invariants.json",
    }
    for reference_name in ("primaryReference", "secondaryReference"):
        reference = manifest.get(reference_name)
        if not isinstance(reference, dict):
            continue
        governed_paths.add(reference.get("normalizedOutput"))
        normalized_output = reference.get("normalizedOutput")
        if isinstance(normalized_output, str):
            governed_paths.add(str(Path(normalized_output).parent / "run.py"))
            governed_paths.add(str(Path(normalized_output).parent / "run.R"))
            governed_paths.add(str(Path(normalized_output).parent / "session-info.txt"))

    for relative_path in sorted(path for path in governed_paths if isinstance(path, str)):
        governed_file = resolve_case_asset(case_dir, relative_path)
        if governed_file.is_file():
            hashes[relative_path] = compute_file_sha256(governed_file)

    if not provenance_only:
        # Freeze identity status only after reference consensus is established.
        manifest["identity"]["status"] = "frozen"
        manifest_changed = True

    if manifest_changed:
        with open(manifest_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(manifest, f, sort_keys=False, allow_unicode=True)

    # Write provenance hashes
    hash_record_path = provenance_dir / "hashes.json"
    with open(hash_record_path, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2, ensure_ascii=False)

    return hashes


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze AI-Agent Golden Bundle Assets")
    parser.add_argument("--capability", type=str, help="Capability ID to freeze")
    parser.add_argument("--case", type=str, help="Specific Case ID to freeze")
    parser.add_argument(
        "--provenance-only",
        action="store_true",
        help="Refresh governed hashes without changing draft/quarantined status",
    )
    args = parser.parse_args()

    if not GOLDENS_DIR.exists():
        print(f"Goldens directory not found at {GOLDENS_DIR}")
        return 1

    targets: list[Path] = []
    if args.capability:
        cap_dir = GOLDENS_DIR / args.capability
        if cap_dir.exists():
            targets.extend([d for d in (cap_dir / "cases").iterdir() if d.is_dir()])
    elif args.case:
        for case_path in GOLDENS_DIR.glob(f"**/cases/{args.case}"):
            if case_path.is_dir():
                targets.append(case_path)
    else:
        # Freeze all cases
        for case_path in GOLDENS_DIR.glob("**/cases/*"):
            if case_path.is_dir() and (case_path / "manifest.yaml").exists():
                targets.append(case_path)

    if not targets:
        print("No cases found to freeze.")
        return 0

    print(f"Freezing {len(targets)} Golden case(s)...")
    for case_dir in targets:
        try:
            hashes = freeze_case(case_dir, provenance_only=args.provenance_only)
            action = "HASHED" if args.provenance_only else "FROZEN"
            print(f" [{action}] {case_dir.relative_to(GOLDENS_DIR)} ({len(hashes)} files hashed)")
        except Exception as exc:
            print(f" [ERROR] Failed to freeze {case_dir}: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
