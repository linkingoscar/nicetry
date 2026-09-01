from __future__ import annotations

import math
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import numpy as np
import pandas as pd

from app.contracts import file_sha256
from app.services.dataset_repository import (
    DatasetRepository,
    MeasurementNotFoundError,
    _write_json_atomic,
)
from app.services.owned_resources import resolve_normalized_dataset_path

Aggregation = Literal["mean", "sum"]
MAX_OMEGA_ITEM_DELETION_WORK = 50_000_000


class MeasurementError(ValueError):
    pass


def _validate_omega_work_budget(item_count: int) -> None:
    deletion_work = item_count * max(0, item_count - 1) ** 3
    if deletion_work > MAX_OMEGA_ITEM_DELETION_WORK:
        raise MeasurementError("构念题项过多，逐题删除 omega 计算超过 5000 万矩阵工作单元限制")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite_or_none(value: float | np.floating[Any]) -> float | None:
    number = float(value)
    return number if math.isfinite(number) else None


def _correlation(left: pd.Series, right: pd.Series) -> float | None:
    paired = pd.concat([left, right], axis=1).dropna()
    if len(paired) < 2 or paired.iloc[:, 0].nunique() < 2 or paired.iloc[:, 1].nunique() < 2:
        return None
    return _finite_or_none(paired.iloc[:, 0].corr(paired.iloc[:, 1]))


def cronbach_alpha(items: pd.DataFrame) -> float | None:
    complete = items.dropna()
    item_count = complete.shape[1]
    if item_count < 2 or len(complete) < 2:
        return None
    item_variances = complete.var(axis=0, ddof=1)
    total_variance = complete.sum(axis=1).var(ddof=1)
    if not math.isfinite(float(total_variance)) or total_variance <= 0:
        return None
    alpha = (
        item_count / (item_count - 1) * (1 - float(item_variances.sum()) / float(total_variance))
    )
    return _finite_or_none(alpha)


def spearman_brown_reliability(items: pd.DataFrame) -> float | None:
    """Spearman-Brown prophecy formula for two-item scales.

    When a construct has only two items, a one-factor congeneric model
    (omega) is not identified.  Spearman-Brown is the standard
    alternative: SB = 2r / (1 + r).
    """
    complete = items.dropna()
    if complete.shape[1] != 2 or len(complete) < 3:
        return None
    if complete.iloc[:, 0].nunique() < 2 or complete.iloc[:, 1].nunique() < 2:
        return None
    r = float(complete.iloc[:, 0].corr(complete.iloc[:, 1]))
    if not math.isfinite(r):
        return None
    denominator = 1 + r
    if abs(denominator) <= np.finfo(float).eps:
        return None
    return _finite_or_none(2 * r / denominator)


def mcdonald_omega(items: pd.DataFrame) -> float | None:
    """One-factor omega total using principal-axis factor extraction.

    Omega is deliberately unavailable below three items because a one-factor
    congeneric model is not identified there.
    """

    complete = items.dropna()
    if complete.shape[1] < 3 or len(complete) < 3:
        return None
    if any(complete[column].nunique() < 2 for column in complete.columns):
        return None
    correlation = complete.corr().to_numpy(dtype=float)
    if not np.all(np.isfinite(correlation)):
        return None
    try:
        inverse = np.linalg.pinv(correlation)
        communalities = np.clip(1 - 1 / np.diag(inverse), 0.05, 0.99)
        loadings = np.zeros(complete.shape[1], dtype=float)
        for _ in range(100):
            reduced = correlation.copy()
            np.fill_diagonal(reduced, communalities)
            eigenvalues, eigenvectors = np.linalg.eigh(reduced)
            largest = int(np.argmax(eigenvalues))
            if eigenvalues[largest] <= 0:
                return None
            next_loadings = eigenvectors[:, largest] * math.sqrt(eigenvalues[largest])
            if next_loadings.sum() < 0:
                next_loadings *= -1
            next_communalities = np.clip(next_loadings**2, 0, 0.999999)
            loadings = next_loadings
            if np.max(np.abs(next_communalities - communalities)) < 1e-8:
                break
            communalities = next_communalities
        uniqueness = np.clip(1 - loadings**2, 0, None)
        common = float(loadings.sum() ** 2)
        denominator = common + float(uniqueness.sum())
        if denominator <= 0:
            return None
        return _finite_or_none(common / denominator)
    except np.linalg.LinAlgError:
        return None


def _describe_score(score: pd.Series) -> dict[str, Any]:
    valid = score.dropna()
    if valid.empty:
        return {
            "validCount": 0,
            "missingCount": int(score.isna().sum()),
            "mean": None,
            "standardDeviation": None,
            "minimum": None,
            "q1": None,
            "median": None,
            "q3": None,
            "maximum": None,
        }
    quantiles = valid.quantile([0.25, 0.5, 0.75])
    return {
        "validCount": int(valid.count()),
        "missingCount": int(score.isna().sum()),
        "mean": _finite_or_none(valid.mean()),
        "standardDeviation": _finite_or_none(valid.std(ddof=1)) if len(valid) > 1 else None,
        "minimum": _finite_or_none(valid.min()),
        "q1": _finite_or_none(quantiles.loc[0.25]),
        "median": _finite_or_none(quantiles.loc[0.5]),
        "q3": _finite_or_none(quantiles.loc[0.75]),
        "maximum": _finite_or_none(valid.max()),
    }


def _analyse_construct(
    transformed: pd.DataFrame,
    item_definitions: list[dict[str, Any]],
    theoretical_minimum: float,
    theoretical_maximum: float,
    score: pd.Series,
) -> dict[str, Any]:
    complete = transformed.dropna()
    item_analysis: list[dict[str, Any]] = []
    for item in item_definitions:
        item_id = item["id"]
        series = transformed[item_id]
        valid = series.dropna()
        other_items = transformed.drop(columns=[item_id])
        corrected_total = other_items.sum(axis=1, min_count=other_items.shape[1])
        item_analysis.append(
            {
                "itemId": item_id,
                "label": item["label"],
                "reversed": item["reversed"],
                "validCount": int(valid.count()),
                "missingCount": int(series.isna().sum()),
                "mean": _finite_or_none(valid.mean()) if not valid.empty else None,
                "standardDeviation": (
                    _finite_or_none(valid.std(ddof=1)) if len(valid) > 1 else None
                ),
                "floorRate": (
                    _finite_or_none(np.isclose(valid, theoretical_minimum).mean())
                    if not valid.empty
                    else None
                ),
                "ceilingRate": (
                    _finite_or_none(np.isclose(valid, theoretical_maximum).mean())
                    if not valid.empty
                    else None
                ),
                "correctedItemTotalCorrelation": _correlation(series, corrected_total),
                "alphaIfDeleted": cronbach_alpha(other_items),
                "omegaIfDeleted": mcdonald_omega(other_items),
            }
        )
    is_two_item = transformed.shape[1] == 2
    result = {
        "completeCaseCount": int(len(complete)),
        "alpha": cronbach_alpha(transformed),
        "omega": mcdonald_omega(transformed),
        "itemAnalysis": item_analysis,
        "scoreDistribution": _describe_score(score),
    }
    if is_two_item:
        result["spearmanBrown"] = spearman_brown_reliability(transformed)
        result["reliabilityMethod"] = "spearman_brown"
    else:
        result["reliabilityMethod"] = "omega" if transformed.shape[1] >= 3 else "alpha_only"
    return result


def build_measurement_version(
    dataset_id: str,
    constructs: list[dict[str, Any]],
    repository: DatasetRepository,
    change_note: str | None = None,
) -> dict[str, Any]:
    dataset = repository.get_dataset(dataset_id)
    if dataset["dictionary"]["status"] != "confirmed":
        raise MeasurementError("请先确认全部变量类型，再建立构念")
    if not constructs:
        raise MeasurementError("至少定义一个构念")

    variables = {variable["id"]: variable for variable in dataset["variables"]}
    assigned_items: dict[str, str] = {}
    construct_ids: set[str] = set()
    construct_names: set[str] = set()
    normalized_constructs: list[dict[str, Any]] = []
    for construct in constructs:
        name = construct["name"].strip()
        if not name:
            raise MeasurementError("构念名称不能为空")
        if construct["id"] in construct_ids:
            raise MeasurementError(f"构念 ID 重复: {construct['id']}")
        if name in construct_names:
            raise MeasurementError(f"构念名称重复: {name}")
        construct_ids.add(construct["id"])
        construct_names.add(name)
        item_ids = list(dict.fromkeys(construct["itemIds"]))
        reverse_ids = list(dict.fromkeys(construct.get("reverseItemIds", [])))
        if len(item_ids) < 2:
            raise MeasurementError(f"构念“{construct['name']}”至少需要两个题项")
        _validate_omega_work_budget(len(item_ids))
        unknown = sorted(set(item_ids) - variables.keys())
        if unknown:
            raise MeasurementError("未知题项 ID: " + ", ".join(unknown))
        if not set(reverse_ids).issubset(item_ids):
            raise MeasurementError(f"构念“{construct['name']}”的反向题必须属于该构念")
        for item_id in item_ids:
            variable = variables[item_id]
            if variable["confirmedType"] not in {"likert", "ordinal", "continuous"}:
                raise MeasurementError(f"题项“{variable['label']}”不是已确认的数值/Likert 变量")
            if item_id in assigned_items:
                raise MeasurementError(
                    f"题项“{variable['label']}”已属于构念“{assigned_items[item_id]}”"
                )
            assigned_items[item_id] = construct["name"]
        minimum = float(construct["theoreticalMinimum"])
        maximum = float(construct["theoreticalMaximum"])
        proportion = float(construct["minimumValidProportion"])
        if not math.isfinite(minimum) or not math.isfinite(maximum) or minimum >= maximum:
            raise MeasurementError(f"构念“{construct['name']}”的理论上下限无效")
        if not math.isfinite(proportion) or not 0 < proportion <= 1:
            raise MeasurementError(f"构念“{construct['name']}”的有效题项比例必须在 0–1 之间")
        normalized_constructs.append(
            {
                "id": construct["id"],
                "name": name,
                "itemIds": item_ids,
                "reverseItemIds": reverse_ids,
                "theoreticalMinimum": minimum,
                "theoreticalMaximum": maximum,
                "aggregation": construct["aggregation"],
                "minimumValidProportion": proportion,
                "minimumValidItems": math.ceil(proportion * len(item_ids) - 1e-12),
                "outputVariableId": f"scale_{construct['id'].removeprefix('construct_')}",
            }
        )

    try:
        previous = repository.get_measurement(dataset_id)
    except MeasurementNotFoundError:
        previous = None
    if previous is not None:
        previous_items = {
            (construct["id"], item_id)
            for construct in previous["constructs"]
            for item_id in construct["itemIds"]
        }
        current_items = {
            (construct["id"], item_id)
            for construct in normalized_constructs
            for item_id in construct["itemIds"]
        }
        if previous_items - current_items and not (change_note or "").strip():
            raise MeasurementError("删除既有题项或构念时必须填写版本说明与理论依据")

    normalized_path = resolve_normalized_dataset_path(repository.settings.state_root, dataset)
    source_data = pd.read_parquet(normalized_path)
    derived_data = source_data.copy(deep=True)
    reports: list[dict[str, Any]] = []
    preview = pd.DataFrame(index=source_data.index)
    for construct in normalized_constructs:
        transformed = pd.DataFrame(index=source_data.index)
        item_definitions: list[dict[str, Any]] = []
        for item_id in construct["itemIds"]:
            variable = variables[item_id]
            original = source_data[variable["originalName"]]
            column = pd.to_numeric(original, errors="coerce")
            nonnumeric = original.notna() & column.isna()
            if nonnumeric.any():
                raise MeasurementError(
                    f"题项“{variable['label']}”有 {int(nonnumeric.sum())} 个非数值取值"
                )
            invalid = column.notna() & (
                (column < construct["theoreticalMinimum"])
                | (column > construct["theoreticalMaximum"])
            )
            if invalid.any():
                raise MeasurementError(
                    f"题项“{variable['label']}”有 {int(invalid.sum())} 个值超出理论范围 "
                    f"[{construct['theoreticalMinimum']:g}, {construct['theoreticalMaximum']:g}]"
                )
            is_reversed = item_id in construct["reverseItemIds"]
            transformed[item_id] = (
                construct["theoreticalMinimum"] + construct["theoreticalMaximum"] - column
                if is_reversed
                else column
            )
            item_definitions.append(
                {"id": item_id, "label": variable["label"], "reversed": is_reversed}
            )
        valid_count = transformed.notna().sum(axis=1)
        eligible = valid_count >= construct["minimumValidItems"]
        if construct["aggregation"] == "mean":
            score = transformed.mean(axis=1, skipna=True).where(eligible)
        else:
            score = transformed.sum(axis=1, skipna=True).where(eligible)
        output_id = construct["outputVariableId"]
        derived_data[output_id] = score
        preview[output_id] = score
        report = _analyse_construct(
            transformed,
            item_definitions,
            construct["theoreticalMinimum"],
            construct["theoreticalMaximum"],
            score,
        )
        report.update({"constructId": construct["id"], "outputVariableId": output_id})
        reports.append(report)

    version = repository.next_measurement_version(dataset_id)
    created_at = _utc_now()
    measurement_id = f"measurement_{uuid.uuid4().hex[:16]}"
    root = (
        repository.settings.state_root
        / "projects"
        / "default"
        / "datasets"
        / dataset_id
        / "measurement"
        / f"v{version}"
    )
    derived_path = root / "derived.parquet"
    definition_path = root / "measurement.json"
    root.mkdir(parents=True, exist_ok=True)
    temporary = derived_path.with_suffix(".parquet.tmp")
    derived_data.to_parquet(temporary, index=False, engine="pyarrow")
    os.replace(temporary, derived_path)
    measurement_warnings: list[dict[str, str]] = []
    for construct, report in zip(normalized_constructs, reports, strict=True):
        if len(construct["itemIds"]) != 2:
            continue
        spearman_brown = report.get("spearmanBrown")
        if spearman_brown is None:
            measurement_warnings.append(
                {
                    "code": "SPEARMAN_BROWN_UNAVAILABLE",
                    "severity": "warning",
                    "message": (
                        f"构念“{construct['name']}”的两题项相关无法支持 Spearman-Brown；"
                        "请核对常量、完全负相关、反向题与编码。"
                    ),
                }
            )
        elif spearman_brown <= 0:
            measurement_warnings.append(
                {
                    "code": "TWO_ITEM_NONPOSITIVE_CORRELATION",
                    "severity": "warning",
                    "message": (
                        f"构念“{construct['name']}”的两题项相关为非正；已按标准 2r/(1+r) 报告，"
                        "但正式解释前必须核对反向题、编码与单维性。"
                    ),
                }
            )
        else:
            measurement_warnings.append(
                {
                    "code": "OMEGA_UNAVAILABLE_SPEARMAN_BROWN_USED",
                    "severity": "info",
                    "message": f"构念“{construct['name']}”仅两个题项，ω 不可识别，已使用标准 Spearman-Brown 公式替代。",
                }
            )

    response = {
        "schemaVersion": "1.0.0",
        "id": measurement_id,
        "datasetVersionId": dataset_id,
        "version": version,
        "createdAt": created_at,
        "changeNote": (change_note or "").strip() or None,
        "status": "ready_for_model_canvas",
        "constructs": normalized_constructs,
        "reports": reports,
        "derivedDataset": {
            "id": f"derived_{uuid.uuid4().hex[:16]}",
            "sourceDatasetVersionId": dataset_id,
            "measurementVersion": version,
            "storage": derived_path.relative_to(repository.settings.state_root).as_posix(),
            "sha256": file_sha256(derived_path),
            "rowCount": int(len(derived_data)),
            "columnCount": int(derived_data.shape[1]),
            "scoreVariables": [
                {
                    "id": construct["outputVariableId"],
                    "label": construct["name"],
                    "type": "scale_score",
                }
                for construct in normalized_constructs
            ],
        },
        "transformationPreview": [
            {key: (None if pd.isna(value) else float(value)) for key, value in row.items()}
            for row in preview.head(8).to_dict(orient="records")
        ],
        "transformationLog": [
            {
                "constructId": construct["id"],
                "message": (
                    f"{construct['name']}: {len(construct['itemIds'])} 题，"
                    f"{len(construct['reverseItemIds'])} 个反向题，"
                    f"{construct['aggregation']}，至少 {construct['minimumValidItems']} 题有效"
                ),
            }
            for construct in normalized_constructs
        ],
        "warnings": measurement_warnings
        + [
            {
                "code": "OMEGA_UNAVAILABLE",
                "severity": "warning",
                "message": f"构念“{construct['name']}”少于两个题项，信度不可估计。",
            }
            for construct in normalized_constructs
            if len(construct["itemIds"]) < 2
        ],
    }
    _write_json_atomic(definition_path, response)
    repository.record_measurement(
        dataset_id,
        version,
        created_at,
        definition_path,
        derived_path,
        len(normalized_constructs),
    )
    return response
