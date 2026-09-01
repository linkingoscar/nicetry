from __future__ import annotations

import re
from typing import cast

from app.services.repository_io import JsonObject

_REPORT_FACT_KINDS = {"estimate", "fit", "diagnostic", "warning", "sample_flow"}
_ARRAY_INDEX = re.compile(r"^(0|[1-9][0-9]*)$")
_INVALID_ESCAPE = re.compile(r"~(?![01])")


def _pointer_tokens(pointer: object, fact_id: str) -> list[str]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError(f"REPORT_FACT_SOURCE_PATH_INVALID: {fact_id} 必须使用 JSON Pointer")
    tokens: list[str] = []
    for encoded in pointer[1:].split("/"):
        if _INVALID_ESCAPE.search(encoded):
            raise ValueError(f"REPORT_FACT_SOURCE_PATH_INVALID: {fact_id} 的 JSON Pointer 无效")
        tokens.append(encoded.replace("~1", "/").replace("~0", "~"))
    return tokens


def resolve_json_pointer(document: object, pointer: object, fact_id: str = "pointer") -> object:
    tokens = _pointer_tokens(pointer, fact_id)
    current = document
    for token in tokens:
        if isinstance(current, dict):
            if token not in current:
                raise ValueError(
                    f"REPORT_FACT_SOURCE_PATH_NOT_FOUND: {fact_id} 未找到 {pointer}"
                )
            current = current[token]
        elif isinstance(current, list):
            if not _ARRAY_INDEX.fullmatch(token):
                raise ValueError(
                    f"REPORT_FACT_SOURCE_PATH_INVALID: {fact_id} 的数组索引无效"
                )
            index = int(token)
            if index >= len(current):
                raise ValueError(
                    f"REPORT_FACT_SOURCE_PATH_NOT_FOUND: {fact_id} 未找到 {pointer}"
                )
            current = current[index]
        else:
            raise ValueError(
                f"REPORT_FACT_SOURCE_PATH_NOT_FOUND: {fact_id} 未找到 {pointer}"
            )
    return current


def _raw_facts(result: JsonObject) -> list[dict[str, object]]:
    if "reportFacts" not in result:
        return []
    raw = result["reportFacts"]
    if not isinstance(raw, list):
        raise ValueError("REPORT_FACTS_INVALID: reportFacts 必须是数组")
    facts: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("REPORT_FACTS_INVALID: reportFacts 元素必须是对象")
        facts.append(cast(dict[str, object], item))
    return facts


def resolve_report_facts(
    result: JsonObject,
) -> list[tuple[dict[str, object], list[tuple[str, object]]]]:
    """Resolve report facts against the result bundle without persisting values."""
    facts = _raw_facts(result)
    if not facts:
        return []
    source_result_id = _result_id(result)
    resolved: list[tuple[dict[str, object], list[tuple[str, object]]]] = []
    seen_fact_ids: set[str] = set()
    for fact in facts:
        fact_id = str(fact.get("factId", "")).strip()
        if not fact_id:
            raise ValueError("REPORT_FACTS_INVALID: factId 不能为空")
        if fact_id in seen_fact_ids:
            raise ValueError(f"REPORT_FACTS_INVALID: factId {fact_id} 不得重复")
        seen_fact_ids.add(fact_id)
        if "values" in fact:
            raise ValueError(
                f"REPORT_FACT_VALUES_FORBIDDEN: {fact_id} 不得保存复制的统计值"
            )
        if fact.get("kind") not in _REPORT_FACT_KINDS:
            raise ValueError(f"REPORT_FACTS_INVALID: {fact_id} 的 kind 无效")
        if fact.get("sourceResultId") != source_result_id:
            raise ValueError(
                f"REPORT_FACT_SOURCE_RESULT_MISMATCH: {fact_id} 未引用当前结果"
            )
        paths = fact.get("sourcePaths")
        if not isinstance(paths, list) or not paths:
            raise ValueError(f"REPORT_FACTS_INVALID: {fact_id} 必须包含 sourcePaths")
        if any(not isinstance(path, str) for path in paths):
            raise ValueError(f"REPORT_FACTS_INVALID: {fact_id} 的 sourcePaths 必须是字符串")
        string_paths = cast(list[str], paths)
        if len(string_paths) != len(set(string_paths)):
            raise ValueError(f"REPORT_FACTS_INVALID: {fact_id} 的 sourcePaths 不得重复")
        if any(path == "/reportFacts" or path.startswith("/reportFacts/") for path in string_paths):
            raise ValueError(f"REPORT_FACT_SOURCE_PATH_FORBIDDEN: {fact_id} 不得引用 reportFacts 自身")
        values = [
            (path, resolve_json_pointer(result, path, fact_id))
            for path in string_paths
        ]
        resolved.append((fact, values))
    return resolved


def _result_id(result: JsonObject) -> str:
    run = result.get("run")
    run_id = run.get("id") if isinstance(run, dict) else None
    if not isinstance(run_id, str) or not run_id:
        run_id = result.get("reportId")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("REPORT_FACT_SOURCE_RESULT_INVALID: 结果缺少 run.id/reportId")
    return run_id


def build_report_facts(result: JsonObject) -> list[dict[str, object]]:
    """Create deterministic references for stable result fields."""
    source_result_id = _result_id(result)
    facts: list[dict[str, object]] = []
    estimates = result.get("estimates")
    if isinstance(estimates, list):
        for index, item in enumerate(estimates):
            if not isinstance(item, dict) or "id" not in item:
                continue
            paths = [
                f"/estimates/{index}/{key}"
                for key in (
                    "estimate",
                    "standardError",
                    "statistic",
                    "pValue",
                    "confidenceLower",
                    "confidenceUpper",
                )
                if key in item
            ]
            if paths:
                facts.append(
                    {
                        "factId": f"estimate_{index}_{item['id']}",
                        "kind": "estimate",
                        "sourceResultId": source_result_id,
                        "sourcePaths": paths,
                        "semanticRole": "estimate",
                        "presentationHints": {"preferredLabel": item.get("label", item["id"])},
                    }
                )
    equations = result.get("equations")
    if isinstance(equations, list):
        for equation_index, equation in enumerate(equations):
            coefficients = equation.get("coefficients") if isinstance(equation, dict) else None
            if not isinstance(coefficients, list):
                continue
            for coefficient_index, coefficient in enumerate(coefficients):
                if not isinstance(coefficient, dict) or "estimate" not in coefficient:
                    continue
                base = f"/equations/{equation_index}/coefficients/{coefficient_index}"
                paths = [
                    f"{base}/{key}"
                    for key in ("estimate", "standardError", "pValue", "confidenceInterval")
                    if key in coefficient
                ]
                facts.append({
                    "factId": f"equation_{equation_index}_coefficient_{coefficient_index}",
                    "kind": "estimate", "sourceResultId": source_result_id,
                    "sourcePaths": paths, "semanticRole": "model_coefficient",
                    "presentationHints": {"preferredLabel": coefficient.get("label", coefficient.get("term", "coefficient"))},
                })
    effects = result.get("effects")
    if isinstance(effects, list):
        for index, effect in enumerate(effects):
            if not isinstance(effect, dict) or "estimate" not in effect:
                continue
            paths = [f"/effects/{index}/estimate"]
            if "confidenceInterval" in effect:
                paths.append(f"/effects/{index}/confidenceInterval")
            facts.append({
                "factId": f"effect_{index}_{effect.get('id', index)}", "kind": "estimate",
                "sourceResultId": source_result_id, "sourcePaths": paths,
                "semanticRole": "effect", "presentationHints": {"preferredLabel": effect.get("label", effect.get("id", "effect"))},
            })
    sem_result = result.get("semResult")
    if isinstance(sem_result, dict):
        fit_indices = sem_result.get("fitIndices")
        if isinstance(fit_indices, dict) and fit_indices:
            facts.append({
                "factId": "sem_fit", "kind": "fit", "sourceResultId": source_result_id,
                "sourcePaths": [f"/semResult/fitIndices/{key}" for key in fit_indices],
                "semanticRole": "model_fit",
            })
        paths = sem_result.get("paths")
        if isinstance(paths, list):
            for index, path in enumerate(paths):
                if not isinstance(path, dict) or "estimate" not in path:
                    continue
                fact_paths = [
                    f"/semResult/paths/{index}/{key}"
                    for key in ("estimate", "standardError", "pValue", "ciLower", "ciUpper")
                    if key in path
                ]
                facts.append({
                    "factId": f"sem_path_{index}", "kind": "estimate",
                    "sourceResultId": source_result_id, "sourcePaths": fact_paths,
                    "semanticRole": "structural_path",
                    "presentationHints": {"preferredLabel": f"{path.get('from', '')} → {path.get('to', '')}"},
                })
    descriptives = result.get("descriptives")
    if isinstance(descriptives, list):
        for index, row in enumerate(descriptives):
            if not isinstance(row, dict):
                continue
            paths = [
                f"/descriptives/{index}/{key}"
                for key in ("n", "mean", "sd", "missing")
                if key in row
            ]
            if paths:
                facts.append({
                    "factId": f"descriptive_{index}", "kind": "estimate",
                    "sourceResultId": source_result_id, "sourcePaths": paths,
                    "semanticRole": "descriptive", "presentationHints": {"preferredLabel": row.get("label", index)},
                })
    sample_flow = result.get("sampleFlow")
    if isinstance(sample_flow, dict):
        paths = [
            f"/sampleFlow/{key}"
            for key in ("original", "included", "excluded")
            if key in sample_flow
        ]
        if paths:
            facts.append(
                {
                    "factId": "sample_flow",
                    "kind": "sample_flow",
                    "sourceResultId": source_result_id,
                    "sourcePaths": paths,
                    "semanticRole": "sample_flow",
                }
            )
    elif isinstance(result.get("sample"), dict):
        sample = cast(dict[str, object], result["sample"])
        paths = [f"/sample/{key}" for key in ("rowCount", "itemCompleteCases") if key in sample]
        if paths:
            facts.append({
                "factId": "sample", "kind": "sample_flow", "sourceResultId": source_result_id,
                "sourcePaths": paths, "semanticRole": "sample_flow",
            })
    for key, kind in (("diagnostics", "diagnostic"), ("warnings", "warning")):
        messages = result.get(key)
        if not isinstance(messages, list):
            continue
        for index, item in enumerate(messages):
            if not isinstance(item, dict) or "message" not in item:
                continue
            code = str(item.get("code", index))
            facts.append(
                {
                    "factId": f"{kind}_{code}_{index}",
                    "kind": kind,
                    "sourceResultId": source_result_id,
                    "sourcePaths": [f"/{key}/{index}/message"],
                    "semanticRole": kind,
                    "presentationHints": {"preferredLabel": code},
                }
            )
    return facts


def ensure_report_facts(result: JsonObject) -> JsonObject:
    if "reportFacts" not in result:
        result["reportFacts"] = build_report_facts(result)
    resolve_report_facts(result)
    return result


def report_fact_rows(result: JsonObject) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for fact, values in resolve_report_facts(result):
        hints = fact.get("presentationHints")
        label = hints.get("preferredLabel") if isinstance(hints, dict) else None
        for path, value in values:
            row: JsonObject = {
                "factId": fact["factId"],
                "semanticRole": fact["semanticRole"],
                "sourcePath": path,
                "value": value,
            }
            if isinstance(label, str) and label:
                row["label"] = label
            rows.append(row)
    return rows
