from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.api.dependencies import ApiServices, get_services
from app.api.responses import (
    AnalysisJobResponse,
    CleanupResponse,
    EmpiricalReportResponse,
    ResultBundleResponse,
)
from app.api.schemas import AnalysisRequest, AnalysisRunRequest
from app.contracts import ContractValidationError
from app.semantics import SemanticValidationError
from app.services.analysis_context import AnalysisContextResolutionError
from app.services.analysis_jobs import AnalysisQueueFullError
from app.services.dataset_repository import (
    DatasetNotFoundError,
    ModelVersionNotFoundError,
)
from app.services.export_bundle import create_export_bundle
from app.services.mediation_demo import DemoDatasetNotFound, run_demo_mediation
from app.services.r_engine import EngineExecutionError

router = APIRouter(tags=["analyses"])


@router.post(
    "/datasets/{dataset_id}/models/{model_id}/versions/{version}/analysis",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AnalysisJobResponse,
)
def analyse_frozen_model(
    dataset_id: str,
    model_id: str,
    version: int,
    request: AnalysisRunRequest | None = None,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        binding = None
        if request is not None and request.study_plan_binding is not None:
            binding = request.study_plan_binding.model_dump(by_alias=True)
        return services.analysis_job_manager.start(dataset_id, model_id, version, binding)
    except (DatasetNotFoundError, ModelVersionNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except LookupError as error:
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
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except AnalysisQueueFullError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error


@router.post("/analyses/mediation", response_model=ResultBundleResponse)
def analyse_mediation(
    request: AnalysisRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        return run_demo_mediation(
            dataset_id=request.dataset_id,
            model_spec=request.model_spec,
            settings=services.settings,
            worker_pool=services.r_worker_pool,
        )
    except DemoDatasetNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ContractValidationError, SemanticValidationError) as error:
        raise HTTPException(status_code=422, detail=error.errors) from error
    except EngineExecutionError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/analyses/{run_id}", response_model=AnalysisJobResponse)
def get_analysis_job(run_id: str, services: ApiServices = Depends(get_services)) -> dict[str, Any]:
    try:
        return services.analysis_job_manager.get(run_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/analyses/{run_id}", response_model=AnalysisJobResponse)
def cancel_analysis_job(
    run_id: str, services: ApiServices = Depends(get_services)
) -> dict[str, Any]:
    try:
        return services.analysis_job_manager.cancel(run_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/analyses/{run_id}/export", response_class=FileResponse)
def export_analysis_job(
    run_id: str,
    include_data: bool = Query(default=False),
    services: ApiServices = Depends(get_services),
) -> FileResponse:
    try:
        state = services.analysis_job_manager.get(run_id)
        archive = create_export_bundle(
            run_id,
            state,
            services.dataset_repository,
            services.settings,
            include_data,
        )
        return FileResponse(
            archive,
            media_type="application/zip",
            filename=archive.name,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


class CleanupRequest(BaseModel):
    keep_count: int | None = Field(default=None, ge=0)
    older_than_days: float | None = Field(default=None, ge=0)


def _progress_event(state: dict[str, object]) -> dict[str, object]:
    """Project job state onto a minimal public SSE event.

    Only fields the UI needs for progress rendering leave the endpoint:
    no raw error text, options, context lineage or internal result paths.
    """
    event: dict[str, object] = {
        "id": state.get("id"),
        "status": state.get("status"),
        "stage": state.get("stage"),
        "progress": state.get("progress"),
        "completedReplicates": state.get("completedReplicates"),
        "totalReplicates": state.get("totalReplicates"),
        "errorCode": state.get("errorCode"),
    }
    metadata = state.get("metadata")
    if isinstance(metadata, dict) and metadata.get("contextHash"):
        event["metadata"] = {"contextHash": metadata["contextHash"]}
    return event


@router.get(
    "/analyses/{run_id}/result",
    response_model=ResultBundleResponse | EmpiricalReportResponse,
)
def get_analysis_result(
    run_id: str, services: ApiServices = Depends(get_services)
) -> dict[str, Any]:
    try:
        return services.analysis_job_manager.get_result(run_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/analyses/{run_id}/progress", response_class=StreamingResponse)
async def stream_analysis_progress(
    run_id: str,
    services: ApiServices = Depends(get_services),
) -> StreamingResponse:
    try:
        initial_state = services.analysis_job_manager.get(run_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    async def event_generator():
        if initial_state.get("status") in {"succeeded", "failed", "cancelled"}:
            yield f"data: {json.dumps(_progress_event(initial_state), ensure_ascii=False)}\n\n"
            return

        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        if not services.analysis_job_manager.register_listener(run_id, queue, loop):
            # Listener budget exhausted: client falls back to its polling path.
            yield f"data: {json.dumps(_progress_event(initial_state), ensure_ascii=False)}\n\n"
            return
        yield f"data: {json.dumps(_progress_event(initial_state), ensure_ascii=False)}\n\n"
        try:
            while True:
                try:
                    state = await asyncio.wait_for(queue.get(), timeout=3.0)
                    yield f"data: {json.dumps(_progress_event(state), ensure_ascii=False)}\n\n"
                    if state.get("status") in {"succeeded", "failed", "cancelled"}:
                        break
                except asyncio.TimeoutError:
                    current = services.analysis_job_manager.get(run_id)
                    if current.get("status") in {"succeeded", "failed", "cancelled"}:
                        yield f"data: {json.dumps(_progress_event(current), ensure_ascii=False)}\n\n"
                        break
        finally:
            services.analysis_job_manager.unregister_listener(run_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/analyses/cleanup", response_model=CleanupResponse)
def cleanup_analysis_runs(
    request: CleanupRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    deleted = services.analysis_job_manager.cleanup_runs(
        keep_count=request.keep_count,
        older_than_days=request.older_than_days,
    )
    return {"deleted": deleted}
