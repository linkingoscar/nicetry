from __future__ import annotations


class EmpiricalAnalysisError(ValueError):
    pass


def validate_empirical_options(metadata: dict[str, object], options: dict[str, object]) -> None:
    """Validate normalized empirical analysis options against dataset metadata."""
    confidence_level = options.get("confidenceLevel", 0.95)
    if not isinstance(confidence_level, (int, float)) or not 0.5 < float(confidence_level) < 1.0:
        raise EmpiricalAnalysisError("confidenceLevel 必须位于 (0.5, 1.0) 区间")
    family_id = options.get("multiplicityFamilyId", "cross_sectional_inference")
    if not isinstance(family_id, str) or not family_id.strip():
        raise EmpiricalAnalysisError("multiplicityFamilyId 不能为空")
    variable_ids = {variable["id"] for variable in metadata["variables"]}
    score_ids = {construct["scoreId"] for construct in metadata["constructs"]}
    available = variable_ids | score_ids
    group_id = options.get("groupVariableId")
    aggregation_id = options.get("aggregationVariableId")
    outcome_id = options.get("outcomeVariableId")
    if group_id and group_id not in variable_ids:
        raise EmpiricalAnalysisError(f"分组变量不存在: {group_id}")
    if aggregation_id and aggregation_id not in variable_ids:
        raise EmpiricalAnalysisError(f"聚类变量不存在: {aggregation_id}")
    if outcome_id and outcome_id not in available:
        raise EmpiricalAnalysisError(f"回归结果变量不存在: {outcome_id}")
    for key in ("predictorVariableIds", "controlVariableIds"):
        unknown = set(options.get(key, [])) - available
        if unknown:
            raise EmpiricalAnalysisError(f"{key} 包含未知变量: {', '.join(sorted(unknown))}")
    overlap = set(options.get("predictorVariableIds", [])) & set(
        options.get("controlVariableIds", [])
    )
    if overlap:
        raise EmpiricalAnalysisError("预测变量与控制变量不能重复")
    if outcome_id in set(options.get("predictorVariableIds", [])) | set(
        options.get("controlVariableIds", [])
    ):
        raise EmpiricalAnalysisError("结果变量不能同时作为预测或控制变量")
    surface_ids = options.get("responseSurfacePredictorIds", [])
    if len(surface_ids) not in {0, 2} or len(set(surface_ids)) != len(surface_ids):
        raise EmpiricalAnalysisError("响应面分析必须选择两个不同的焦点预测变量")
    unknown_surface = set(surface_ids) - available
    if unknown_surface:
        raise EmpiricalAnalysisError(
            f"responseSurfacePredictorIds 包含未知变量: {', '.join(sorted(unknown_surface))}"
        )
    if outcome_id in set(surface_ids) or set(surface_ids) & set(
        options.get("controlVariableIds", [])
    ):
        raise EmpiricalAnalysisError("响应面焦点变量不能与结果变量或控制变量重复")
    panel = options.get("longitudinalPanel")
    if panel:
        subject_id = panel.get("subjectVariableId")
        if subject_id not in variable_ids:
            raise EmpiricalAnalysisError(f"纵向被试标识变量不存在: {subject_id}")
        waves = panel.get("waves", [])
        minimum_waves = 3 if panel.get("modelType") == "ri_clpm" else 2
        if len(waves) < minimum_waves:
            raise EmpiricalAnalysisError(
                f"{panel.get('modelType')} 至少需要 {minimum_waves} 个时间点"
            )
        if panel.get("measurementMode") == "latent_items":
            panel_ids = {
                variable_id
                for wave in waves
                for variable_id in (*wave.get("xItemIds", []), *wave.get("yItemIds", []))
            }
            item_ids = {
                item_id for construct in metadata["constructs"] for item_id in construct["itemIds"]
            }
            nonitems = panel_ids - item_ids
            if nonitems:
                raise EmpiricalAnalysisError(
                    "潜变量纵向模型只能使用测量版本中的题项: " + ", ".join(sorted(nonitems))
                )
        else:
            panel_ids = {
                variable_id
                for wave in waves
                for variable_id in (wave.get("xVariableId"), wave.get("yVariableId"))
                if variable_id
            }
        unknown_panel = panel_ids - available
        if unknown_panel:
            raise EmpiricalAnalysisError(
                f"纵向模型包含未知变量: {', '.join(sorted(unknown_panel))}"
            )
    diary = options.get("diaryMultilevel")
    if diary:
        diary_ids = {
            diary.get("subjectVariableId"),
            diary.get("timeVariableId"),
            diary.get("outcomeVariableId"),
            diary.get("predictorVariableId"),
            diary.get("mediatorVariableId"),
            diary.get("level2ModeratorVariableId"),
            diary.get("responseLatencyVariableId"),
            *diary.get("level2CovariateIds", []),
            *diary.get("controlVariableIds", []),
            *[
                item_id
                for construct in diary.get("reliabilityConstructs", [])
                for item_id in construct.get("itemIds", [])
            ],
        }
        diary_ids.discard(None)
        unknown_diary = diary_ids - available
        if unknown_diary:
            raise EmpiricalAnalysisError(
                f"日记多层模型包含未知变量: {', '.join(sorted(unknown_diary))}"
            )
