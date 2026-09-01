from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.services.canonical_identity import canonical_sha256
from app.services.dataset_repository import DatasetRepository
from app.services.evidence_identity import resolve_current_artifact_identity
from app.services.study_plan_binding_helpers import (
    binding_value as _binding_value,
)
from app.services.study_plan_binding_helpers import (
    declaration_deviation as _declaration_deviation,
)
from app.services.study_plan_binding_helpers import (
    execution_value as _execution_value,
)
from app.services.study_plan_binding_helpers import (
    identity_value as _identity_value,
)
from app.services.study_plan_binding_helpers import (
    string_list as _string_list,
)
from app.study_plan_contracts import StudyPlanPayload

if TYPE_CHECKING:
    from app.services.study_plans import StudyPlanService


class StudyPlanBindingService:
    """Validate and classify the StudyPlan → analysis-result intent chain."""

    def __init__(self, repository: DatasetRepository) -> None:
        self.repository = repository

    _value = staticmethod(_binding_value)
    _string_list = staticmethod(_string_list)
    _execution_value = staticmethod(_execution_value)
    _declaration_deviation = staticmethod(_declaration_deviation)
    _identity_value = staticmethod(_identity_value)

    def current_artifact_identity(
        self, dataset_id: str, binding: dict[str, object]
    ) -> dict[str, str]:
        return resolve_current_artifact_identity(self.repository, dataset_id, binding)

    def bind_for_analysis(
        self,
        plan_service: StudyPlanService,
        dataset_id: str,
        binding: dict[str, object],
        *,
        execution_spec: dict[str, object] | None = None,
        identity: dict[str, object] | None = None,
        spec_hash: str | None = None,
    ) -> dict[str, object]:
        plan_id = str(self._value(binding, "study_plan_version_id") or "").strip()
        plan_hash = str(self._value(binding, "study_plan_hash") or "").strip()
        hypothesis_ids = self._string_list(self._value(binding, "hypothesis_ids"))
        hypothesis_id = str(self._value(binding, "hypothesis_id") or "").strip()
        if not hypothesis_ids and hypothesis_id:
            hypothesis_ids = [hypothesis_id]
        if hypothesis_ids and not hypothesis_id:
            hypothesis_id = hypothesis_ids[0]
        estimand_id = str(self._value(binding, "estimand_id") or "").strip()
        declaration_id = str(self._value(binding, "analysis_declaration_id") or "").strip()
        if not all((plan_id, plan_hash, hypothesis_ids, estimand_id, declaration_id)):
            raise ValueError("STUDY_PLAN_BINDING_REQUIRED: 结果必须绑定完整的 StudyPlan intent 链")
        plan = self.repository.get_study_plan(plan_id)
        if plan is None:
            raise LookupError("STUDY_PLAN_NOT_FOUND: 绑定的研究计划版本不存在")
        if plan.get("status") != "frozen":
            raise ValueError("STUDY_PLAN_NOT_FROZEN: 只有冻结计划才能绑定分析结果")
        if str(plan.get("planHash")) != plan_hash:
            raise ValueError("STUDY_PLAN_HASH_MISMATCH: 绑定的计划 hash 已变化")
        dataset = self.repository.get_dataset(dataset_id)
        if str(plan.get("projectId")) != str(dataset.get("projectId")):
            raise ValueError("PLAN_PROJECT_DATASET_MISMATCH: 计划与分析数据不属于同一研究项目")
        payload = plan_service._payload_from_plan(plan)
        plan_service._validate_payload(payload)
        hypotheses = cast(list[object], payload["hypotheses"])
        estimands = cast(list[object], payload["estimands"])
        declarations = cast(list[object], payload["analysisDeclarations"])
        selected_hypotheses = [
            item
            for item in hypotheses
            if isinstance(item, dict) and item.get("id") in hypothesis_ids
        ]
        estimand = next((item for item in estimands if isinstance(item, dict) and item.get("id") == estimand_id), None)
        declaration = next((item for item in declarations if isinstance(item, dict) and item.get("id") == declaration_id), None)
        if len(selected_hypotheses) != len(hypothesis_ids):
            missing = [item_id for item_id in hypothesis_ids if item_id not in {item.get("id") for item in selected_hypotheses}]
            raise ValueError(f"STUDY_PLAN_HYPOTHESIS_NOT_FOUND: {', '.join(missing)}")
        if estimand is None:
            raise ValueError(f"STUDY_PLAN_ESTIMAND_NOT_FOUND: {estimand_id}")
        if declaration is None:
            raise ValueError(f"STUDY_PLAN_ANALYSIS_DECLARATION_NOT_FOUND: {declaration_id}")
        for selected in selected_hypotheses:
            if estimand_id not in cast(list[object], selected.get("estimandIds", [])):
                raise ValueError(
                    "STUDY_PLAN_BINDING_MISMATCH: hypothesis 未声明该 estimand"
                )
        if estimand_id not in cast(list[object], declaration.get("estimandIds", [])):
            raise ValueError("STUDY_PLAN_BINDING_MISMATCH: analysis declaration 未声明该 estimand")
        compact = {
            "studyPlanVersionId": plan_id,
            "studyPlanHash": plan_hash,
            "hypothesisId": hypothesis_id,
            "hypothesisIds": hypothesis_ids,
            "estimandId": estimand_id,
            "analysisDeclarationId": declaration_id,
        }
        if execution_spec is None and identity is None and spec_hash is None:
            return compact
        return self.build_result_binding(
            plan_service,
            dataset_id,
            compact,
            execution_spec=execution_spec,
            identity=identity,
            spec_hash=spec_hash,
        )

    def build_result_binding(
        self,
        plan_service: StudyPlanService,
        dataset_id: str,
        binding: dict[str, object],
        *,
        execution_spec: dict[str, object] | None,
        identity: dict[str, object] | None,
        spec_hash: str | None,
    ) -> dict[str, object]:
        """Attach immutable artifact identities and declaration status to a result binding."""
        dataset = self.repository.get_dataset(dataset_id)
        plan_id = str(binding.get("studyPlanVersionId", "")).strip()
        plan = self.repository.get_study_plan(plan_id)
        if plan is None:
            raise LookupError("STUDY_PLAN_NOT_FOUND: 绑定的研究计划版本不存在")
        payload = plan_service._payload_from_plan(plan)
        plan_service._validate_payload(payload)
        declarations = cast(list[object], payload["analysisDeclarations"])
        declaration_id = str(binding.get("analysisDeclarationId", ""))
        declaration = next(
            (item for item in declarations if isinstance(item, dict) and item.get("id") == declaration_id),
            None,
        )
        if declaration is None:
            raise ValueError(f"STUDY_PLAN_ANALYSIS_DECLARATION_NOT_FOUND: {declaration_id}")

        resolved_identity = identity or {}
        dataset_sha256 = self._identity_value(resolved_identity, "datasetSha256")
        if dataset_sha256 is None:
            original_file = dataset.get("originalFile")
            dataset_sha256 = original_file.get("sha256") if isinstance(original_file, dict) else None
        references = {
            "datasetSha256": dataset_sha256,
            "sampleVersionId": self._identity_value(resolved_identity, "sampleVersionId"),
            "sampleHash": self._identity_value(resolved_identity, "sampleHash"),
            "measurementVersionId": self._identity_value(resolved_identity, "measurementVersionId"),
            "measurementHash": self._identity_value(resolved_identity, "measurementHash"),
        }
        missing = [key for key, value in references.items() if value is None or not str(value).strip()]
        if missing:
            raise ValueError(
                "RESULT_EVIDENCE_IDENTITY_INCOMPLETE: 缺少 " + ", ".join(missing)
            )
        deviation_reason = self._declaration_deviation(
            cast(dict[str, object], declaration), execution_spec
        )
        declaration_status = "deviated" if deviation_reason else "declared"
        return {
            **binding,
            **{key: str(value) for key, value in references.items()},
            "specHash": spec_hash or canonical_sha256(execution_spec or {}),
            "declarationStatus": declaration_status,
            "deviationReason": deviation_reason,
            "publicationEligible": declaration_status == "declared",
        }

    def multiplicity_context(
        self, plan_service: StudyPlanService, binding: dict[str, object]
    ) -> dict[str, object]:
        """Expose immutable family declarations to the execution engine."""
        plan_id = str(binding.get("studyPlanVersionId", "")).strip()
        plan = self.repository.get_study_plan(plan_id)
        if plan is None:
            raise LookupError("STUDY_PLAN_NOT_FOUND: 绑定的研究计划版本不存在")
        payload = plan_service._payload_from_plan(plan)
        plan_service._validate_payload(payload)
        return {
            "studyPlanVersionId": plan_id,
            "studyPlanHash": str(plan.get("planHash", "")),
            "hypotheses": payload.get("hypotheses", []),
            "estimands": payload.get("estimands", []),
            "analysisDeclarations": payload.get("analysisDeclarations", []),
            "multiplicityFamilies": payload.get("multiplicityFamilies", []),
            "studyPlanBinding": dict(binding),
        }

    def result_binding_status(
        self,
        current_plan: dict[str, object] | None,
        binding: dict[str, object],
    ) -> tuple[str, list[str]]:
        if current_plan is None:
            return "stale", ["STUDY_PLAN_VERSION_REMOVED"]
        reasons: list[str] = []
        if str(current_plan.get("id")) != str(binding.get("studyPlanVersionId")):
            reasons.append("STUDY_PLAN_NEWER_REVISION")
        if str(current_plan.get("planHash")) != str(binding.get("studyPlanHash")):
            reasons.append("STUDY_PLAN_HASH_CHANGED")
        return ("stale", reasons) if reasons else ("current", [])

    def refresh_result_binding(
        self,
        result: dict[str, object],
        *,
        current_plan: dict[str, object] | None,
        current_data_sha256: str,
        current_sample_version_id: str | None = None,
        current_sample_hash: str | None = None,
        current_measurement_version_id: str | None = None,
        current_measurement_hash: str | None = None,
    ) -> dict[str, object]:
        binding = result.get("studyPlanBinding")
        if not isinstance(binding, dict):
            return result
        status, reasons = self.result_binding_status(current_plan, binding)
        provenance = result.get("provenance")
        result_data_sha256 = provenance.get("dataSha256") if isinstance(provenance, dict) else None
        if (
            isinstance(result_data_sha256, str)
            and current_data_sha256
            and result_data_sha256 != current_data_sha256
        ):
            status = "stale"
            reasons = [*reasons, "DATASET_HASH_CHANGED"]
        binding_data_sha256 = binding.get("datasetSha256")
        if (
            isinstance(binding_data_sha256, str)
            and current_data_sha256
            and binding_data_sha256 != current_data_sha256
        ):
            status = "stale"
            reasons = [*reasons, "DATASET_HASH_CHANGED"]

        identity_checks = (
            (
                "sampleVersionId",
                current_sample_version_id,
                "SAMPLE_VERSION_CHANGED",
                "SAMPLE_VERSION_IDENTITY_UNAVAILABLE",
                "SAMPLE_VERSION_IDENTITY_MISSING",
            ),
            (
                "sampleHash",
                current_sample_hash,
                "SAMPLE_HASH_CHANGED",
                "SAMPLE_HASH_IDENTITY_UNAVAILABLE",
                "SAMPLE_HASH_IDENTITY_MISSING",
            ),
            (
                "measurementVersionId",
                current_measurement_version_id,
                "MEASUREMENT_VERSION_CHANGED",
                "MEASUREMENT_VERSION_IDENTITY_UNAVAILABLE",
                "MEASUREMENT_VERSION_IDENTITY_MISSING",
            ),
            (
                "measurementHash",
                current_measurement_hash,
                "MEASUREMENT_HASH_CHANGED",
                "MEASUREMENT_HASH_IDENTITY_UNAVAILABLE",
                "MEASUREMENT_HASH_IDENTITY_MISSING",
            ),
        )
        for identity_key, current_value, changed_reason, unavailable_reason, missing_reason in identity_checks:
            if current_value is None:
                continue
            current_text = str(current_value).strip()
            result_text = str(binding.get(identity_key, "")).strip()
            if not current_text:
                status = "stale"
                reasons = [*reasons, unavailable_reason]
            elif not result_text:
                status = "stale"
                reasons = [*reasons, missing_reason]
            elif result_text != current_text:
                status = "stale"
                reasons = [*reasons, changed_reason]
        declaration_status = str(binding.get("declarationStatus", "declared"))
        publication_eligible = (
            status == "current"
            and declaration_status != "deviated"
            and bool(binding.get("publicationEligible", True))
        )
        refreshed = {
            **binding,
            "status": status,
            "currentEvidence": status == "current",
            "staleReasons": list(dict.fromkeys(reasons)),
            "publicationEligible": publication_eligible,
        }
        result["studyPlanBinding"] = refreshed
        if isinstance(provenance, dict):
            provenance["studyPlanBinding"] = refreshed
        evidence_graph = result.get("evidenceGraph")
        if isinstance(evidence_graph, dict) and "resultBinding" in evidence_graph:
            evidence_graph["resultBinding"] = dict(refreshed)
        if status != "current":
            result["publicationEligible"] = False
            result["requiresManualReview"] = True
            publication_reasons = result.get("publicationEligibilityReasons")
            if not isinstance(publication_reasons, list):
                publication_reasons = []
            result["publicationEligibilityReasons"] = list(
                dict.fromkeys([*publication_reasons, *reasons])
            )
        return result

    def attach_result_binding(
        self,
        result: dict[str, object],
        binding: dict[str, object],
    ) -> dict[str, object]:
        attached = {
            **binding,
            "status": "current",
            "currentEvidence": True,
            "staleReasons": self._string_list(binding.get("staleReasons")),
        }
        result["studyPlanBinding"] = attached
        provenance = result.get("provenance")
        if isinstance(provenance, dict):
            provenance["studyPlanBinding"] = attached
        result["evidenceGraph"] = self.build_evidence_graph(
            attached,
            existing_graph=result.get("evidenceGraph"),
        )
        if attached.get("declarationStatus") == "deviated":
            result["publicationEligible"] = False
            result["requiresManualReview"] = True
            reasons = result.get("publicationEligibilityReasons")
            if not isinstance(reasons, list):
                reasons = []
            result["publicationEligibilityReasons"] = list(
                dict.fromkeys([*reasons, "STUDY_PLAN_DECLARATION_DEVIATED"])
            )
        return result

    def build_evidence_graph(
        self,
        binding: dict[str, object],
        *,
        existing_graph: object = None,
    ) -> dict[str, object]:
        plan_id = str(binding.get("studyPlanVersionId", ""))
        plan = self.repository.get_study_plan(plan_id)
        if plan is None:
            raise LookupError("STUDY_PLAN_NOT_FOUND: 绑定的研究计划版本不存在")
        payload = {
            key: plan[key]
            for key in (
                "schemaVersion",
                "title",
                "researchQuestion",
                "hypotheses",
                "estimands",
                "analysisDeclarations",
                "multiplicityFamilies",
                "sampleDefinition",
                "measurementPlan",
                "missingDataPlan",
                "powerPlan",
                "context",
                "migration",
            )
            if key in plan
        }
        StudyPlanPayload.model_validate(payload)
        hypothesis_ids = self._string_list(binding.get("hypothesisIds"))
        if not hypothesis_ids and binding.get("hypothesisId"):
            hypothesis_ids = [str(binding["hypothesisId"])]
        estimand_id = str(binding.get("estimandId", ""))
        declaration_id = str(binding.get("analysisDeclarationId", ""))
        hypotheses = [
            {
                "id": item["id"],
                "estimandIds": list(item.get("estimandIds", [])),
            }
            for item in cast(list[object], payload["hypotheses"])
            if isinstance(item, dict) and item.get("id") in hypothesis_ids
        ]
        estimand_item = next(
            (
                item
                for item in cast(list[object], payload["estimands"])
                if isinstance(item, dict) and item.get("id") == estimand_id
            ),
            None,
        )
        declaration_item = next(
            (
                item
                for item in cast(list[object], payload["analysisDeclarations"])
                if isinstance(item, dict) and item.get("id") == declaration_id
            ),
            None,
        )
        graph = dict(existing_graph) if isinstance(existing_graph, dict) else {}
        graph.update(
            {
                "schemaVersion": "2.0.0",
                "studyPlanVersion": {
                    "id": plan["id"],
                    "hash": plan["planHash"],
                    "revision": plan["revision"],
                    "status": plan["status"],
                },
                "hypotheses": hypotheses,
                "estimands": (
                    [
                        {
                            "id": estimand_item["id"],
                            "quantity": estimand_item.get("quantity"),
                            "hypothesisIds": hypothesis_ids,
                        }
                    ]
                    if isinstance(estimand_item, dict)
                    else []
                ),
                "analysisDeclarations": (
                    [
                        {
                            "id": declaration_item["id"],
                            "role": declaration_item.get("role"),
                            "estimandIds": list(declaration_item.get("estimandIds", [])),
                            "capabilitySliceId": declaration_item.get("capabilitySliceId"),
                            "requestedMethod": declaration_item.get("requestedMethod"),
                        }
                    ]
                    if isinstance(declaration_item, dict)
                    else []
                ),
                "resultBinding": dict(binding),
            }
        )
        return graph
