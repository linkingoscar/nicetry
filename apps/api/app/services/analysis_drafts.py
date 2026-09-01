from __future__ import annotations

from typing import cast

from app.services.analysis_context import AnalysisContextService
from app.services.capability_applicability import CapabilityApplicabilityRegistry
from app.services.dataset_repository import DatasetRepository


class AnalysisDraftError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class AnalysisDraftService:
    """Create and edit executable analysis drafts against one context hash."""

    _ADVANCED_FAMILIES = {
        "experimental_design",
        "multilevel_model",
        "power_analysis",
        "multiple_imputation",
        "questionnaire_measurement",
    }

    def __init__(
        self,
        repository: DatasetRepository,
        context_service: AnalysisContextService,
        registry: CapabilityApplicabilityRegistry,
    ) -> None:
        self.repository = repository
        self.context_service = context_service
        self.registry = registry

    def _current_context(self, dataset_id: str, expected_hash: str) -> dict[str, object]:
        context = self.context_service.resolve(dataset_id)
        current_hash = str(context["contextHash"])
        self.repository.mark_analysis_drafts_stale(dataset_id, current_hash, context)
        if current_hash != expected_hash:
            raise AnalysisDraftError(
                "ANALYSIS_CONTEXT_STALE",
                "分析草稿引用的 contextHash 已不是当前上下文",
            )
        return context

    def _capability(self, context: dict[str, object], slice_id: str) -> dict[str, object]:
        capabilities = [
            item
            for item in self.registry.list(context)
            if item.get("sliceId") == slice_id
        ]
        if not capabilities:
            raise AnalysisDraftError(
                "METHOD_NOT_APPLICABLE_TO_CONTEXT", f"未知或未登记的分析 slice: {slice_id}"
            )
        capability = capabilities[0]
        if capability.get("family") not in self._ADVANCED_FAMILIES:
            raise AnalysisDraftError(
                "METHOD_NOT_APPLICABLE_TO_CONTEXT",
                "该方法属于内建实证/模型工作台，不能创建高级分析草稿。",
            )
        if not capability.get("executionAvailable") or not capability.get("applicable"):
            raise AnalysisDraftError(
                "METHOD_NOT_APPLICABLE_TO_CONTEXT",
                str(capability.get("blockedReason") or "当前上下文不满足方法要求"),
            )
        return capability

    def _merge_spec(
        self,
        dataset_id: str,
        context: dict[str, object],
        capability: dict[str, object],
        spec: dict[str, object],
        role_overrides: dict[str, dict[str, str]],
    ) -> dict[str, object]:
        declared_dataset = spec.get("datasetVersionId")
        if declared_dataset is not None and declared_dataset != dataset_id:
            raise AnalysisDraftError(
                "ARTIFACT_DATASET_MISMATCH", "分析规格引用了其他数据版本"
            )
        required = cast(list[str], capability.get("requiredRoles", []))
        optional = cast(list[str], capability.get("optionalRoles", []))
        allowed_roles = set(required + optional)
        dataset = self.repository.get_dataset(dataset_id)
        variables = cast(list[dict[str, object]], dataset["variables"])
        known_ids = {str(variable["id"]) for variable in variables}
        defaults = cast(dict[str, str], capability.get("defaultBindings", {}))
        roles = dict(defaults)
        encoded_overrides: dict[str, dict[str, str]] = {}
        for role, override in role_overrides.items():
            if role not in allowed_roles or override["variableId"] not in known_ids:
                raise AnalysisDraftError(
                    "STRUCTURE_ROLE_INVALID", f"分析草稿角色覆盖无效: {role}"
                )
            roles[role] = override["variableId"]
            encoded_overrides[role] = override
        merged = dict(spec)
        merged.update(
            {
                "schemaVersion": "1.0.0",
                "datasetVersionId": dataset_id,
                "contextHash": context["contextHash"],
                "roles": roles,
            }
        )
        merged["roleOverrides"] = encoded_overrides
        return merged

    def get_validity(self, draft_id: str) -> dict[str, object]:
        """Return a draft refreshed against the current resolved context."""
        draft = self.repository.get_analysis_draft(draft_id)
        if draft is None:
            raise AnalysisDraftError("ANALYSIS_DRAFT_NOT_FOUND", "分析草稿不存在")
        current = self.context_service.resolve(str(draft["datasetVersionId"]))
        if draft.get("contextHash") != current.get("contextHash"):
            self.repository.mark_analysis_drafts_stale(
                str(draft["datasetVersionId"]), str(current["contextHash"]), current
            )
            refreshed = self.repository.get_analysis_draft(draft_id)
            if refreshed is not None:
                draft = refreshed
        return draft

    def create(
        self, dataset_id: str, slice_id: str, context_hash: str
    ) -> dict[str, object]:
        context = self._current_context(dataset_id, context_hash)
        capability = self._capability(context, slice_id)
        spec = self._merge_spec(
            dataset_id,
            context,
            capability,
            {},
            {},
        )
        snapshot_id = self.repository.save_analysis_context_snapshot(dataset_id, context)
        return self.repository.create_analysis_draft(
            dataset_id,
            str(capability["family"]),
            slice_id,
            context_hash,
            snapshot_id,
            spec,
            {},
            "ready",
        )

    def update(
        self,
        draft_id: str,
        expected_revision: int,
        spec: dict[str, object],
        role_overrides: dict[str, dict[str, str]],
    ) -> dict[str, object]:
        draft = self.repository.get_analysis_draft(draft_id)
        if draft is None:
            raise AnalysisDraftError("ANALYSIS_DRAFT_NOT_FOUND", "分析草稿不存在")
        revision = draft.get("revision")
        if not isinstance(revision, int) or revision != expected_revision:
            raise AnalysisDraftError("REVISION_CONFLICT", "分析草稿 revision 已变化")
        if draft["validity"] in {"stale", "superseded"}:
            raise AnalysisDraftError(
                "ANALYSIS_DRAFT_SUPERSEDED", "过期草稿不可原地恢复，请创建替代草稿"
            )
        dataset_id = str(draft["datasetVersionId"])
        context = self._current_context(dataset_id, str(draft["contextHash"]))
        capability = self._capability(context, str(draft["sliceId"]))
        merged = self._merge_spec(dataset_id, context, capability, spec, role_overrides)
        snapshot_id = self.repository.save_analysis_context_snapshot(dataset_id, context)
        del snapshot_id
        updated = self.repository.update_analysis_draft(
            draft_id,
            expected_revision,
            str(context["contextHash"]),
            merged,
            role_overrides,
            "ready",
        )
        if updated is None:
            raise AnalysisDraftError("ANALYSIS_DRAFT_NOT_FOUND", "分析草稿不存在")
        return updated
