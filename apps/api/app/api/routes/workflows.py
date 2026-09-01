from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import ApiServices, get_services
from app.imputation_plan_contracts import (
    ImputationCompatibilityResponse,
    ImputationDatasetVersion,
    ImputationPlanCreateRequest,
    ImputationPlanVersion,
)
from app.services.advanced_jobs import AdvancedQueueFullError
from app.services.dataset_repository import DatasetNotFoundError
from app.services.imputation_plans import ImputationPlanError
from app.services.repository_io import JsonObject
from app.study_plan_contracts import (
    StudyPlanCreateRequest,
    StudyPlanDatasetMapping,
    StudyPlanDatasetMappingRequest,
    StudyPlanMutation,
    StudyPlanVersion,
)

router = APIRouter(tags=["analysis-workflows"])


def _workflow_error(error: ValueError, remediation: str) -> HTTPException:
    code = getattr(error, "code", None) or str(error).split(":", 1)[0]
    return HTTPException(
        status_code=409,
        detail={"code": code, "message": str(error), "details": {}, "remediation": remediation},
    )


@router.post(
    "/datasets/{dataset_id}/imputation-plans",
    response_model=ImputationPlanVersion,
    status_code=status.HTTP_201_CREATED,
)
def create_imputation_plan(
    dataset_id: str,
    request: ImputationPlanCreateRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, object]:
    try:
        return services.workflow_services.imputation_plan.create(
            dataset_id, request.model_dump(by_alias=True)
        )
    except DatasetNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ImputationPlanError as error:
        raise _workflow_error(error, "重新读取当前上下文并重建插补计划。") from error


@router.get("/imputation-plans/{plan_id}", response_model=ImputationPlanVersion)
def get_imputation_plan(
    plan_id: str, services: ApiServices = Depends(get_services)
) -> dict[str, object]:
    try:
        return services.workflow_services.imputation_plan.get(plan_id)
    except ImputationPlanError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/imputation-plans/{plan_id}/run")
def run_imputation_plan(
    plan_id: str, services: ApiServices = Depends(get_services)
) -> JsonObject:
    try:
        return services.workflow_services.imputation_plan.run(
            plan_id, services.advanced_job_manager
        )
    except ImputationPlanError as error:
        raise _workflow_error(error, "重新确认插补计划与当前分析草稿的兼容性。") from error
    except AdvancedQueueFullError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except ValueError as error:
        raise _workflow_error(error, "检查插补变量、核心模型和资源预算。") from error


@router.get(
    "/imputation-datasets/{imputation_dataset_id}",
    response_model=ImputationDatasetVersion,
)
def get_imputation_dataset_version(
    imputation_dataset_id: str, services: ApiServices = Depends(get_services)
) -> dict[str, object]:
    stored = services.dataset_repository.get_imputation_dataset_version(imputation_dataset_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="插补数据版本不存在")
    return stored


@router.get(
    "/imputation-plans/{plan_id}/compatible-analyses",
    response_model=ImputationCompatibilityResponse,
)
def get_compatible_analyses(
    plan_id: str,
    draft_id: str = Query(alias="draftId"),
    services: ApiServices = Depends(get_services),
) -> dict[str, object]:
    try:
        return services.workflow_services.imputation_plan.compatible_analyses(plan_id, draft_id)
    except ImputationPlanError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/imputation-datasets/{imputation_dataset_id}/compatibility",
    response_model=ImputationCompatibilityResponse,
)
def get_imputation_dataset_compatibility(
    imputation_dataset_id: str,
    draft_id: str = Query(alias="draftId"),
    services: ApiServices = Depends(get_services),
) -> dict[str, object]:
    try:
        return services.workflow_services.imputation_plan.compatible_dataset(
            imputation_dataset_id, draft_id
        )
    except ImputationPlanError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/projects/{project_id}/study-plans",
    response_model=StudyPlanVersion,
    status_code=status.HTTP_201_CREATED,
)
def create_study_plan(
    project_id: str,
    request: StudyPlanCreateRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, object]:
    try:
        return services.workflow_services.study_plan.create(
            project_id, request.payload
        )
    except ValueError as error:
        raise _workflow_error(error, "补充研究目标、设计和估计对象后重试。") from error


@router.put("/study-plans/{plan_id}", response_model=StudyPlanVersion)
def update_study_plan(
    plan_id: str,
    request: StudyPlanMutation,
    services: ApiServices = Depends(get_services),
) -> dict[str, object]:
    try:
        return services.workflow_services.study_plan.update(
            plan_id, request.expected_revision, request.payload
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise _workflow_error(error, "读取最新计划版本；冻结版本请创建下一 revision。") from error


@router.post("/study-plans/{plan_id}/revisions", response_model=StudyPlanVersion)
def create_study_plan_revision(
    plan_id: str,
    request: StudyPlanMutation,
    services: ApiServices = Depends(get_services),
) -> dict[str, object]:
    try:
        return services.workflow_services.study_plan.revise(
            plan_id, request.expected_revision, request.payload
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise _workflow_error(error, "读取当前计划 revision，并提交新的 v2 计划草稿。") from error


@router.post("/study-plans/{plan_id}/freeze", response_model=StudyPlanVersion)
def freeze_study_plan(
    plan_id: str, services: ApiServices = Depends(get_services)
) -> dict[str, object]:
    try:
        return services.workflow_services.study_plan.freeze(plan_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise _workflow_error(error, "选择已登记且可执行的计划方法后重试。") from error


@router.post(
    "/study-plans/{plan_id}/map-dataset",
    response_model=StudyPlanDatasetMapping,
)
def map_study_plan_dataset(
    plan_id: str,
    request: StudyPlanDatasetMappingRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, object]:
    try:
        return services.workflow_services.study_plan.map_dataset(
            plan_id,
            request.dataset_version_id,
            request.mapping,
            request.status,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise _workflow_error(error, "检查实际变量映射和计划偏离说明后重试。") from error
