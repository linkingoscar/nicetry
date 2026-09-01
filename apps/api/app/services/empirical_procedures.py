"""Validate procedure scope before execution, never silently broaden a request."""
from __future__ import annotations

from typing import Any, get_args

from app.empirical_procedure_contracts import EmpiricalProcedure
from app.services.empirical_options_validator import EmpiricalAnalysisError


def validate_procedure(metadata: dict[str, Any], options: dict[str, Any]) -> None:
    procedure = options.get("procedure")
    if procedure is None:
        return
    if procedure not in get_args(EmpiricalProcedure):
        raise EmpiricalAnalysisError("未知的单项分析方法")
    selected = options.get("analysisVariableIds", [])
    constructs = options.get("constructIds", [])
    variables = {v["id"]: v for v in metadata["variables"]}
    score_ids = {c["scoreId"] for c in metadata["constructs"]}
    construct_ids = {c["id"] for c in metadata["constructs"]}
    if len(set(selected)) != len(selected) or set(selected) - (set(variables) | score_ids):
        raise EmpiricalAnalysisError("分析变量重复或不属于当前数据版本")
    if len(set(constructs)) != len(constructs) or set(constructs) - construct_ids:
        raise EmpiricalAnalysisError("所选构念重复或不属于当前测量版本")
    if procedure in {"descriptives", "frequencies", "missing", "correlation", "groups"}:
        if len(selected) < (2 if procedure == "correlation" else 1):
            raise EmpiricalAnalysisError("请选择分析变量（相关分析至少两个）")
        if procedure in {"descriptives", "correlation", "groups"} and any(
            v in variables and variables[v]["type"] not in {"continuous", "ordinal", "likert", "binary"}
            for v in selected
        ):
            raise EmpiricalAnalysisError("此分析要求数值变量")
    if procedure in {"reliability", "efa", "cfa", "validity", "common_method", "invariance", "aggregation"} and not constructs:
        raise EmpiricalAnalysisError("请选择本次分析的构念/量表")
    if procedure in {"groups", "invariance"} and not options.get("groupVariableId"):
        raise EmpiricalAnalysisError("请选择分组变量")
    if procedure == "groups" and options.get("groupVariableId") in selected:
        raise EmpiricalAnalysisError("分组变量不能同时作为被比较的分析变量")
    if procedure == "aggregation" and not options.get("aggregationVariableId"):
        raise EmpiricalAnalysisError("请选择 cluster 聚合变量")
    if procedure in {"regression", "relative_importance", "response_surface"} and not options.get("outcomeVariableId"):
        raise EmpiricalAnalysisError("请选择结果变量")
    if procedure in {"regression", "relative_importance"} and not options.get("predictorVariableIds"):
        raise EmpiricalAnalysisError("请选择预测变量")
    if procedure == "response_surface" and len(options.get("responseSurfacePredictorIds", [])) != 2:
        raise EmpiricalAnalysisError("响应面需要两个焦点变量")
    if procedure == "correlation" and options.get("correlationMethod") == "partial":
        controls = options.get("controlVariableIds", [])
        if not controls or set(controls) & set(selected):
            raise EmpiricalAnalysisError("偏相关需要与分析变量不同的控制变量")
    if procedure == "correlation" and options.get("correlationMethod") != "partial" and options.get("controlVariableIds"):
        raise EmpiricalAnalysisError("只有偏相关接受控制变量")
    for name, allowed in {
        "analysisVariableIds": {"descriptives", "frequencies", "missing", "correlation", "groups"},
        "constructIds": {"reliability", "efa", "cfa", "validity", "common_method", "invariance", "aggregation"},
        "groupVariableId": {"groups", "invariance"},
        "aggregationVariableId": {"aggregation"},
        "outcomeVariableId": {"regression", "relative_importance", "response_surface"},
        "predictorVariableIds": {"regression", "relative_importance"},
        "responseSurfacePredictorIds": {"response_surface"},
        "controlVariableIds": {"correlation", "regression", "relative_importance", "response_surface"},
        "longitudinalPanel": {"longitudinal"},
        "diaryMultilevel": {"diary"},
    }.items():
        if options.get(name) and procedure not in allowed:
            raise EmpiricalAnalysisError(f"{procedure} 不接受其他分析的配置: {name}")
    for proc, key in (("longitudinal", "longitudinalPanel"), ("diary", "diaryMultilevel")):
        if procedure == proc and not options.get(key):
            raise EmpiricalAnalysisError("请完成当前模型的变量与估计设置")
