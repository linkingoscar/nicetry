from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.services.advanced_jobs import AdvancedJobManager
from app.services.analysis_context import AnalysisContextService
from app.services.analysis_jobs import AnalysisJobManager
from app.services.capability_applicability import CapabilityApplicabilityRegistry
from app.services.dataset_repository import DatasetRepository
from app.services.r_workers import RWorkerPool
from app.services.workflow_services import WorkflowServices
from app.settings import Settings


@dataclass(frozen=True)
class ApiServices:
    """Application-scoped dependencies exposed to route modules."""

    settings: Settings
    dataset_repository: DatasetRepository
    analysis_context_service: AnalysisContextService
    workflow_services: WorkflowServices
    capability_applicability_service: CapabilityApplicabilityRegistry
    analysis_job_manager: AnalysisJobManager
    advanced_job_manager: AdvancedJobManager
    r_worker_pool: RWorkerPool


def get_services(request: Request) -> ApiServices:
    services = getattr(request.app.state, "services", None)
    if not isinstance(services, ApiServices):
        raise RuntimeError("ResearchPath API services have not been initialized")
    return services
