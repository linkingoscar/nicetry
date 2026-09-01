from __future__ import annotations

from typing import Any

import pandas as pd


def compile_sem_model(
    model_spec: dict[str, Any], data: pd.DataFrame, available_variables: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """
    编译 ModelSpec 0.3.0 结构方程模型为 lavaan 语法字符串，并进行预检和约束。
    包含：
    1. 测量方程编译 (e.g. F1 =~ item1 + item2 + item3)
    2. 结构方程编译 (e.g. F2 ~ F1)
    3. 控制变量按显式目标方程投影（潜变量或观测变量）
    4. 分组变量取值数量限制 (<= 5)
    5. 返回编译后的 R 运行参数（lavaanSyntax, requiredVariables, orderedVariables）
    """
    errors: list[str] = []
    warnings: list[dict[str, str]] = []

    # 提取基本元素
    nodes = model_spec.get("nodes", [])
    edges = model_spec.get("edges", [])
    latents = model_spec.get("latents", [])
    covariates = model_spec.get("covariates", [])
    estimation = model_spec.get("estimation", {})
    if estimation.get("estimator") == "WLSMV" and estimation.get("missing") == "fiml":
        errors.append("WLSMV 不支持 FIML；请改用完整案例处理，或在连续指标下选择 ML+FIML")

    node_by_id = {node.get("id"): node for node in nodes}

    # 1. 验证潜变量定义及其题项
    required_variables: set[str] = set()
    ordered_variables: set[str] = set()

    measurement_lines: list[str] = []
    latent_ids = {str(lat.get("id")) for lat in latents}
    for lat in latents:
        latent_id = lat.get("id")
        indicators = lat.get("indicators", [])
        level = lat.get("level", "first_order")

        if len(indicators) < 2:
            errors.append(f"潜变量“{lat.get('name', latent_id)}”至少需要 2 个测量指标")
        if level == "higher_order" and len(indicators) < 3:
            errors.append(f"高阶潜变量“{lat.get('name', latent_id)}”至少需要 3 个低阶潜变量")

        indicator_cols = []
        for ind_id in indicators:
            if ind_id in latent_ids:
                if level != "higher_order":
                    errors.append(f"一阶潜变量 {latent_id} 不能引用潜变量指标 {ind_id}")
                    continue
                indicator_cols.append(ind_id)
                continue
            if level == "higher_order":
                errors.append(f"高阶潜变量 {latent_id} 只能引用已定义的低阶潜变量，不能引用 {ind_id}")
                continue
            node = node_by_id.get(ind_id)
            if node is None:
                # 也可能是直接引用的原始变量 ID
                var_info = available_variables.get(ind_id)
                if var_info is None:
                    errors.append(f"潜变量 {latent_id} 引用的指标 {ind_id} 不存在")
                    continue
                col_name = ind_id
                data_type = var_info["dataType"]
            else:
                col_name = node.get("variableId", ind_id)
                data_type = node.get("dataType")

            indicator_cols.append(col_name)
            required_variables.add(col_name)

            # 若估计器为 WLSMV，且变量在字典中是 Likert 或有序分类，则需声明为 ordered
            if estimation.get("estimator") == "WLSMV":
                if data_type in ("ordinal", "likert"):
                    ordered_variables.add(col_name)

        if indicator_cols:
            measurement_lines.append(f"{latent_id} =~ " + " + ".join(indicator_cols))

    # 2. 识别回归路径与内生变量
    structural_dict: dict[str, list[str]] = {}

    for edge in edges:
        from_id = edge.get("from")
        to_id = edge.get("to")

        # 确定在 lavaan 中对应的名称
        # 如果是潜变量，直接使用其潜变量 ID，如果是观测变量，使用其 variableId
        from_name = from_id
        if from_id in node_by_id:
            node_from = node_by_id[from_id]
            if node_from.get("kind") != "latent":
                from_name = node_from.get("variableId", from_id)
                required_variables.add(from_name)

        to_name = to_id
        if to_id in node_by_id:
            node_to = node_by_id[to_id]
            if node_to.get("kind") != "latent":
                to_name = node_to.get("variableId", to_id)
                required_variables.add(to_name)

        structural_dict.setdefault(to_name, []).append(from_name)

    # 3. 严格按画布中的目标方程分配控制变量；空目标不产生隐式路径。
    for cov in covariates:
        cov_id = cov.get("nodeId")
        node_cov = node_by_id.get(cov_id)
        if not node_cov or node_cov.get("kind") == "latent":
            errors.append(f"控制变量 {cov_id} 必须引用有效观测节点")
            continue
        cov_name = node_cov.get("variableId", cov_id)
        for target_id in cov.get("outcomeNodeIds", []):
            target = node_by_id.get(target_id)
            if not target or target_id == cov_id:
                errors.append(f"控制变量 {cov_id} 引用了无效目标 {target_id}")
                continue
            target_name = target_id if target.get("kind") == "latent" else target.get("variableId", target_id)
            predictors = structural_dict.setdefault(target_name, [])
            if cov_name not in predictors:
                predictors.append(cov_name)
            required_variables.add(cov_name)
            if target.get("kind") != "latent":
                required_variables.add(target_name)

    # 构建结构方程语法
    structural_lines: list[str] = []
    for to_name, predictors in structural_dict.items():
        structural_lines.append(f"{to_name} ~ " + " + ".join(predictors))

    # 组合为完整 lavaan 语法
    lavaan_syntax = "\n".join(measurement_lines + structural_lines)

    # 4. 校验多组分析的分组变量取值
    group_var_id = estimation.get("groupVariableId")
    if group_var_id:
        node_group = node_by_id.get(group_var_id)
        group_col = group_var_id
        if node_group:
            group_col = node_group.get("variableId", group_var_id)

        required_variables.add(group_col)

        group_data_col = group_col
        if group_col in available_variables:
            group_data_col = available_variables[group_col]["column"]

        if group_data_col in data.columns:
            unique_levels = data[group_data_col].dropna().unique()
            level_count = len(unique_levels)
            if level_count > 5:
                errors.append(
                    f"分组变量“{group_var_id}”取值过多（共有 {level_count} 个），测量等值性分析的分组取值数不得超过 5 个"
                )
            elif level_count < 2:
                errors.append(
                    f"分组变量“{group_var_id}”的有效组数不足（仅有 {level_count} 个），多组分析至少需要 2 组"
                )
        else:
            errors.append(f"数据集中未找到分组变量“{group_var_id}”对应的列")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "lavaanSyntax": lavaan_syntax,
        "requiredVariables": list(required_variables),
        "orderedVariables": list(ordered_variables),
    }
