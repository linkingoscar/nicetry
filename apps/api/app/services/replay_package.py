from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

from app.services.repository_io import JsonObject

VERIFY_SCRIPT_PATH = Path(__file__).resolve().parents[4] / "scripts" / "verify-replay-package.py"


def replay_descriptor(command: str | None) -> JsonObject:
    available = command is not None
    return {
        "schemaVersion": "1.0.0",
        "packageFormat": "ResearchPath Replay Package",
        "packageVersion": "1.0.0",
        "available": available,
        "command": command,
        "verificationCommand": "python replay/verify-package.py ." if available else None,
        "hashAlgorithm": "sha256",
        "packageGenerated": False,
        "cleanRoomVerified": False,
        "dataIncluded": None,
        "licenses": {"code": "NOASSERTION", "data": "NOASSERTION"},
        "limitations": [
            "Package creation and hash verification do not establish independent statistical replication.",
            "Code and data licenses are not inferred; NOASSERTION requires human review.",
            "A no-data export requires the exact declared input data before replay can run.",
        ],
    }


def ensure_replay_descriptor(result: JsonObject, *, command: str | None) -> JsonObject:
    result["replay"] = replay_descriptor(command)
    return result


def exported_result(result: JsonObject, *, include_data: bool) -> JsonObject:
    exported = copy.deepcopy(result)
    replay = exported.get("replay")
    if isinstance(replay, dict):
        replay["packageGenerated"] = True
        replay["dataIncluded"] = include_data
    return exported


def write_replay_metadata(
    root: Path,
    *,
    run_id: str,
    command: str,
    include_data: bool,
    manifest_path: str,
) -> None:
    replay_root = root / "replay"
    replay_root.mkdir(parents=True, exist_ok=True)
    if not VERIFY_SCRIPT_PATH.is_file():
        raise ValueError("回放校验脚本不存在")
    shutil.copy2(VERIFY_SCRIPT_PATH, replay_root / "verify-package.py")
    metadata = {
        "@context": "https://w3id.org/ro/crate/1.3/context",
        "@graph": [
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "about": {"@id": "./"},
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.3"},
            },
            {
                "@id": "./",
                "@type": "Dataset",
                "name": "ResearchPath replay package",
                "identifier": run_id,
                "license": "NOASSERTION",
                "hasPart": [
                    {"@id": manifest_path},
                    {"@id": "replay/verify-package.py"},
                    {"@id": "#reproduction-instructions"},
                    {"@id": "#verification-instructions"},
                ],
                "additionalProperty": [
                    {"@id": "#data-included"},
                    {"@id": "#clean-room-verified"},
                    {"@id": "#code-license"},
                    {"@id": "#data-license"},
                ],
            },
            {
                "@id": "replay/verify-package.py",
                "@type": "SoftwareSourceCode",
                "name": "SHA-256 replay package verifier",
                "programmingLanguage": "Python 3 standard library",
            },
            {
                "@id": manifest_path,
                "@type": "MediaObject",
                "name": "Package file manifest",
                "encodingFormat": "application/json",
            },
            {
                "@id": "#reproduction-instructions",
                "@type": "HowTo",
                "name": "Reproduce the analysis",
                "description": command,
            },
            {
                "@id": "#verification-instructions",
                "@type": "HowTo",
                "name": "Verify package file hashes",
                "description": "python replay/verify-package.py .",
            },
            {"@id": "#data-included", "@type": "PropertyValue", "name": "dataIncluded", "value": include_data},
            {"@id": "#clean-room-verified", "@type": "PropertyValue", "name": "cleanRoomVerified", "value": False},
            {"@id": "#code-license", "@type": "PropertyValue", "name": "codeLicense", "value": "NOASSERTION"},
            {"@id": "#data-license", "@type": "PropertyValue", "name": "dataLicense", "value": "NOASSERTION"},
        ],
    }
    (root / "ro-crate-metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
