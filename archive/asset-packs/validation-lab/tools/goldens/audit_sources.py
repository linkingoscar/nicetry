"""Source & License Auditor (INFRA-02 per Spec 32, Section 8).

Discovers and validates all data/source.json files across tests/goldens/,
checking SHA256 hashes, license declarations, canonical URLs, and source ID uniqueness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDENS_DIR = PROJECT_ROOT / "tests" / "goldens"

REQUIRED_FIELDS = [
    "sourceId",
    "sourceType",
    "title",
    "publisher",
    "canonicalUrl",
    "retrievedAt",
    "version",
    "license",
    "sha256",
    "allowedUse",
]


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_single_source(source_json_path: Path) -> Dict[str, Any]:
    issues: List[str] = []
    case_dir = source_json_path.parent.parent

    try:
        with source_json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {
            "path": str(source_json_path),
            "valid": False,
            "issues": [f"JSON format error: {e}"],
        }

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data or not data[field]:
            issues.append(f"Missing required field: '{field}'")

    # Verify input data file hash if present
    data_dir = source_json_path.parent
    input_files = list(data_dir.glob("input.*"))
    if input_files:
        actual_hash = _hash_file(input_files[0])
        expected_hash = data.get("sha256")
        if expected_hash and actual_hash != expected_hash:
            issues.append(
                f"File SHA256 mismatch for {input_files[0].name}: expected {expected_hash}, got {actual_hash}"
            )

    return {
        "path": str(source_json_path),
        "sourceId": data.get("sourceId"),
        "license": data.get("license"),
        "valid": len(issues) == 0,
        "issues": issues,
    }


def audit_all_sources() -> Dict[str, Any]:
    sources = list(GOLDENS_DIR.glob("**/data/source.json"))
    results: List[Dict[str, Any]] = []
    seen_sources: Dict[str, str] = {}
    total_issues = 0

    for s_path in sources:
        res = audit_single_source(s_path)
        s_id = res.get("sourceId")
        if s_id:
            if s_id in seen_sources and seen_sources[s_id] != str(s_path):
                res["issues"].append(f"Duplicate sourceId '{s_id}' collision with {seen_sources[s_id]}")
                res["valid"] = False
            else:
                seen_sources[s_id] = str(s_path)

        if not res["valid"]:
            total_issues += len(res["issues"])
        results.append(res)

    report = {
        "totalSourcesFound": len(sources),
        "validSources": sum(1 for r in results if r["valid"]),
        "invalidSources": sum(1 for r in results if not r["valid"]),
        "totalIssues": total_issues,
        "results": results,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Data Source & License Auditor")
    parser.add_argument("--all", action="store_true", help="Audit all data/source.json files")
    parser.add_argument("--fix", action="store_true", help="Automatically calculate and populate missing sha256 hashes")
    parser.add_argument("--out", type=str, help="Output report JSON file path")
    args = parser.parse_args()

    if args.fix:
        sources = list(GOLDENS_DIR.glob("**/data/source.json"))
        fixed_count = 0
        for s_path in sources:
            with s_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            input_files = list(s_path.parent.glob("input.*"))
            if input_files and ("sha256" not in data or not data["sha256"]):
                data["sha256"] = _hash_file(input_files[0])
                with s_path.open("w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                fixed_count += 1
        print(f"Auto-fixed sha256 hash for {fixed_count} source.json files.")

    report = audit_all_sources()

    print(f"Source Auditor Summary: Found {report['totalSourcesFound']} sources.")
    print(f"  Valid: {report['validSources']}, Invalid: {report['invalidSources']}")

    if report["totalIssues"] > 0:
        print("\nDiscovered Issues:")
        for r in report["results"]:
            if not r["valid"]:
                print(f"  [{r['path']}]:")
                for issue in r["issues"]:
                    print(f"    - {issue}")

    if args.out:
        out_p = Path(args.out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with out_p.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nReport saved to {out_p}")

    return 0 if report["totalIssues"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
