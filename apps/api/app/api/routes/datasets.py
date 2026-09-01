from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.dependencies import ApiServices, get_services
from app.api.dto.empirical_spec_builder import build_empirical_analysis_options
from app.api.responses import (
    AnalysisJobResponse,
    DatasetMergeResponse,
    DatasetVersionResponse,
    EmpiricalSegmentResponse,
    MeasurementVersionResponse,
)
from app.api.schemas import (
    DatasetMergeRequest,
    DictionaryUpdateRequest,
    EmpiricalAnalysisRequest,
    MeasurementUpdateRequest,
)
from app.contracts import validate_contract
from app.data_quality_contracts import (
    AnalysisSampleVersion,
    AnalysisSampleVersionRequest,
    DataQualityRun,
    DataQualityRunRequest,
    QualityCasePage,
)
from app.services.analysis_context import AnalysisContextResolutionError
from app.services.analysis_jobs import AnalysisQueueFullError
from app.services.data_quality import (
    DataQualityError,
    create_analysis_sample,
    read_quality_case_page,
    read_sample_case_page,
    run_data_quality,
)
from app.services.dataset_import import (
    DatasetImportError,
    import_dataset,
)
from app.services.dataset_repository import (
    DatasetNotFoundError,
    DictionaryUpdateError,
    MeasurementNotFoundError,
)
from app.services.empirical_analysis import (
    EmpiricalAnalysisError,
    export_empirical_workbook,
)
from app.services.empirical_export import empirical_report_path
from app.services.empirical_report_segments import project_segment
from app.services.measurement import MeasurementError, build_measurement_version
from app.services.repository_io import JsonObject, read_json_safe

logger = logging.getLogger("researchpath")

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post(
    "/import",
    status_code=status.HTTP_201_CREATED,
    response_model=DatasetVersionResponse,
)
def import_data_file(
    file: UploadFile = File(...),
    selected_sheet: str | None = Query(None, alias="selectedSheet"),
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        dataset = import_dataset(
            source=file.file,
            filename=file.filename or "uploaded-data",
            settings=services.settings,
            repository=services.dataset_repository,
            selected_sheet=selected_sheet,
        )
        validate_contract(dataset, services.settings.dataset_schema_path)
        return dataset
    except DatasetImportError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        file.file.close()


@router.get("/{dataset_id}", response_model=DatasetVersionResponse)
def get_dataset(dataset_id: str, services: ApiServices = Depends(get_services)) -> JsonObject:
    try:
        dataset = services.dataset_repository.get_dataset(dataset_id)
        validate_contract(dataset, services.settings.dataset_schema_path)
        return dataset
    except DatasetNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/{dataset_id}/quality-runs",
    status_code=status.HTTP_201_CREATED,
    response_model=DataQualityRun,
)
def create_quality_run(
    dataset_id: str,
    request: DataQualityRunRequest,
    services: ApiServices = Depends(get_services),
) -> DataQualityRun:
    try:
        return run_data_quality(dataset_id, request, services.settings, services.dataset_repository)
    except DatasetNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DataQualityError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/{dataset_id}/quality-runs",
    response_model=list[DataQualityRun],
)
def list_quality_runs(
    dataset_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    services: ApiServices = Depends(get_services),
) -> list[dict[str, object]]:
    try:
        services.dataset_repository.get_dataset(dataset_id)
        runs = services.dataset_repository.list_data_quality_runs(dataset_id)
        return runs[offset : offset + limit]
    except (DatasetNotFoundError, LookupError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/{dataset_id}/quality-runs/{run_id}/cases",
    response_model=QualityCasePage,
)
def get_quality_cases(
    dataset_id: str,
    run_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    services: ApiServices = Depends(get_services),
) -> QualityCasePage:
    try:
        return read_quality_case_page(
            dataset_id, run_id, services.settings, services.dataset_repository, offset, limit
        )
    except (DatasetNotFoundError, LookupError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DataQualityError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/{dataset_id}/sample-versions",
    status_code=status.HTTP_201_CREATED,
    response_model=AnalysisSampleVersion,
)
def create_sample_version(
    dataset_id: str,
    request: AnalysisSampleVersionRequest,
    services: ApiServices = Depends(get_services),
) -> AnalysisSampleVersion:
    try:
        return create_analysis_sample(
            dataset_id, request, services.settings, services.dataset_repository
        )
    except (DatasetNotFoundError, LookupError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DataQualityError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/{dataset_id}/sample-versions",
    response_model=list[AnalysisSampleVersion],
)
def list_sample_versions(
    dataset_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    services: ApiServices = Depends(get_services),
) -> list[dict[str, object]]:
    try:
        services.dataset_repository.get_dataset(dataset_id)
        samples = services.dataset_repository.list_analysis_samples(dataset_id)
        return samples[offset : offset + limit]
    except (DatasetNotFoundError, LookupError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/{dataset_id}/sample-versions/{sample_id}",
    response_model=AnalysisSampleVersion,
)
def get_sample_version(
    dataset_id: str,
    sample_id: str,
    services: ApiServices = Depends(get_services),
) -> dict[str, object]:
    try:
        return services.dataset_repository.get_analysis_sample(dataset_id, sample_id)
    except (DatasetNotFoundError, LookupError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/{dataset_id}/sample-versions/{sample_id}/cases",
    response_model=QualityCasePage,
)
def get_sample_cases(
    dataset_id: str,
    sample_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    services: ApiServices = Depends(get_services),
) -> QualityCasePage:
    try:
        return read_sample_case_page(
            dataset_id, sample_id, services.settings, services.dataset_repository, offset, limit
        )
    except (DatasetNotFoundError, LookupError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DataQualityError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{dataset_id}/dictionary", response_model=DatasetVersionResponse)
def update_dictionary(
    dataset_id: str,
    request: DictionaryUpdateRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    if not request.variables:
        raise HTTPException(status_code=422, detail="至少确认一个变量")
    updates = {variable.id: variable.confirmed_type for variable in request.variables}
    try:
        dataset = services.dataset_repository.confirm_dictionary(dataset_id, updates)
        validate_contract(dataset, services.settings.dataset_schema_path)
        return dataset
    except DatasetNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DictionaryUpdateError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{dataset_id}/measurement", response_model=MeasurementVersionResponse)
def update_measurement(
    dataset_id: str,
    request: MeasurementUpdateRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    constructs = [
        {
            "id": construct.id,
            "name": construct.name,
            "itemIds": construct.item_ids,
            "reverseItemIds": construct.reverse_item_ids,
            "theoreticalMinimum": construct.theoretical_minimum,
            "theoreticalMaximum": construct.theoretical_maximum,
            "aggregation": construct.aggregation,
            "minimumValidProportion": construct.minimum_valid_proportion,
        }
        for construct in request.constructs
    ]
    try:
        measurement = build_measurement_version(
            dataset_id,
            constructs,
            services.dataset_repository,
            request.change_note,
        )
        validate_contract(measurement, services.settings.measurement_schema_path)
        return measurement
    except DatasetNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except MeasurementError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{dataset_id}/measurement", response_model=MeasurementVersionResponse)
def get_latest_measurement(
    dataset_id: str,
    version: int | None = Query(default=None),
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        measurement = services.dataset_repository.get_measurement(dataset_id, version)
        validate_contract(measurement, services.settings.measurement_schema_path)
        return measurement
    except (DatasetNotFoundError, MeasurementNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/{dataset_id}/measurements/{version}/empirical-analysis",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AnalysisJobResponse,
)
def analyse_questionnaire_empirically(
    dataset_id: str,
    version: int | None,
    request: EmpiricalAnalysisRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        options = build_empirical_analysis_options(request)
        return services.analysis_job_manager.start_empirical(
            dataset_id,
            version,
            options,
        )
    except (DatasetNotFoundError, MeasurementNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except AnalysisContextResolutionError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "code": error.code,
                "message": str(error),
                "remediation": "刷新当前分析上下文并重新确认数据结构角色。",
            },
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except AnalysisQueueFullError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error


@router.get(
    "/{dataset_id}/measurements/{version}/empirical-analyses/{report_id}/segments/{segment}",
    response_model=EmpiricalSegmentResponse,
    response_model_exclude_none=True,
)
def get_empirical_analysis_segment(
    dataset_id: str,
    version: int | None,
    report_id: str,
    segment: str,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        report_path = empirical_report_path(
            dataset_id, version, report_id, services.settings
        )
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="报告不存在")
        report = read_json_safe(report_path)
        try:
            return project_segment(report, segment)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
    except HTTPException:
        raise
    except EmpiricalAnalysisError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Failed to read empirical report segment")
        raise HTTPException(
            status_code=500,
            detail="读取实证报告失败；诊断信息已写入服务日志，请通过任务状态进一步排查。",
        ) from error


@router.get(
    "/{dataset_id}/measurements/{version}/empirical-analyses/{report_id}/export",
    response_class=FileResponse,
)
def export_questionnaire_empirical_tables(
    dataset_id: str,
    version: int | None,
    report_id: str,
    services: ApiServices = Depends(get_services),
) -> FileResponse:
    try:
        workbook = export_empirical_workbook(dataset_id, version, report_id, services.settings)
        return FileResponse(
            workbook,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=workbook.name,
        )
    except EmpiricalAnalysisError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{dataset_id}/empirical-analysis", status_code=status.HTTP_202_ACCEPTED, response_model=AnalysisJobResponse)
def analyse_raw_variables(
    dataset_id: str, request: EmpiricalAnalysisRequest, services: ApiServices = Depends(get_services),
) -> JsonObject:
    return analyse_questionnaire_empirically(dataset_id, None, request, services)


@router.get("/{dataset_id}/empirical-analyses/{report_id}/segments/{segment}", response_model=EmpiricalSegmentResponse, response_model_exclude_none=True)
def get_raw_empirical_segment(
    dataset_id: str, report_id: str, segment: str, services: ApiServices = Depends(get_services),
) -> JsonObject:
    return get_empirical_analysis_segment(dataset_id, None, report_id, segment, services)


@router.get("/{dataset_id}/empirical-analyses/{report_id}/export", response_class=FileResponse)
def export_raw_empirical_tables(
    dataset_id: str, report_id: str, services: ApiServices = Depends(get_services),
) -> FileResponse:
    return export_questionnaire_empirical_tables(dataset_id, None, report_id, services)


@router.post(
    "/{dataset_id}/merge",
    status_code=status.HTTP_201_CREATED,
    response_model=DatasetMergeResponse,
)
def merge_dataset_endpoint(
    dataset_id: str,
    request_data: DatasetMergeRequest,
    services: ApiServices = Depends(get_services),
) -> dict[str, object]:
    try:
        new_dataset, summary = services.dataset_repository.execute_dataset_merge(
            dataset_id,
            request_data.target_dataset_id,
            request_data.subject_key,
            request_data.wave_key,
        )
        validate_contract(new_dataset, services.settings.dataset_schema_path)
        return {"dataset": new_dataset, "report": summary}

    except DatasetNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DatasetImportError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        logger.exception("Dataset merge failed")
        raise HTTPException(
            status_code=400,
            detail="合并数据集失败；诊断信息已写入服务日志，请检查文件结构后重试。",
        ) from error
