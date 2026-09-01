from __future__ import annotations

from typing import Any

from app.empirical_procedure_contracts import PROCEDURE_SLICES
from app.services.analysis_context import AnalysisContextResolutionError
from app.services.capability_applicability import (
    CapabilityApplicabilityRegistry,
    applicable_capability_registry,
)


def empirical_capability_slices(options: dict[str, Any]) -> tuple[str, ...]:
    """Map one empirical request to every statistical slice it will execute."""
    procedure = options.get("procedure")
    if procedure in PROCEDURE_SLICES:
        return (PROCEDURE_SLICES[procedure],)
    panel = options.get("longitudinalPanel")
    if isinstance(panel, dict):
        model_type = str(panel.get("modelType") or "clpm")
        slices = [{
            "clpm": "empirical.panel.clpm",
            "ri_clpm": "empirical.panel.ri_clpm",
            "lcm_sr": "empirical.panel.lcm_sr",
        }.get(model_type, "empirical.panel.clpm")]
        if options.get("groupVariableId"):
            slices.append("empirical.cross_sectional.group_comparison")
        if options.get("aggregationVariableId"):
            slices.append("empirical.cross_sectional.overview")
        if options.get("outcomeVariableId") and options.get("predictorVariableIds"):
            slices.append("empirical.cross_sectional.hierarchical_regression")
        if len(options.get("responseSurfacePredictorIds") or []) == 2:
            slices.append("empirical.cross_sectional.response_surface")
        return tuple(slices)
    diary = options.get("diaryMultilevel")
    if isinstance(diary, dict):
        if diary.get("clusterStructure") == "cross_classified" or diary.get("crossClassVariableId"):
            return ("empirical.diary.cross_classified_gaussian",)
        slices = [{
            "lmm": "empirical.diary.lmm",
            "glmm": "empirical.diary.glmm",
            "mediation": "empirical.diary.multilevel_mediation",
            "bayesian_dsem": "empirical.diary.dsem",
        }.get(str(diary.get("analysisType") or "lmm"), "empirical.diary.lmm")]
        if options.get("groupVariableId"):
            slices.append("empirical.cross_sectional.group_comparison")
        if options.get("aggregationVariableId"):
            slices.append("empirical.cross_sectional.overview")
        if options.get("outcomeVariableId") and options.get("predictorVariableIds"):
            slices.append("empirical.cross_sectional.hierarchical_regression")
        if len(options.get("responseSurfacePredictorIds") or []) == 2:
            slices.append("empirical.cross_sectional.response_surface")
        return tuple(slices)

    slices = [
        "empirical.cross_sectional.overview",
        "empirical.cross_sectional.measurement",
    ]
    if options.get("groupVariableId"):
        slices.append("empirical.cross_sectional.group_comparison")
    if options.get("outcomeVariableId") and options.get("predictorVariableIds"):
        slices.append("empirical.cross_sectional.hierarchical_regression")
    if len(options.get("responseSurfacePredictorIds") or []) == 2:
        slices.append("empirical.cross_sectional.response_surface")
    return tuple(slices)


def require_empirical_capability(
    context: dict[str, object],
    options: dict[str, Any],
    registry: CapabilityApplicabilityRegistry = applicable_capability_registry,
) -> tuple[str, ...]:
    """Fail closed when any requested empirical module is not context-applicable."""
    slice_ids = list(empirical_capability_slices(options))
    study = context.get("studyContext")
    study_value = study.get("value") if isinstance(study, dict) else None
    if (
        options.get("aggregationVariableId")
        and isinstance(study_value, dict)
        and study_value.get("dependenceStructure") == "nested"
    ):
        slice_ids.append("multilevel_model.aggregation.icc_rwg")
    for slice_id in slice_ids:
        applicability = registry.evaluate_slice(slice_id, context)
        if not applicability.get("executionAvailable") or not applicability.get("applicable"):
            raise AnalysisContextResolutionError(
                "METHOD_NOT_APPLICABLE_TO_CONTEXT",
                f"{slice_id}: " + str(
                    applicability.get("blockedReason")
                    or "当前研究上下文不允许该实证方法。"
                ),
            )
    return tuple(slice_ids)
