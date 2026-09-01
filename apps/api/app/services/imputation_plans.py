from __future__ import annotations

from typing import cast

from app.advanced_contracts import MultipleImputationSpec
from app.services.advanced_jobs import AdvancedJobManager
from app.services.analysis_context import AnalysisContextResolutionError, AnalysisContextService
from app.services.canonical_identity import canonical_sha256
from app.services.dataset_repository import DatasetRepository


class ImputationPlanError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class ImputationPlanService:
    def __init__(self, repository: DatasetRepository, context_service: AnalysisContextService) -> None:
        self.repository = repository
        self.context_service = context_service

    @staticmethod
    def _artifact(context: dict[str, object], key: str) -> dict[str, object]:
        value = context.get(key)
        if not isinstance(value, dict):
            raise ImputationPlanError("IMPUTATION_PLAN_INCOMPATIBLE", f"上下文缺少 {key}")
        return cast(dict[str, object], value)

    @staticmethod
    def _structure_required(context: dict[str, object]) -> bool:
        study = context.get("studyContext")
        value = study.get("value", {}) if isinstance(study, dict) else {}
        return not (
            isinstance(value, dict)
            and value.get("timeStructure") == "cross_sectional"
            and value.get("dependenceStructure") == "independent"
            and value.get("design") == "observational"
        )

    def _context_for_request(self, dataset_id: str, payload: dict[str, object]) -> dict[str, object]:
        requested_sample = str(payload["sampleVersionId"])
        sample_id = None if requested_sample.startswith("sample_all_") else requested_sample
        try:
            context = self.context_service.resolve(
                dataset_id,
                sample_version_id=sample_id,
            )
        except AnalysisContextResolutionError as error:
            raise ImputationPlanError(error.code, str(error)) from error
        if str(context["contextHash"]) != str(payload["contextHash"]):
            raise ImputationPlanError(
                "ANALYSIS_CONTEXT_STALE", "插补计划引用的 contextHash 不是当前上下文"
            )
        sample = self._artifact(context, "sample")
        if str(sample["id"]) != requested_sample:
            raise ImputationPlanError(
                "IMPUTATION_PLAN_INCOMPATIBLE", "sampleVersionId 不属于当前数据上下文"
            )
        structure = context.get("structure")
        if isinstance(structure, dict):
            structure = self._artifact(context, "structure")
            if str(structure.get("id")) != str(payload.get("structureVersionId")):
                raise ImputationPlanError(
                    "IMPUTATION_PLAN_INCOMPATIBLE", "structureVersionId 不属于当前数据上下文"
                )
        elif self._structure_required(context):
            self._artifact(context, "structure")
            raise ImputationPlanError(
                "IMPUTATION_PLAN_INCOMPATIBLE", "上下文缺少 structureVersionId"
            )
        elif payload.get("structureVersionId") is not None:
            raise ImputationPlanError(
                "IMPUTATION_PLAN_INCOMPATIBLE", "独立横截面上下文不应绑定结构版本"
            )
        requested_measurement = payload.get("measurementVersionId")
        if requested_measurement is not None:
            measurement = context.get("measurement")
            if not isinstance(measurement, dict) or str(measurement.get("id")) != str(requested_measurement):
                raise ImputationPlanError(
                    "IMPUTATION_PLAN_INCOMPATIBLE", "measurementVersionId 不属于当前数据上下文"
                )
        return context

    @staticmethod
    def _hashes(payload: dict[str, object], context: dict[str, object]) -> tuple[str, str, str]:
        sample = ImputationPlanService._artifact(context, "sample")
        structure = context.get("structure")
        measurement = context.get("measurement")
        substantive_hash = canonical_sha256(payload["substantiveModel"])
        predictor_matrix_hash = canonical_sha256(
            {
                "variables": payload["variables"],
                "passiveRules": payload.get("passiveRules", []),
                "clusterVariableId": payload.get("clusterVariableId"),
            }
        )
        plan_hash = canonical_sha256(
            {
                "contextHash": payload["contextHash"],
                "sampleHash": sample["hash"],
                "structureHash": structure.get("hash") if isinstance(structure, dict) else None,
                "measurementHash": None if not isinstance(measurement, dict) else measurement["hash"],
                "substantiveModel": payload["substantiveModel"],
                "variables": payload["variables"],
                "passiveRules": payload.get("passiveRules", []),
                "clusterVariableId": payload.get("clusterVariableId"),
                "imputations": payload["imputations"],
                "iterations": payload["iterations"],
                "seed": payload["seed"],
                "diagnostics": payload["diagnostics"],
                "predictorMatrixHash": predictor_matrix_hash,
            }
        )
        return substantive_hash, predictor_matrix_hash, plan_hash

    def create(self, dataset_id: str, payload: dict[str, object]) -> dict[str, object]:
        dataset = self.repository.get_dataset(dataset_id)
        context = self._context_for_request(dataset_id, payload)
        substantive_hash, predictor_matrix_hash, plan_hash = self._hashes(payload, context)
        supplied_substantive = payload.get("substantiveModelHash")
        if supplied_substantive is not None and supplied_substantive != substantive_hash:
            raise ImputationPlanError(
                "MI_SUBSTANTIVE_MODEL_CHANGED_REIMPUTE_REQUIRED",
                "substantiveModelHash 与服务端重算值不一致",
            )
        supplied_plan = payload.get("planHash")
        if supplied_plan is not None and supplied_plan != plan_hash:
            raise ImputationPlanError(
                "IMPUTATION_PLAN_HASH_MISMATCH", "planHash 与服务端重算值不一致"
            )
        stored_payload = dict(payload)
        original_file = dataset.get("originalFile")
        if not isinstance(original_file, dict) or not isinstance(original_file.get("sha256"), str):
            raise ImputationPlanError(
                "DATASET_HASH_UNAVAILABLE", "当前数据版本缺少可验证的原始文件 SHA-256"
            )
        measurement = context.get("measurement")
        structure = context.get("structure")
        stored_payload["datasetSha256"] = original_file["sha256"]
        stored_payload["sampleHash"] = self._artifact(context, "sample")["hash"]
        stored_payload["structureHash"] = structure.get("hash") if isinstance(structure, dict) else None
        stored_payload["measurementHash"] = (
            measurement.get("hash") if isinstance(measurement, dict) else None
        )
        stored_payload["predictorMatrixHash"] = predictor_matrix_hash
        stored_payload["substantiveModelHash"] = substantive_hash
        stored_payload["planHash"] = plan_hash
        return self.repository.save_imputation_plan(
            dataset_id,
            str(payload["structureVersionId"]) if payload.get("structureVersionId") is not None else None,
            str(payload["contextHash"]),
            str(self._artifact(context, "sample")["hash"]),
            substantive_hash,
            plan_hash,
            stored_payload,
        )

    def get(self, plan_id: str) -> dict[str, object]:
        plan = self.repository.get_imputation_plan(plan_id)
        if plan is None:
            raise ImputationPlanError("IMPUTATION_PLAN_NOT_FOUND", "插补计划不存在")
        return plan

    def compatible_analyses(self, plan_id: str, draft_id: str) -> dict[str, object]:
        plan = self.get(plan_id)
        draft = self.repository.get_analysis_draft(draft_id)
        reasons: list[str] = []
        if draft is None:
            reasons.append("ANALYSIS_DRAFT_NOT_FOUND")
        else:
            if draft["datasetVersionId"] != plan["datasetVersionId"]:
                reasons.append("DATASET_VERSION_CHANGED")
            if draft["contextHash"] != plan["contextHash"]:
                reasons.append("ANALYSIS_CONTEXT_CHANGED")
            spec = draft.get("spec")
            if isinstance(spec, dict):
                declared_hash = spec.get("substantiveModelHash")
                substantive_model = spec.get("substantiveModel") or spec.get("pooledAnalysis")
                current_hash = (
                    canonical_sha256(substantive_model)
                    if isinstance(substantive_model, dict)
                    else None
                )
                if declared_hash not in {None, plan["substantiveModelHash"]}:
                    reasons.append("SUBSTANTIVE_MODEL_HASH_MISMATCH")
                if current_hash is not None and current_hash != plan["substantiveModelHash"]:
                    reasons.append("SUBSTANTIVE_MODEL_CHANGED_REIMPUTE_REQUIRED")
        return {
            "compatible": not reasons,
            "reasons": reasons,
            "remediation": "按当前分析草稿重新创建并运行插补计划。" if reasons else "当前插补计划可被该分析草稿消费。",
        }

    def compatible_dataset(self, dataset_id: str, draft_id: str) -> dict[str, object]:
        plan_id = self.repository.get_imputation_dataset_plan_id(dataset_id)
        if plan_id is None and dataset_id.startswith("imputation_plan_"):
            plan_id = dataset_id
        if plan_id is None:
            raise ImputationPlanError("IMPUTATION_DATASET_NOT_FOUND", "插补数据版本不存在")
        return self.compatible_analyses(plan_id, draft_id)

    def run(self, plan_id: str, job_manager: AdvancedJobManager) -> dict[str, object]:
        plan = self.get(plan_id)
        model = cast(dict[str, object], plan["substantiveModel"])
        spec_payload = {
            "schemaVersion": "0.1.0",
            "analysisId": f"mi_{str(plan['id'])[-24:]}",
            "name": "context-bound multiple imputation",
            "family": "multiple_imputation",
            "datasetVersionId": plan["datasetVersionId"],
            "method": "mice_fcs",
            "imputations": plan["imputations"],
            "iterations": plan["iterations"],
            "variables": plan["variables"],
            "passiveRules": plan["passiveRules"],
            "clusterVariableId": plan["clusterVariableId"],
            "pooling": "rubin",
            "pooledAnalysis": model,
            "substantiveModelHash": plan["substantiveModelHash"],
            "planVersionId": plan_id,
            "imputationPlanVersionId": plan_id,
            "contextHash": plan["contextHash"],
            "sampleVersionId": plan["sampleVersionId"],
            "sampleHash": plan["sampleHash"],
            "structureVersionId": plan.get("structureVersionId"),
            "structureHash": plan.get("structureHash"),
            "measurementVersionId": plan.get("measurementVersionId"),
            "measurementHash": plan.get("measurementHash"),
            "datasetSha256": plan["datasetSha256"],
            "predictorMatrixHash": plan["predictorMatrixHash"],
            "diagnostics": plan["diagnostics"],
        }
        spec = MultipleImputationSpec.model_validate(spec_payload)
        job = job_manager.start(
            spec,
            metadata={
                "planVersionId": plan_id,
                "imputationPlanVersionId": plan_id,
                "contextHash": plan["contextHash"],
            },
        )
        return {
            "planVersionId": plan_id,
            "imputationPlanVersionId": plan_id,
            "imputationDatasetVersionId": self.repository.imputation_dataset_id(
                plan_id, str(job["id"])
            ),
            "job": job,
            "contextHash": plan["contextHash"],
        }
