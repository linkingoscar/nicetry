from __future__ import annotations

from dataclasses import dataclass

from app.services.analysis_context import AnalysisContextService
from app.services.analysis_drafts import AnalysisDraftService
from app.services.capability_applicability import CapabilityApplicabilityRegistry
from app.services.dataset_repository import DatasetRepository
from app.services.imputation_plans import ImputationPlanService
from app.services.study_plans import StudyPlanService


@dataclass(frozen=True)
class WorkflowServices:
    analysis_draft: AnalysisDraftService
    imputation_plan: ImputationPlanService
    study_plan: StudyPlanService

    @classmethod
    def build(
        cls,
        repository: DatasetRepository,
        context_service: AnalysisContextService,
        registry: CapabilityApplicabilityRegistry,
    ) -> "WorkflowServices":
        return cls(
            analysis_draft=AnalysisDraftService(repository, context_service, registry),
            imputation_plan=ImputationPlanService(repository, context_service),
            study_plan=StudyPlanService(repository, registry),
        )
