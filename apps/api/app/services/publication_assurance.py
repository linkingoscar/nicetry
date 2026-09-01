from __future__ import annotations

from pathlib import Path

from app.contracts import validate_contract
from app.services.publication_gate import build_publication_gate
from app.services.replay_package import ensure_replay_descriptor
from app.services.reporting_profiles import ensure_reporting_profiles
from app.services.repository_io import JsonObject

ASSURANCE_SCHEMA_PATH = Path(__file__).resolve().parents[4] / "specs" / "publication-assurance.schema.json"


def ensure_publication_assurance(result: JsonObject, *, replay_command: str | None) -> JsonObject:
    ensure_replay_descriptor(result, command=replay_command)
    ensure_reporting_profiles(result)
    result["publicationGate"] = build_publication_gate(result)
    validate_contract(
        {"replay": result["replay"], "publicationGate": result["publicationGate"]},
        ASSURANCE_SCHEMA_PATH,
    )
    return result
