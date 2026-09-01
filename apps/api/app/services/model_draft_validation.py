"""Drafts may be incomplete; the execution ModelSpec contract remains strict."""
from __future__ import annotations

from pathlib import Path

from jsonschema import Draft202012Validator

from app.contracts import ContractValidationError, ModelSpec, load_json, validate_contract


def validate_draft_contract(model: ModelSpec, schema_path: Path) -> list[str]:
    # Only relax the root graph cardinality, retaining field types, ids, bounds,
    # estimator constraints and the shape of each node/edge/latent definition.
    schema = load_json(schema_path)
    graph_requirements = schema["allOf"][0]
    graph_requirements["else"]["properties"]["nodes"]["minItems"] = 0
    graph_requirements["else"]["properties"]["edges"]["minItems"] = 0
    graph_requirements["then"]["required"] = []
    graph_requirements["then"]["properties"]["latents"]["minItems"] = 0
    errors = list(Draft202012Validator(schema).iter_errors(model))
    if errors:
        raise ContractValidationError([
            f"{'.'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
            for error in errors
        ])
    try:
        validate_contract(model, schema_path)
    except ContractValidationError as error:
        return error.errors
    return []


def incomplete_draft_validation(errors: list[str]) -> ModelSpec:
    messages = [
        "请添加至少一条回归路径；未完成的草稿已保存。" if error.startswith("edges:")
        else "请补全 X、Y 等结构节点；未完成的草稿已保存。" if error.startswith("nodes:")
        else "请添加并配置测量因子；未完成的 SEM 草稿已保存。"
        for error in errors
    ]
    return {
        "valid": False, "structuralStatus": "invalid", "errors": messages,
        "warnings": [], "template": None, "catalogVersion": "5.0",
        "matchStatus": "invalid", "processModelNumber": None,
        "displayName": "未完成的模型草稿", "executionAvailable": False,
        "unsupportedReason": "草稿已保存；补全模型并通过检查后才能运行。",
        "sampleFlow": None,
    }
