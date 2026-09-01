from __future__ import annotations

import re
import uuid
from typing import Any, cast

import pandas as pd  # noqa: F401

from app.contracts import ContractValidationError, canonical_model_hash, validate_contract
from app.services.analysis_context import AnalysisContextResolutionError, AnalysisContextService
from app.services.capability_applicability import applicable_capability_registry
from app.services.dataset_repository import DatasetRepository, _write_json_atomic
from app.services.model_service_helpers import _model_variables, _utc_now  # noqa: F401
from app.services.model_service_validation import validate_model_for_dataset
from app.settings import Settings

MODEL_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")


class ModelValidationError(ValueError):
    pass


def validate_model_context(
    dataset_id: str,
    model_spec: dict[str, object],
    context_service: AnalysisContextService,
) -> dict[str, object] | None:
    context_hash = model_spec.get("contextHash")
    if context_hash is None:
        raise AnalysisContextResolutionError(
            "ANALYSIS_CONTEXT_REQUIRED",
            "PROCESS/SEM 模型必须绑定当前服务端解析的分析上下文。",
        )
    sample_version_id = model_spec.get("sampleVersionId")
    sample_id = (
        None
        if not sample_version_id or str(sample_version_id).startswith("sample_all_")
        else str(sample_version_id)
    )
    context = context_service.resolve(dataset_id, sample_version_id=sample_id)
    if context.get("contextHash") != context_hash:
        raise AnalysisContextResolutionError(
            "ANALYSIS_CONTEXT_CHANGED",
            "ModelSpec 的 contextHash 不是当前服务端解析出的上下文版本。",
        )
    if context.get("validity") != "ready":
        raise AnalysisContextResolutionError(
            "ANALYSIS_CONTEXT_INCOMPLETE",
            "PROCESS/SEM 运行前必须完成 study context 与结构角色确认。",
        )
    estimation = model_spec.get("estimation")
    estimation = estimation if isinstance(estimation, dict) else {}
    capability_slice = (
        "model.sem"
        if estimation.get("family") == "sem"
        else "model.process_catalog"
    )
    applicability = applicable_capability_registry.evaluate_slice(
        capability_slice,
        context,
    )
    if not applicability.get("executionAvailable") or not applicability.get("applicable"):
        raise AnalysisContextResolutionError(
            "METHOD_NOT_APPLICABLE_TO_CONTEXT",
            str(
                applicability.get("blockedReason")
                or "当前研究上下文不允许该 PROCESS/SEM 方法。"
            ),
        )
    dataset_ref = cast(dict[str, object], context.get("dataset") or {})
    sample_ref = cast(dict[str, object], context.get("sample") or {})
    structure_ref = cast(dict[str, object], context.get("structure") or {})
    measurement_ref = cast(dict[str, object], context.get("measurement") or {})
    expected_refs = {
        "datasetSha256": dataset_ref.get("sha256"),
        "sampleVersionId": sample_ref.get("id"),
        "sampleHash": sample_ref.get("hash"),
        "structureVersionId": structure_ref.get("id"),
        "structureHash": structure_ref.get("hash"),
        "measurementVersionId": measurement_ref.get("id"),
        "measurementHash": measurement_ref.get("hash"),
    }
    for key, actual in expected_refs.items():
        supplied = model_spec.get(key)
        if supplied is not None and supplied != actual:
            raise AnalysisContextResolutionError(
                "ANALYSIS_CONTEXT_CHANGED",
                f"ModelSpec 的 {key} 与当前服务端版本不一致。",
            )
    return {
        key: value
        for key, value in {"contextHash": context.get("contextHash"), **expected_refs}.items()
        if value is not None
    }


def validate_model_for_dataset_request(
    dataset_id: str,
    model_spec: dict[str, object],
    repository: DatasetRepository,
    context_service: AnalysisContextService,
    settings: Settings,
) -> dict[str, Any]:
    """Validate a model against the dataset-bound context, shaping the response."""
    try:
        validate_contract(model_spec, settings.model_schema_path)
    except ContractValidationError as error:
        return {
            "valid": False,
            "structuralStatus": "invalid",
            "errors": error.errors,
            "warnings": [],
            "template": None,
            "catalogVersion": "5.0",
            "matchStatus": "invalid",
            "processModelNumber": None,
            "displayName": "模型契约无效",
            "executionAvailable": False,
            "unsupportedReason": "请先修正模型数据结构",
            "sampleFlow": None,
        }
    validate_model_context(dataset_id, model_spec, context_service)
    return validate_model_for_dataset(dataset_id, model_spec, repository)


def save_model_draft(
    dataset_id: str,
    model_spec: dict[str, Any],
    validation: dict[str, Any],
    repository: DatasetRepository,
) -> dict[str, Any]:
    model_id = str(model_spec.get("modelId", ""))
    if not MODEL_ID.fullmatch(model_id):
        raise ModelValidationError("模型 ID 无效，无法保存草稿")
    repository.get_dataset(dataset_id)
    updated_at = _utc_now()
    model_hash = canonical_model_hash(model_spec)
    path = (
        repository.settings.state_root / "projects" / "default" / "models" / model_id / "draft.json"
    )
    response = {
        "schemaVersion": "1.0.0",
        "id": f"draft_{uuid.uuid4().hex[:16]}",
        "status": "draft",
        "datasetId": dataset_id,
        "modelId": model_id,
        "updatedAt": updated_at,
        "modelHash": model_hash,
        "validation": validation,
        "modelSpec": model_spec,
    }
    _write_json_atomic(path, response)
    repository.record_model_draft(dataset_id, model_id, updated_at, path, model_hash)
    return response


def freeze_model(
    dataset_id: str,
    model_spec: dict[str, Any],
    validation: dict[str, Any],
    override_reason: str | None,
    repository: DatasetRepository,
) -> dict[str, Any]:
    if not validation["valid"]:
        raise ModelValidationError("模型包含不可覆盖的错误，不能冻结")
    cleaned_reason = (override_reason or "").strip()
    if validation["warnings"] and not cleaned_reason:
        raise ModelValidationError("模型包含方法警告；冻结前必须填写覆盖理由")
    model_id = str(model_spec.get("modelId", ""))
    if not MODEL_ID.fullmatch(model_id):
        raise ModelValidationError("模型 ID 无效")
    version = repository.next_model_version(model_id)
    created_at = _utc_now()
    model_hash = canonical_model_hash(model_spec)
    path = (
        repository.settings.state_root
        / "projects"
        / "default"
        / "models"
        / model_id
        / f"v{version}.json"
    )
    response = {
        "schemaVersion": "1.0.0",
        "id": f"modelversion_{uuid.uuid4().hex[:16]}",
        "status": "frozen",
        "datasetId": dataset_id,
        "modelId": model_id,
        "version": version,
        "createdAt": created_at,
        "modelHash": model_hash,
        "overrideReason": cleaned_reason or None,
        "validation": validation,
        "modelSpec": model_spec,
    }
    _write_json_atomic(path, response)
    repository.record_model_version(
        dataset_id,
        model_id,
        version,
        created_at,
        path,
        model_hash,
        cleaned_reason or None,
    )
    return response
