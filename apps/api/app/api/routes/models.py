from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import ApiServices, get_services
from app.api.responses import ModelValidationResponse, ModelVersionResponse
from app.api.schemas import ModelDraftRequest, ModelFreezeRequest
from app.contracts import ContractValidationError, validate_contract
from app.semantics import SemanticValidationError, validate_model_semantics
from app.services.analysis_context import AnalysisContextResolutionError
from app.services.dataset_repository import (
    DatasetNotFoundError,
    MeasurementNotFoundError,
    ModelDraftNotFoundError,
)
from app.services.model_draft_validation import incomplete_draft_validation, validate_draft_contract
from app.services.model_service import (
    ModelValidationError,
    freeze_model,
    save_model_draft,
    validate_model_context,
    validate_model_for_dataset_request,
)

router = APIRouter(tags=["models"])


@router.post("/models/validate", response_model=ModelValidationResponse)
def validate_model(
    model_spec: dict[str, Any], services: ApiServices = Depends(get_services)
) -> dict[str, Any]:
    try:
        validate_contract(model_spec, services.settings.model_schema_path)
        validation = validate_model_semantics(model_spec)
        if not validation["valid"]:
            raise SemanticValidationError(validation["errors"])
    except (ContractValidationError, SemanticValidationError) as error:
        raise HTTPException(status_code=422, detail=error.errors) from error
    return validation


@router.post(
    "/datasets/{dataset_id}/models/validate",
    response_model=ModelValidationResponse,
)
def validate_dataset_model(
    dataset_id: str,
    request: ModelDraftRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        return validate_model_for_dataset_request(
            dataset_id,
            request.model_spec,
            services.dataset_repository,
            services.analysis_context_service,
            services.settings,
        )
    except (DatasetNotFoundError, MeasurementNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except AnalysisContextResolutionError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "code": error.code,
                "message": str(error),
                "remediation": "刷新当前上下文并重新创建模型草稿。",
            },
        ) from error


@router.put(
    "/datasets/{dataset_id}/models/{model_id}/draft",
    response_model=ModelVersionResponse,
)
def update_model_draft(
    dataset_id: str,
    model_id: str,
    request: ModelDraftRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    if request.model_spec.get("modelId") != model_id:
        raise HTTPException(status_code=422, detail="路径中的模型 ID 与 ModelSpec 不一致")
    try:
        # 1. Schema check
        incomplete_errors = validate_draft_contract(request.model_spec, services.settings.model_schema_path)
        validate_model_context(dataset_id, request.model_spec, services.analysis_context_service)

        # 2. Structural/Semantic check
        semantic_val = validate_model_semantics(request.model_spec)

        # 3. Try to get cached full validation
        dataset = services.dataset_repository.get_dataset(dataset_id)
        measurement = services.dataset_repository.get_measurement(dataset_id)
        dataset_sha = dataset.get("originalFile", {}).get("sha256", "")
        measurement_version = measurement.get("version", 0)

        from app.contracts import compute_analysis_signature
        from app.services.dataset_repository import DatasetRepository

        analysis_sig = compute_analysis_signature(request.model_spec)
        cache_key = (dataset_sha, measurement_version, analysis_sig)

        cached_val = DatasetRepository.get_precheck_cache_item(cache_key)
        if incomplete_errors:
            validation = incomplete_draft_validation(incomplete_errors)
        elif cached_val is not None and cached_val.get("catalogVersion") == "5.0":
            validation = cached_val
        else:
            validation = {
                **semantic_val,
                "sampleFlow": None,
            }

        return save_model_draft(
            dataset_id,
            request.model_spec,
            validation,
            services.dataset_repository,
        )
    except (DatasetNotFoundError, MeasurementNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except AnalysisContextResolutionError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "code": error.code,
                "message": str(error),
                "remediation": "刷新当前上下文并重新创建模型草稿。",
            },
        ) from error
    except ContractValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors) from error
    except ModelValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/datasets/{dataset_id}/models/{model_id}/draft",
    response_model=ModelVersionResponse | None,
)
def get_model_draft(
    dataset_id: str,
    model_id: str,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any] | None:
    try:
        services.dataset_repository.get_dataset(dataset_id)
    except DatasetNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    try:
        return services.dataset_repository.get_model_draft(dataset_id, model_id)
    except ModelDraftNotFoundError:
        return None


@router.post(
    "/datasets/{dataset_id}/models/{model_id}/freeze",
    response_model=ModelVersionResponse,
)
def create_frozen_model(
    dataset_id: str,
    model_id: str,
    request: ModelFreezeRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    if request.model_spec.get("modelId") != model_id:
        raise HTTPException(status_code=422, detail="路径中的模型 ID 与 ModelSpec 不一致")
    try:
        validation = validate_model_for_dataset_request(
            dataset_id,
            request.model_spec,
            services.dataset_repository,
            services.analysis_context_service,
            services.settings,
        )
        return freeze_model(
            dataset_id,
            request.model_spec,
            validation,
            request.override_reason,
            services.dataset_repository,
        )
    except (DatasetNotFoundError, MeasurementNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except AnalysisContextResolutionError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "code": error.code,
                "message": str(error),
                "remediation": "刷新当前上下文并重新创建模型草稿。",
            },
        ) from error
    except ModelValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
