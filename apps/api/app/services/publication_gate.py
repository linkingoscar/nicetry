from __future__ import annotations

from datetime import datetime

from app.capability_catalog import capability_gate_metadata
from app.services.repository_io import JsonObject


def _capability_slice_ids(result: JsonObject) -> list[str]:
    values: list[str] = []
    graph = result.get("evidenceGraph")
    if isinstance(graph, dict):
        declarations = graph.get("analysisDeclarations")
        if isinstance(declarations, list):
            values.extend(
                str(item["capabilitySliceId"])
                for item in declarations
                if isinstance(item, dict) and item.get("capabilitySliceId")
            )
    provenance = result.get("provenance")
    if isinstance(provenance, dict) and provenance.get("sliceId"):
        values.append(str(provenance["sliceId"]))
    if not values:
        run = result.get("run")
        if isinstance(run, dict):
            if run.get("family"):
                values.append(str(run["family"]))
            elif result.get("semResult") is not None or run.get("template") == "sem":
                values.append("model.sem")
            else:
                values.append("model.process_catalog")
        elif result.get("reportId"):
            values.append("empirical.cross_sectional.overview")
    return list(dict.fromkeys(values or ["unknown.unregistered"]))


def _layer(status: str, checks: list[JsonObject], reasons: list[str]) -> JsonObject:
    return {"status": status, "checks": checks, "reasons": reasons}


def _capability_layer(result: JsonObject) -> JsonObject:
    slice_ids = _capability_slice_ids(result)
    levels = {item: capability_gate_metadata(item).validation_level for item in slice_ids}
    checks = [
        {
            "id": f"capability:{slice_id}",
            "passed": level == "externally_validated",
            "evidence": level,
        }
        for slice_id, level in levels.items()
    ]
    if all(level == "externally_validated" for level in levels.values()):
        status = "passed"
        reasons: list[str] = []
    elif any(level == "unvalidated" for level in levels.values()):
        status = "failed"
        reasons = ["至少一个执行切片尚未完成内部验证。"]
    else:
        status = "conditional"
        reasons = ["执行切片仅完成内部验证，尚缺独立外部数值证据。"]
    return {**_layer(status, checks, reasons), "sliceIds": slice_ids, "validationLevels": levels}


def _run_layer(result: JsonObject) -> JsonObject:
    run = result.get("run")
    run_status = run.get("status") if isinstance(run, dict) else None
    job_status = result.get("jobStatus")
    status_ok = run_status == "succeeded" or job_status == "completed"
    estimation_ok = result.get("estimationStatus") == "succeeded"
    inference_ok = result.get("inferenceStatus") == "reliable"
    identity_ok = bool(
        (isinstance(run, dict) and run.get("id")) or result.get("reportId")
    )
    provenance = result.get("provenance")
    data_ok = isinstance(provenance, dict) and bool(
        provenance.get("dataSha256") or provenance.get("datasetSha256")
    )
    replay = result.get("replay")
    replay_ok = isinstance(replay, dict) and replay.get("packageGenerated") is True and replay.get("cleanRoomVerified") is True
    messages: list[object] = []
    for field in ("diagnostics", "warnings"):
        raw_messages = result.get(field)
        if isinstance(raw_messages, list):
            messages.extend(raw_messages)
    blocking_errors = any(
        isinstance(item, dict) and item.get("severity") == "error"
        for item in messages
    )
    checks = [
        {"id": "successful_run", "passed": status_ok, "evidence": str(run_status or job_status)},
        {"id": "estimation_succeeded", "passed": estimation_ok, "evidence": str(result.get("estimationStatus"))},
        {"id": "inference_reliable", "passed": inference_ok, "evidence": str(result.get("inferenceStatus"))},
        {"id": "result_identity", "passed": identity_ok, "evidence": "bound" if identity_ok else "missing"},
        {"id": "data_identity", "passed": data_ok, "evidence": "sha256" if data_ok else "missing"},
        {"id": "no_blocking_errors", "passed": not blocking_errors, "evidence": "none" if not blocking_errors else "present"},
        {"id": "clean_room_replay", "passed": replay_ok, "evidence": "verified" if replay_ok else "not_verified"},
    ]
    passed = all(item["passed"] is True for item in checks)
    return _layer(
        "passed" if passed else "failed",
        checks,
        [] if passed else ["单次运行尚未同时满足可靠推断、身份绑定和干净环境回放。"],
    )


def _reporting_layer(result: JsonObject) -> JsonObject:
    assessments = result.get("reportingProfileAssessments")
    applicable = [
        item
        for item in assessments
        if isinstance(item, dict) and item.get("applicable") is True
    ] if isinstance(assessments, list) else []
    checks = [
        {
            "id": str(item.get("profileId")),
            "passed": item.get("completeness") == 1,
            "evidence": f"completeness={item.get('completeness')}",
        }
        for item in applicable
    ]
    passed = bool(checks) and all(item["passed"] is True for item in checks)
    return _layer(
        "passed" if passed else "failed",
        checks,
        [] if passed else ["至少一个适用披露画像不完整，或没有可评估画像。"],
    )


def build_publication_gate(
    result: JsonObject,
    *,
    confirmed_by: str | None = None,
    confirmed_at: str | None = None,
) -> JsonObject:
    capability = _capability_layer(result)
    run = _run_layer(result)
    reporting = _reporting_layer(result)
    confirmed = bool(confirmed_by and confirmed_at)
    if confirmed_at is not None:
        datetime.fromisoformat(confirmed_at.replace("Z", "+00:00"))
    layers_pass = all(layer["status"] == "passed" for layer in (capability, run, reporting))
    final_eligible = layers_pass and confirmed
    if final_eligible:
        final_status = "eligible"
        reasons: list[str] = []
    elif layers_pass:
        final_status = "requires_human_confirmation"
        reasons = ["三层机器门禁已通过，但仍需具名人工确认。"]
    else:
        final_status = "ineligible"
        reasons = ["能力证据、单次运行证据或稿件披露至少一层未通过。"]
    return {
        "schemaVersion": "1.0.0",
        "capabilityLayer": capability,
        "runEvidenceLayer": run,
        "reportingLayer": reporting,
        "humanConfirmation": {
            "confirmed": confirmed,
            "confirmedBy": confirmed_by if confirmed else None,
            "confirmedAt": confirmed_at if confirmed else None,
        },
        "finalStatus": final_status,
        "finalEligible": final_eligible,
        "reasons": reasons,
    }
