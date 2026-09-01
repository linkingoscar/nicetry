from __future__ import annotations

# Pandas' dynamically typed column operations are isolated in this module;
# dataset contracts are checked elsewhere.
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
import hashlib
import re
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

IDENTIFIER_NAME = re.compile(r"(^|[_\s-])(id|uuid|编号|序号|代码|code)($|[_\s-])", re.IGNORECASE)


def _json_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _variable_id(name: str, index: int) -> str:
    digest = hashlib.sha256(f"{index}:{name}".encode("utf-8")).hexdigest()[:8]
    return f"var_{index + 1}_{digest}"


def _infer_type(series: pd.Series, name: str) -> tuple[str, float, str]:
    valid = series.dropna()
    unique_count = int(valid.nunique(dropna=True))
    if valid.empty:
        return "text", 0.3, "该列全部缺失，无法可靠推断"
    if unique_count == 2:
        return "binary", 0.96, "有效值恰好包含两个类别"
    name_suggests_id = IDENTIFIER_NAME.search(name) is not None
    unique_ratio = unique_count / len(valid)
    if name_suggests_id and unique_ratio >= 0.8:
        return "id", 0.94, "变量名包含标识符线索且取值高度唯一"
    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(valid, errors="coerce").dropna().to_numpy(dtype=float)
        all_integer = bool(np.all(np.isclose(numeric, np.round(numeric))))
        if all_integer and 3 <= unique_count <= 7:
            return "ordinal", 0.82, "整数取值为 3–7 个有序等级，疑似 Likert/等级变量"
        return "continuous", 0.9, "数值型且取值数量支持连续变量解释"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "text", 0.75, "日期时间暂作为非分析文本保留"
    if unique_ratio >= 0.95 and len(valid) >= 10:
        return "text", 0.78, "文本取值几乎全部唯一，疑似开放文本"
    if unique_count <= max(20, int(len(valid) * 0.2)):
        return "nominal", 0.86, "文本取值类别数相对较少"
    return "text", 0.82, "文本取值较多，疑似开放文本"


def profile_variables(dataframe: pd.DataFrame, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    variables: list[dict[str, Any]] = []
    row_count = len(dataframe)
    labels = metadata.get("labels", {})
    value_labels = metadata.get("valueLabels", {})
    for index, name in enumerate(dataframe.columns):
        series = dataframe[name]
        missing_count = int(series.isna().sum())
        missing_rate = missing_count / row_count
        unique_count = int(series.nunique(dropna=True))
        inferred_type, confidence, rationale = _infer_type(series, name)
        issues: list[str] = []
        if unique_count <= 1:
            issues.append("constant_or_empty")
        if missing_rate >= 0.2:
            issues.append("high_missing")
        valid_unique = series.dropna().drop_duplicates().head(5)
        variable: dict[str, Any] = {
            "id": _variable_id(name, index),
            "originalName": name,
            "label": labels.get(name) or name,
            "storageType": str(series.dtype),
            "inferredType": inferred_type,
            "confidence": confidence,
            "rationale": rationale,
            "missingCount": missing_count,
            "missingRate": missing_rate,
            "uniqueCount": unique_count,
            "sampleValues": [_json_value(value) for value in valid_unique.tolist()],
            "valueLabels": value_labels.get(name, {}),
            "issues": issues,
        }
        if pd.api.types.is_numeric_dtype(series) and not series.dropna().empty:
            variable["minimum"] = _json_value(series.min(skipna=True))
            variable["maximum"] = _json_value(series.max(skipna=True))
        variables.append(variable)
    return variables


def preview_dataset(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {name: _json_value(value) for name, value in row.items()}
        for row in dataframe.head(8).to_dict(orient="records")
    ]
