from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(root: Path) -> list[str]:
    root = root.resolve()
    candidates = (root / "manifest.json", root / "provenance" / "manifest.json")
    manifests = [path for path in candidates if path.is_file()]
    if len(manifests) != 1:
        return ["expected exactly one supported manifest"]
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    failures: list[str] = []
    for item in manifest.get("files", []):
        relative = item.get("path")
        expected = item.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            failures.append("manifest contains an invalid file entry")
            continue
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            failures.append(f"unsafe path: {relative}")
            continue
        if not target.is_file():
            failures.append(f"missing: {relative}")
        elif _sha256(target) != expected:
            failures.append(f"sha256 mismatch: {relative}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a ResearchPath replay package")
    parser.add_argument("root", nargs="?", default=".")
    failures = verify(Path(parser.parse_args().root))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("Replay package hashes verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
