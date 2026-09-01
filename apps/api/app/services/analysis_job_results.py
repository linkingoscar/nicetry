from __future__ import annotations

from app.services.dataset_repository import DatasetRepository
from app.services.status_model import apply_status_model
from app.services.study_plans import StudyPlanService


class AnalysisResultReader:
    def __init__(self, repository: DatasetRepository, study_plan_service: StudyPlanService) -> None:
        self.repository = repository
        self.study_plan_service = study_plan_service

    def get_result(self, run_id: str, state: dict[str, object]) -> dict[str, object]:
        if state.get("jobKind") == "empirical":
            if state.get("status") != "succeeded" or not state.get("resultPath"):
                raise ValueError("实证分析尚未成功完成")
            result = self.repository.get_empirical_report(state)
        else:
            result = self.repository.get_analysis_result(run_id)
        apply_status_model(result)
        binding = result.get("studyPlanBinding")
        if not isinstance(binding, dict):
            return result
        dataset = self.repository.get_dataset(str(state["datasetId"]))
        current_plan = self.repository.get_latest_study_plan(str(dataset["projectId"]))
        original_file = dataset.get("originalFile")
        current_data_sha256 = (
            str(original_file.get("sha256", "")) if isinstance(original_file, dict) else ""
        )
        current_identity = self.study_plan_service.binding.current_artifact_identity(
            str(state["datasetId"]), binding
        )
        refreshed = self.study_plan_service.binding.refresh_result_binding(
            result,
            current_plan=current_plan,
            current_data_sha256=current_data_sha256,
            current_sample_version_id=current_identity["sampleVersionId"],
            current_sample_hash=current_identity["sampleHash"],
            current_measurement_version_id=current_identity["measurementVersionId"],
            current_measurement_hash=current_identity["measurementHash"],
        )
        return apply_status_model(refreshed)
