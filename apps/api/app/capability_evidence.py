from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

MANIFEST_PATH = Path(__file__).resolve().parents[3] / "specs" / "capability-evidence.json"


@lru_cache(maxsize=1)
def capability_evidence_manifest() -> dict[str, dict[str, object]]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = payload.get("capabilities")
    if payload.get("schemaVersion") != "1.0.0" or not isinstance(entries, list):
        raise RuntimeError("Capability evidence manifest has an unsupported shape")
    mapping: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("sliceId"), str):
            raise RuntimeError("Capability evidence entry is missing sliceId")
        slice_id = entry["sliceId"]
        if slice_id in mapping:
            raise RuntimeError(f"Duplicate capability evidence: {slice_id}")
        mapping[slice_id] = entry
    return mapping


def capability_evidence(slice_id: str) -> dict[str, object]:
    try:
        return capability_evidence_manifest()[slice_id]
    except KeyError as error:
        raise RuntimeError(f"Missing capability evidence: {slice_id}") from error
