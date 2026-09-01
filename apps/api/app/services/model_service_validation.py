from __future__ import annotations

from typing import Any, cast

import numpy as np
import pandas as pd

from app.semantics import validate_model_semantics
from app.services.dataset_repository import DatasetRepository
from app.services.model_encoding import encode_node_series, predictor_columns
from app.services.model_service_helpers import _model_variables, _warning
from app.services.owned_resources import resolve_derived_dataset_path


def validate_model_for_dataset(
    dataset_id: str,
    model_spec: dict[str, Any],
    repository: DatasetRepository,
) -> dict[str, Any]:
    summary = validate_model_semantics(model_spec)
    errors = list(summary["errors"])
    warnings = list(summary["warnings"])
    dataset = repository.get_dataset(dataset_id)
    measurement = repository.get_measurement(dataset_id)
    derived = measurement["derivedDataset"]

    dataset_sha = dataset.get("originalFile", {}).get("sha256", "")
    measurement_version = measurement.get("version", 0)
    from app.contracts import compute_analysis_signature

    analysis_sig = compute_analysis_signature(model_spec)
    cache_key = (dataset_sha, measurement_version, analysis_sig)

    cached_val = repository.get_precheck_cache_item(cache_key)
    if cached_val is not None and cached_val.get("catalogVersion") == "5.0":
        return cached_val

    if model_spec.get("datasetVersionId") != derived["id"]:
        errors.append("ModelSpec 必须引用当前测量版本生成的派生数据集")

    available = _model_variables(dataset, measurement)
    nodes = model_spec.get("nodes", [])

    binary_mediators = [
        node
        for node in nodes
        if node.get("role") == "m" and node.get("dataType") == "binary"
    ]
    if binary_mediators:
        errors.append(
            "BINARY_MEDIATOR_NOT_SUPPORTED："
            + "、".join(str(node.get("id", "")) for node in binary_mediators)
            + " 为二分类中介变量；logit 系数与 OLS 系数的乘积不构成可解释的间接效应，"
            "当前不支持二分类 M。"
        )

    family = model_spec.get("estimation", {}).get("family", "ols")
    if family == "sem":
        from app.services.sem_compiler import compile_sem_model

        data_path = resolve_derived_dataset_path(
            repository.settings.state_root,
            measurement,
        )
        data = pd.read_parquet(data_path)
        compiled_sem = compile_sem_model(model_spec, data, available)
        errors.extend(compiled_sem["errors"])
        warnings.extend(compiled_sem["warnings"])

        # 获取分组变量列名
        estimation = model_spec.get("estimation", {})
        group_var_id = estimation.get("groupVariableId")
        group_col = None
        if group_var_id:
            node_group = next((n for n in nodes if n.get("id") == group_var_id), None)
            group_var_id_mapped = (
                node_group.get("variableId", group_var_id) if node_group else group_var_id
            )
            if group_var_id_mapped in available:
                group_col = available[group_var_id_mapped]["column"]
            else:
                group_col = group_var_id_mapped

        required_vars = compiled_sem["requiredVariables"]
        numeric = pd.DataFrame(index=data.index)
        for var_id in required_vars:
            col = var_id
            if var_id in available:
                col = available[var_id]["column"]

            if col == group_col:
                continue

            if col in data.columns:
                original = cast(pd.Series, data[col])
                converted = cast(pd.Series, pd.to_numeric(original, errors="coerce"))
                nonnumeric = original.notna() & converted.isna()
                if nonnumeric.any():
                    errors.append(f"变量“{var_id}”包含 {int(nonnumeric.sum())} 个非数值取值")
                numeric[var_id] = converted
                if converted.dropna().nunique() <= 1:
                    errors.append(f"变量“{var_id}”在有效数据中为零方差")
            else:
                errors.append(f"分析变量不存在: {var_id}")

        complete = numeric.dropna()
        if group_col and group_col in data.columns:
            complete = complete[data.loc[complete.index, group_col].notna()]
        sample_flow = {
            "original": int(len(numeric)),
            "included": int(len(complete)),
            "excluded": int(len(numeric) - len(complete)),
            "missingMethod": model_spec.get("estimation", {}).get(
                "missing", "complete_cases_per_model"
            ),
        }
        if complete.empty:
            errors.append("所选变量没有共同完整案例")
        elif sample_flow["excluded"] / sample_flow["original"] >= 0.2:
            warnings.append(
                _warning(
                    "HIGH_COMPLETE_CASE_LOSS",
                    f"完整案例分析将排除 {sample_flow['excluded']} 行（{sample_flow['excluded'] / sample_flow['original']:.1%}）。",
                )
            )

        result = {
            "valid": not errors,
            "structuralStatus": "valid" if not errors else "invalid",
            "errors": list(dict.fromkeys(errors)),
            "warnings": list({item["code"] + item["message"]: item for item in warnings}.values()),
            "template": "sem",
            "catalogVersion": summary["catalogVersion"],
            "matchStatus": "sem",
            "processModelNumber": None,
            "displayName": summary["displayName"],
            "executionAvailable": not errors,
            "unsupportedReason": None,
            "sampleFlow": sample_flow,
        }
        repository.set_precheck_cache_item(cache_key, result)
        return result

    for node in nodes:
        variable = available.get(node.get("variableId"))
        if variable is None:
            errors.append(f"节点 {node.get('id')} 引用了当前派生数据中不存在的变量")
            continue
        if node.get("kind") != variable["kind"]:
            errors.append(f"节点“{node.get('label')}”的 observed/scale_score 类型与数据字典不一致")
        if node.get("dataType") != variable["dataType"]:
            errors.append(f"节点“{node.get('label')}”的数据类型与数据字典不一致")

    sample_flow = {
        "original": dataset["rowCount"],
        "included": 0,
        "excluded": dataset["rowCount"],
        "missingMethod": "complete_cases_per_model",
    }
    if not nodes or any(node.get("variableId") not in available for node in nodes):
        result = {
            **summary,
            "valid": False,
            "structuralStatus": "invalid",
            "executionAvailable": False,
            "errors": list(dict.fromkeys(errors)),
            "warnings": warnings,
            "sampleFlow": sample_flow,
        }
        repository.set_precheck_cache_item(cache_key, result)
        return result

    data_path = resolve_derived_dataset_path(repository.settings.state_root, measurement)
    data = pd.read_parquet(data_path)
    numeric = pd.DataFrame(index=data.index)
    for node in nodes:
        variable = available[node["variableId"]]
        original = cast(pd.Series, data[variable["column"]])
        converted, encoding_errors = encode_node_series(node, original)
        errors.extend(encoding_errors)
        numeric[node["id"]] = converted
        if converted.dropna().nunique() <= 1:
            errors.append(f"变量“{variable['label']}”在有效数据中为零方差")

    complete = numeric.dropna()
    sample_flow = {
        "original": int(len(numeric)),
        "included": int(len(complete)),
        "excluded": int(len(numeric) - len(complete)),
        "missingMethod": "complete_cases_per_model",
    }
    if complete.empty:
        errors.append("所选变量没有共同完整案例")
    elif sample_flow["excluded"] / sample_flow["original"] >= 0.2:
        warnings.append(
            _warning(
                "HIGH_COMPLETE_CASE_LOSS",
                f"完整案例分析将排除 {sample_flow['excluded']} 行（{sample_flow['excluded'] / sample_flow['original']:.1%}）。",
            )
        )

    edge_by_id = {edge["id"]: edge for edge in model_spec.get("edges", [])}
    for outcome in [node for node in nodes if node.get("role") in {"m", "y"}]:
        predictors = [
            edge["from"]
            for edge in model_spec.get("edges", [])
            if edge.get("to") == outcome["id"] and edge.get("from") in numeric.columns
        ]
        for assignment in model_spec.get("covariates", []):
            if outcome["id"] in assignment.get("outcomeNodeIds", []):
                predictors.append(assignment["nodeId"])
        design_parts: list[np.ndarray] = []
        unique_predictors = list(dict.fromkeys(predictors))
        appended_moderators = set()
        if not complete.empty:
            for predictor in unique_predictors:
                design_parts.extend(predictor_columns(complete[predictor]))
        for moderation in model_spec.get("moderations", []):
            edge = edge_by_id.get(moderation.get("targetEdgeId"))
            if edge and edge.get("to") == outcome["id"] and not complete.empty:
                moderator_id = moderation.get("moderatorNodeId")
                secondary_moderator_id = moderation.get("secondaryModeratorNodeId")
                source_id = edge.get("from")
                if moderator_id in complete and source_id in complete:
                    if (
                        moderator_id not in unique_predictors
                        and moderator_id not in appended_moderators
                    ):
                        design_parts.append(complete[moderator_id].to_numpy(dtype=float))
                        appended_moderators.add(moderator_id)
                    if secondary_moderator_id in complete:
                        if (
                            secondary_moderator_id not in unique_predictors
                            and secondary_moderator_id not in appended_moderators
                        ):
                            design_parts.append(
                                complete[secondary_moderator_id].to_numpy(dtype=float)
                            )
                            appended_moderators.add(secondary_moderator_id)
                        design_parts.append(
                            complete[moderator_id].to_numpy(dtype=float)
                            * complete[secondary_moderator_id].to_numpy(dtype=float)
                        )
                        design_parts.append(
                            complete[source_id].to_numpy(dtype=float)
                            * complete[moderator_id].to_numpy(dtype=float)
                            * complete[secondary_moderator_id].to_numpy(dtype=float)
                        )
                    else:
                        design_parts.append(
                            complete[moderator_id].to_numpy(dtype=float)
                            * complete[source_id].to_numpy(dtype=float)
                        )
        if design_parts and not complete.empty:
            matrix = np.column_stack([np.ones(len(complete)), *design_parts])
            if np.linalg.matrix_rank(matrix) < matrix.shape[1]:
                errors.append(f"{outcome.get('role', '').upper()} 方程的设计矩阵完全共线")
            parameter_count = matrix.shape[1]
            if len(complete) < max(20, parameter_count * 5):
                warnings.append(
                    _warning(
                        "SMALL_EQUATION_SAMPLE",
                        f"{outcome.get('role', '').upper()} 方程仅有 {len(complete)} 个完整案例和 {parameter_count} 个参数，请谨慎解释。",
                    )
                )

    result = {
        "valid": not errors,
        "structuralStatus": "valid" if not errors else "invalid",
        "errors": list(dict.fromkeys(errors)),
        "warnings": list({item["code"] + item["message"]: item for item in warnings}.values()),
        "template": summary["template"],
        "catalogVersion": summary["catalogVersion"],
        "matchStatus": summary["matchStatus"],
        "processModelNumber": summary["processModelNumber"],
        "displayName": summary["displayName"],
        "executionAvailable": bool(summary["executionAvailable"] and not errors),
        "unsupportedReason": summary["unsupportedReason"],
        "sampleFlow": sample_flow,
    }
    repository.set_precheck_cache_item(cache_key, result)
    return result
