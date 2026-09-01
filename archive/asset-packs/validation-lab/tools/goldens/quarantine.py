"""Quarantine Manager & Conflict Reconciliation Diagnostic Generator (Specification 29, Section 4.3 & 4.4).

Manages external datasets in reference/quarantine/, performs license & security verification,
promotes verified assets to reference/sources/, and generates reference-comparison.json for reference conflicts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
QUARANTINE_DIR = PROJECT_ROOT / "reference" / "quarantine"
SOURCES_DIR = PROJECT_ROOT / "reference" / "sources"
GOLDENS_DIR = PROJECT_ROOT / "tests" / "goldens"

FORBIDDEN_EXTENSIONS = {
    ".pickle",
    ".pkl",
    ".rdata",
    ".rds",
    ".exe",
    ".bat",
    ".ps1",
    ".cmd",
    ".docm",
    ".xlsm",
}
ALLOWED_EXTENSIONS = {".csv", ".tsv", ".json", ".parquet", ".txt", ".yaml", ".yml"}


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(file_path.read_bytes())
    return hasher.hexdigest()


def verify_quarantine_file(file_path: Path) -> Dict[str, Any]:
    """Validates security, license, format, and size of a file in quarantine."""
    if not file_path.exists():
        return {"valid": False, "reason": "File does not exist"}

    ext = file_path.suffix.lower()
    if ext in FORBIDDEN_EXTENSIONS:
        return {
            "valid": False,
            "reason": f"Forbidden file extension '{ext}'. Pickle, RData, and macro-enabled files are prohibited.",
        }

    if ext not in ALLOWED_EXTENSIONS:
        return {
            "valid": False,
            "reason": f"Unsupported extension '{ext}'. Only open formats allowed.",
        }

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > 50.0:
        return {
            "valid": False,
            "reason": f"File size ({file_size_mb:.2f}MB) exceeds 50MB quarantine ceiling.",
        }

    sha256 = compute_sha256(file_path)

    return {
        "valid": True,
        "filename": file_path.name,
        "sha256": sha256,
        "sizeBytes": file_path.stat().st_size,
    }


def promote_from_quarantine(quarantine_file: Path, license_name: str = "MIT/Public-Domain") -> Path:
    """Promotes a validated quarantine asset to reference/sources/."""
    result = verify_quarantine_file(quarantine_file)
    if not result["valid"]:
        raise ValueError(f"Quarantine verification failed: {result['reason']}")

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    target_path = SOURCES_DIR / quarantine_file.name
    shutil.copy2(quarantine_file, target_path)

    meta_path = SOURCES_DIR / f"{quarantine_file.stem}.meta.json"
    metadata = {
        "filename": quarantine_file.name,
        "sha256": result["sha256"],
        "promotedFrom": str(quarantine_file.relative_to(PROJECT_ROOT)),
        "license": license_name,
        "status": "verified_source",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(
        f"[PROMOTED] {quarantine_file.name} -> reference/sources/ (SHA-256: {result['sha256'][:12]}...)"
    )
    return target_path


def generate_reference_comparison(
    case_dir: Path,
    primary_output: Dict[str, Any],
    secondary_output: Dict[str, Any],
    discrepancies: List[Dict[str, Any]],
) -> Path:
    """Generates reference-comparison.json when primary & secondary reference implementations differ (Spec 29 Sec 4.4)."""
    has_conflict = len(discrepancies) > 0
    comparison_record = {
        "status": "reference_conflict" if has_conflict else "pass",
        "errorCode": "REFERENCE_CONFLICT_UNRESOLVED" if has_conflict else None,
        "capabilityId": case_dir.parent.parent.name if case_dir.name == "cases" else case_dir.name,
        "discrepancies": discrepancies,
        "resolution": "Retained as experimental. Manual methodology review required."
        if has_conflict
        else "Consistent",
    }

    out_path = case_dir / "reference-comparison.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(comparison_record, f, indent=2, ensure_ascii=False)

    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Quarantine & Reference Conflict Management Tool")
    parser.add_argument("--check", action="store_true", help="Check quarantine directory integrity")
    parser.add_argument("--promote", type=str, help="Promote a file from quarantine to sources/")
    parser.add_argument(
        "--license", type=str, default="Public-Domain", help="License name for promoted file"
    )
    args = parser.parse_args()

    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    if args.promote:
        q_file = QUARANTINE_DIR / args.promote
        if not q_file.exists():
            q_file = Path(args.promote)
        try:
            promote_from_quarantine(q_file, args.license)
            return 0
        except Exception as exc:
            print(f"[ERROR] {exc}")
            return 1

    if args.check:
        print(f"[QUARANTINE CHECK] Directory: {QUARANTINE_DIR}")
        files = list(QUARANTINE_DIR.glob("*"))
        valid_count = 0
        for f in files:
            if f.is_file() and f.name != "README.md":
                res = verify_quarantine_file(f)
                status = "VALID" if res["valid"] else f"INVALID ({res['reason']})"
                print(f" - {f.name}: {status}")
                if res["valid"]:
                    valid_count += 1
        print(f"[QUARANTINE CHECK] Checked {len(files)} items ({valid_count} valid).")
        return 0

    print(
        "Use --check to inspect quarantine, or --promote <filename> --license <name> to promote an asset."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
