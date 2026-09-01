from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import cast

from app.services.report_facts import resolve_json_pointer
from app.services.repository_io import JsonObject

PROFILE_PATH = Path(__file__).resolve().parents[4] / "specs" / "reporting-profiles.json"


@lru_cache(maxsize=1)
def reporting_profiles() -> list[dict[str, object]]:
    payload = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profiles = payload.get("profiles")
    if payload.get("schemaVersion") != "1.0.0" or not isinstance(profiles, list):
        raise RuntimeError("Reporting profile manifest has an unsupported shape")
    return [cast(dict[str, object], item) for item in profiles if isinstance(item, dict)]


def _path_match(result: JsonObject, requirement: dict[str, object]) -> list[str]:
    paths = requirement.get("anyOfPaths")
    if not isinstance(paths, list):
        return []
    matched: list[str] = []
    for path in paths:
        if not isinstance(path, str):
            continue
        try:
            value = resolve_json_pointer(result, path, str(requirement.get("id", "requirement")))
        except ValueError:
            continue
        if requirement.get("requireNonNull") is True and value is None:
            continue
        if "expectedValue" in requirement and value != requirement["expectedValue"]:
            continue
        matched.append(path)
    return matched


def _is_randomized(result: JsonObject) -> bool:
    boundary = result.get("claimBoundary")
    if isinstance(boundary, dict) and boundary.get("experimentalEffectEstablished") is True:
        return True
    run = result.get("run")
    return isinstance(run, dict) and run.get("family") == "experimental_design"


def assess_reporting_profiles(result: JsonObject) -> list[dict[str, object]]:
    randomized = _is_randomized(result)
    assessments: list[dict[str, object]] = []
    for profile in reporting_profiles():
        profile_id = str(profile["id"])
        applicable = not (
            (profile_id == "consort_2025_randomized" and not randomized)
            or (profile_id == "strobe_observational" and randomized)
        )
        requirements = profile.get("requirements")
        items: list[dict[str, object]] = []
        if isinstance(requirements, list):
            for raw in requirements:
                if not isinstance(raw, dict):
                    continue
                requirement = cast(dict[str, object], raw)
                matched = _path_match(result, requirement) if applicable else []
                items.append({
                    "id": requirement["id"],
                    "label": requirement["label"],
                    "satisfied": bool(matched) if applicable else False,
                    "evidencePaths": matched,
                })
        satisfied = sum(item["satisfied"] is True for item in items)
        total = len(items)
        assessments.append({
            "profileId": profile_id,
            "profileVersion": profile["version"],
            "label": profile["label"],
            "scopeNote": profile["scopeNote"],
            "purpose": "disclosure_completeness_only",
            "applicable": applicable,
            "satisfiedCount": satisfied,
            "totalCount": total,
            "completeness": satisfied / total if applicable and total else None,
            "items": items,
            "qualityCertified": False,
            "causalCertified": False,
            "publicationEligibilityGranted": False,
        })
    return assessments


def ensure_reporting_profiles(result: JsonObject) -> JsonObject:
    result["reportingProfileAssessments"] = assess_reporting_profiles(result)
    return result
