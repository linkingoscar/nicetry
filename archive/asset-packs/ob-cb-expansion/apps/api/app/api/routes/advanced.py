from __future__ import annotations

from typing import Any

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
from app.services.advanced_analysis import (
    AdvancedCapabilityNotImplemented,
    advanced_analysis_registry,
)
from app.services.advanced_export import create_advanced_export_bundle
from app.services.advanced_runner import AdvancedExecutionError
from app.services.dataset_repository import DatasetNotFoundError

router = APIRouter(prefix="/advanced-analyses", tags=["advanced-analyses"])


@router.get("/capabilities", response_model=AdvancedCapabilitiesResponse)
def get_capabilities() -> dict[str, Any]:
    return {
        "schemaVersion": "0.1.0",
        "capabilities": advanced_analysis_registry.capabilities(),
    }


@router.post("/validate", response_model=AdvancedValidationResponse)
def validate_analysis(request: AdvancedAnalysisRequest) -> dict[str, Any]:
    return advanced_analysis_registry.validate(request.spec)


@router.post("", response_model=AdvancedJobResponse, status_code=status.HTTP_202_ACCEPTED)
def start_analysis(
    request: AdvancedAnalysisRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        if request.dataset_id:
            services.dataset_repository.get_dataset(request.dataset_id)
        advanced_analysis_registry.assert_executable(request.spec)
        return services.advanced_job_manager.start(request.spec)
    except DatasetNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
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
                "message": str(error),
            },
        ) from error
    except AdvancedExecutionError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": error.code, "message": error.message, "details": error.details},
        ) from error


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
) -> dict[str, Any]:
    try:
        return services.advanced_job_manager.get(run_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{run_id}/result", response_model=AdvancedResultResponse)
def get_job_result(
    run_id: str,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
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
) -> dict[str, Any]:
    try:
        return services.advanced_job_manager.cancel(run_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
