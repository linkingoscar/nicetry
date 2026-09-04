from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import ApiServices, get_services
from app.services.analysis_index import AnalysisIndexService

router = APIRouter(tags=["analysis-index"])


class _IndexModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class AnalysisDocumentIndexRequest(_IndexModel):
    id: str
    project_id: str = Field(alias="projectId")
    title: str
    method_id: str = Field(alias="methodId")
    category_id: str = Field(alias="categoryId")
    source: Literal["empirical", "model", "advanced"]
    dataset_version_id: str = Field(alias="datasetVersionId")
    measurement_version_id: str | None = Field(default=None, alias="measurementVersionId")
    procedure: str | None = None
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")
    current_draft_id: str | None = Field(default=None, alias="currentDraftId")
    latest_run_id: str | None = Field(default=None, alias="latestRunId")
    primary_run_id: str | None = Field(default=None, alias="primaryRunId")
    pinned: bool = False
    archived: bool = False


class AnalysisDocumentPatchRequest(_IndexModel):
    title: str | None = None
    pinned: bool | None = None
    archived: bool | None = None
    primary_run_id: str | None = Field(default=None, alias="primaryRunId")


class AnalysisRunIndexRequest(_IndexModel):
    id: str | None = None
    run_id: str | None = Field(default=None, alias="runId")
    analysis_id: str = Field(alias="analysisId")
    source: Literal["empirical", "model", "advanced"]
    method_id: str = Field(alias="methodId")
    label: str
    category_id: str | None = Field(default=None, alias="categoryId")
    family: str | None = None
    model_id: str | None = Field(default=None, alias="modelId")
    procedure: str | None = None
    dataset_version_id: str = Field(alias="datasetVersionId")
    measurement_version_id: str | None = Field(default=None, alias="measurementVersionId")
    status: str | None = None
    result_id: str | None = Field(default=None, alias="resultId")
    report_id: str | None = Field(default=None, alias="reportId")
    created_at: str | None = Field(default=None, alias="createdAt")


def _service(services: ApiServices) -> AnalysisIndexService:
    return AnalysisIndexService(services.dataset_repository, services.settings)


@router.get("/projects/{project_id}/analysis-index", include_in_schema=False)
def get_analysis_index(
    project_id: str,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        return _service(services).get_index(project_id)
    except (LookupError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.put(
    "/projects/{project_id}/analysis-documents/{analysis_id}",
    include_in_schema=False,
)
def upsert_analysis_document(
    project_id: str,
    analysis_id: str,
    request: AnalysisDocumentIndexRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    if request.id != analysis_id or request.project_id != project_id:
        raise HTTPException(status_code=409, detail="AnalysisDocument 路径身份与载荷不一致")
    try:
        return _service(services).upsert_document(
            project_id,
            request.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.patch(
    "/projects/{project_id}/analysis-documents/{analysis_id}",
    include_in_schema=False,
)
def patch_analysis_document(
    project_id: str,
    analysis_id: str,
    request: AnalysisDocumentPatchRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        return _service(services).patch_document(
            project_id,
            analysis_id,
            request.model_dump(mode="json", by_alias=True, exclude_unset=True),
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/projects/{project_id}/analysis-runs", include_in_schema=False)
def register_analysis_run(
    project_id: str,
    request: AnalysisRunIndexRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        return _service(services).register_run(
            project_id,
            request.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
