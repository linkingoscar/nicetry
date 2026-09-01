from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

NUMERIC_ENCODINGS = {"as_is", "mean_center", "standardize", "ordinal_score"}


def encoding_method(node: dict[str, Any]) -> str:
    configured = node.get("encoding", {}).get("method")
    if configured:
        return str(configured)
    return {
        "binary": "binary_indicator",
        "nominal": "treatment",
        "ordinal": "ordinal_score",
    }.get(node.get("dataType"), "as_is")


def encode_node_series(node: dict[str, Any], source: pd.Series) -> tuple[pd.Series, list[str]]:
    method = encoding_method(node)
    label = node.get("label", node.get("id", "变量"))
    errors: list[str] = []
    text = source.astype("string")
    valid_text = text.dropna()
    configured_levels = [str(value) for value in node.get("encoding", {}).get("levels", [])]
    levels = configured_levels or sorted(valid_text.unique().tolist())

    if method in {"binary_indicator", "treatment"}:
        required = 2 if method == "binary_indicator" else 1
        if len(levels) < required:
            errors.append(f"变量“{label}”没有足够的有效类别用于编码")
            return pd.Series(np.nan, index=source.index), errors
        if method == "binary_indicator" and len(levels) != 2:
            errors.append(f"二分类变量“{label}”必须恰好包含两个水平")
        unknown = valid_text[~valid_text.isin(levels)]
        if not unknown.empty:
            errors.append(f"变量“{label}”包含未在编码顺序中声明的类别")
        reference = node.get("encoding", {}).get("referenceLevel")
        if reference is not None and str(reference) in levels:
            levels = [str(reference), *[level for level in levels if level != str(reference)]]
        if method == "binary_indicator":
            mapping = {level: index for index, level in enumerate(levels[:2])}
            return text.map(mapping).astype(float), errors
        return pd.Series(pd.Categorical(text, categories=levels), index=source.index), errors

    if method == "ordinal_score" and configured_levels:
        mapping = {level: index + 1 for index, level in enumerate(configured_levels)}
        encoded = text.map(mapping).astype(float)
        unknown = source.notna() & encoded.isna()
        if unknown.any():
            errors.append(f"变量“{label}”包含未在有序水平中声明的取值")
        return encoded, errors

    numeric = pd.to_numeric(source, errors="coerce")
    nonnumeric = source.notna() & numeric.isna()
    if nonnumeric.any():
        errors.append(f"变量“{label}”包含 {int(nonnumeric.sum())} 个无法按数值编码的取值")
    if method == "mean_center":
        numeric = numeric - numeric.mean()
    elif method == "standardize":
        standard_deviation = numeric.std(ddof=1)
        if not np.isfinite(standard_deviation) or standard_deviation <= 0:
            errors.append(f"变量“{label}”无法标准化（标准差为零或不可估计）")
        else:
            numeric = (numeric - numeric.mean()) / standard_deviation
    return numeric, errors


def predictor_columns(series: pd.Series) -> list[np.ndarray]:
    if isinstance(series.dtype, pd.CategoricalDtype):
        encoded = pd.get_dummies(series, drop_first=True, dtype=float)
        return [encoded[column].to_numpy(dtype=float) for column in encoded.columns]
    return [series.to_numpy(dtype=float)]
