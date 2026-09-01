from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import ApiServices, get_services
from app.protocol_contracts import (
    HypothesisInput,
    ProtocolDeviation,
    ResearchProgramSpec,
    StudyProtocolIndex,
    StudyProtocolSpec,
)

router = APIRouter(prefix="/programs", tags=["protocols"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ResearchProgramSpec,
)
def create_or_update_program(
    program: ResearchProgramSpec,
    services: ApiServices = Depends(get_services),
) -> ResearchProgramSpec:
    try:
        services.dataset_repository.record_program(program)
        return program
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法创建或更新研究计划: {error}",
        ) from error


@router.get(
    "/{program_id}",
    response_model=ResearchProgramSpec,
)
def get_program(
    program_id: str,
    services: ApiServices = Depends(get_services),
) -> ResearchProgramSpec:
    try:
        return services.dataset_repository.get_program(program_id)
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.post(
    "/{program_id}/protocols/{study_id}/draft",
    status_code=status.HTTP_201_CREATED,
    response_model=StudyProtocolSpec,
)
def save_protocol_draft(
    program_id: str,
    study_id: str,
    protocol: StudyProtocolSpec,
    services: ApiServices = Depends(get_services),
) -> StudyProtocolSpec:
    try:
        services.dataset_repository.record_protocol_draft(program_id, study_id, protocol)
        return protocol
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.get(
    "/{program_id}/protocols/{study_id}/draft",
    response_model=StudyProtocolSpec,
)
def get_protocol_draft(
    program_id: str,
    study_id: str,
    services: ApiServices = Depends(get_services),
) -> StudyProtocolSpec:
    try:
        return services.dataset_repository.get_protocol_draft(program_id, study_id)
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.post(
    "/{program_id}/protocols/{study_id}/freeze",
    status_code=status.HTTP_200_OK,
)
def freeze_protocol_version(
    program_id: str,
    study_id: str,
    version_id: str,
    preregistration_url: str | None = None,
    preregistration_sha256: str | None = None,
    services: ApiServices = Depends(get_services),
) -> dict[str, str]:
    try:
        frozen_hash = services.dataset_repository.freeze_protocol(
            program_id, study_id, version_id, preregistration_url, preregistration_sha256
        )
        return {"status": "frozen", "versionId": version_id, "frozenHash": frozen_hash}
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.get(
    "/{program_id}/protocols/{study_id}/versions/{version_id}",
    response_model=StudyProtocolSpec,
)
def get_protocol_version(
    program_id: str,
    study_id: str,
    version_id: str,
    services: ApiServices = Depends(get_services),
) -> StudyProtocolSpec:
    try:
        return services.dataset_repository.get_protocol_version(program_id, study_id, version_id)
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.post(
    "/{program_id}/protocols/{study_id}/hypotheses",
    status_code=status.HTTP_201_CREATED,
    response_model=HypothesisInput,
)
def add_or_update_hypothesis(
    program_id: str,
    study_id: str,
    hyp: HypothesisInput,
    services: ApiServices = Depends(get_services),
) -> HypothesisInput:
    try:
        services.dataset_repository.record_hypothesis(program_id, study_id, hyp)
        return hyp
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.get(
    "/{program_id}/protocols/{study_id}/hypotheses",
    response_model=list[HypothesisInput],
)
def list_hypotheses(
    program_id: str,
    study_id: str,
    services: ApiServices = Depends(get_services),
) -> list[HypothesisInput]:
    try:
        return services.dataset_repository.list_hypotheses_for_study(program_id, study_id)
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.get(
    "/{program_id}/studies",
    response_model=list[StudyProtocolIndex],
)
def list_studies(
    program_id: str,
    services: ApiServices = Depends(get_services),
) -> list[StudyProtocolIndex]:
    try:
        return services.dataset_repository.list_protocol_studies(program_id)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post(
    "/{program_id}/protocols/{study_id}/verify-deviation",
    response_model=list[ProtocolDeviation],
)
def verify_deviation(
    program_id: str,
    study_id: str,
    version_id: str,
    analysis_spec: dict[str, object],
    analysis_id: str | None = None,
    reason: str | None = None,
    services: ApiServices = Depends(get_services),
) -> list[ProtocolDeviation]:
    try:
        return services.dataset_repository.verify_protocol_deviation(
            program_id, study_id, version_id, analysis_spec, analysis_id, reason
        )
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get(
    "/{program_id}/protocols/{study_id}/versions/{version_id}/deviations",
    response_model=list[ProtocolDeviation],
)
def list_deviations(
    program_id: str,
    study_id: str,
    version_id: str,
    services: ApiServices = Depends(get_services),
) -> list[ProtocolDeviation]:
    try:
        return services.dataset_repository.list_protocol_deviations(
            program_id, study_id, version_id
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
