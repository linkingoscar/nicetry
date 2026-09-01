from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.advanced_contracts import AdvancedAnalysisRequest
from app.api.dependencies import ApiServices, get_services
from app.api.responses import (
    AdvancedCapabilitiesResponse,
    AdvancedJobResponse,
    AdvancedResultResponse,
    AdvancedValidationResponse,
)
from app.contracts import ContractValidationError, validate_contract
from app.services.advanced_analysis import (
    AdvancedCapabilityNotImplemented,
    advanced_analysis_registry,
)
from app.services.advanced_export import create_advanced_export_bundle
from app.services.advanced_jobs import AdvancedQueueFullError
from app.services.advanced_runner import AdvancedExecutionError
from app.services.analysis_context import AnalysisContextResolutionError
from app.services.dataset_repository import DatasetNotFoundError
from app.services.repository_io import JsonObject

router = APIRouter(prefix="/advanced-analyses", tags=["advanced-analyses"])


@router.get("/capabilities", response_model=AdvancedCapabilitiesResponse)
def get_capabilities() -> JsonObject:
    return {
        "schemaVersion": "0.1.0",
        "capabilities": advanced_analysis_registry.capabilities(),
    }


@router.post("/validate", response_model=AdvancedValidationResponse)
def validate_analysis(
    request: AdvancedAnalysisRequest,
    services: ApiServices = Depends(get_services),
) -> JsonObject:
    try:
        validate_contract(
            request.spec.model_dump(by_alias=True),
            services.settings.advanced_spec_schema_path,
        )
    except ContractValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors) from error
    return advanced_analysis_registry.validate(request.spec)


@router.post("", response_model=AdvancedJobResponse, status_code=status.HTTP_202_ACCEPTED)
def start_analysis(
    request: AdvancedAnalysisRequest,
    services: ApiServices = Depends(get_services),
) -> JsonObject:
    try:
        validate_contract(
            request.spec.model_dump(by_alias=True),
            services.settings.advanced_spec_schema_path,
        )
        if request.dataset_id:
            services.dataset_repository.get_dataset(request.dataset_id)
            if request.spec.context_hash is None:
                raise AnalysisContextResolutionError(
                    "ANALYSIS_CONTEXT_REQUIRED",
                    "绑定数据版本的高级分析必须引用当前 resolved-analysis-context。",
                )
            if request.draft_id is None:
                raise AnalysisContextResolutionError(
                    "ANALYSIS_DRAFT_REQUIRED",
                    "上下文绑定的高级分析必须从当前 analysis draft 启动。",
                )
            draft = services.dataset_repository.get_analysis_draft(request.draft_id)
            if draft is None:
                raise AnalysisContextResolutionError(
                    "ANALYSIS_DRAFT_NOT_FOUND",
                    "分析草稿不存在或已被清理。",
                )
            if draft.get("datasetVersionId") != request.dataset_id:
                raise AnalysisContextResolutionError(
                    "ARTIFACT_DATASET_MISMATCH",
                    "分析草稿与运行请求引用了不同的数据版本。",
                )
            if draft.get("contextHash") != request.spec.context_hash:
                raise AnalysisContextResolutionError(
                    "ANALYSIS_CONTEXT_CHANGED",
                    "分析草稿与运行规格引用了不同的 contextHash，请重新创建草稿。",
                )
            if draft.get("validity") != "ready":
                raise AnalysisContextResolutionError(
                    "ANALYSIS_DRAFT_SUPERSEDED",
                    "当前分析草稿已过期或尚未就绪，请创建新的草稿。",
                )
            capability_slice = advanced_analysis_registry.slice_for_spec(request.spec)
            if capability_slice is None or draft.get("sliceId") != capability_slice.id:
                raise AnalysisContextResolutionError(
                    "ANALYSIS_DRAFT_METHOD_MISMATCH",
                    "运行规格与分析草稿登记的方法切片不一致。",
                )
        advanced_analysis_registry.assert_executable(request.spec)
        if request.dataset_id:
            return services.advanced_job_manager.start(
                request.spec,
                metadata={"analysisDraftId": request.draft_id},
                dataset_id=request.dataset_id,
            )
        return services.advanced_job_manager.start(request.spec)
    except DatasetNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ContractValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors) from error
    except AdvancedCapabilityNotImplemented as error:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "code": "CAPABILITY_NOT_IMPLEMENTED",
                "family": error.family,
                "capabilityId": (
                    error.capability_slice.id
                    if error.capability_slice is not None
                    else f"{error.family}.unclassified"
                ),
                "sliceId": error.capability_slice.id
                if error.capability_slice is not None
                else None,
                "implementationStatus": (
                    error.capability_slice.status
                    if error.capability_slice is not None
                    else error.capability.status
                ),
                "executionAvailable": False,
                "validationLevel": "unvalidated",
                "maturityLevel": "experimental",
                "publicationEligibility": "ineligible",
                "publicationEligibilityReason": "当前切片不可执行，因此不具备论文主分析资格。",
                "validationEvidence": {
                    "contractTests": False,
                    "applicabilityTests": False,
                    "failureFixtures": False,
                    "externalOracle": None,
                    "numericGoldenId": None,
                },
                "message": str(error),
            },
        ) from error
    except AdvancedExecutionError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": error.code, "message": error.message, "details": error.details},
        ) from error
    except AnalysisContextResolutionError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "code": error.code,
                "message": str(error),
                "details": error.details,
                "remediation": "重新读取 resolved-analysis-context，并从当前适用方法目录创建新的分析草稿。",
            },
        ) from error
    except AdvancedQueueFullError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error


@router.get("/{run_id}/export", response_class=FileResponse)
def export_job(
    run_id: str,
    include_data: bool = Query(default=False),
    services: ApiServices = Depends(get_services),
) -> FileResponse:
    try:
        state = services.advanced_job_manager.get(run_id)
        spec = services.advanced_job_manager.get_spec(run_id)
        result = services.advanced_job_manager.get_result(run_id)
        archive = create_advanced_export_bundle(
            run_id,
            state,
            spec,
            result,
            services.dataset_repository,
            services.settings,
            include_data,
        )
        return FileResponse(archive, media_type="application/zip", filename=archive.name)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/{run_id}", response_model=AdvancedJobResponse)
def get_job_status(
    run_id: str,
    services: ApiServices = Depends(get_services),
) -> JsonObject:
    try:
        return services.advanced_job_manager.get(run_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{run_id}/result", response_model=AdvancedResultResponse)
def get_job_result(
    run_id: str,
    services: ApiServices = Depends(get_services),
) -> JsonObject:
    try:
        return services.advanced_job_manager.get_result(run_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.delete("/{run_id}", response_model=AdvancedJobResponse)
def cancel_job(
    run_id: str,
    services: ApiServices = Depends(get_services),
) -> JsonObject:
    try:
        return services.advanced_job_manager.cancel(run_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
