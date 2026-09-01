from __future__ import annotations

# Pandas' dynamically typed column/index operations are isolated in this
# service; API and persistence contracts remain statically checked elsewhere.
# pyright: reportAttributeAccessIssue=false, reportArgumentType=false, reportIndexIssue=false, reportOperatorIssue=false, reportAssignmentType=false, reportCallIssue=false
import json
import uuid

import numpy as np
import pandas as pd

from app.data_quality_contracts import (
    AnalysisSampleVersion,
    AnalysisSampleVersionRequest,
    ExclusionRuleInput,
    QualityCasePage,
)
from app.services.data_quality import (
    DataQualityError,
    PandasFrame,
    PandasSeries,
    _as_json_value,
    _canonical_json,
    _sha256_bytes,
    _write_parquet_atomic,
)
from app.services.dataset_repository import DatasetRepository
from app.services.repository_io import _write_json_atomic
from app.settings import Settings


def _rule_column(metric: str) -> str:
    return {
        "duration_seconds": "durationSeconds",
        "relative_duration": "relativeDuration",
        "missing_rate": "missingRate",
        "structural_missing_rate": "structuralMissingRate",
        "longstring_max": "longstringMax",
        "response_variance": "responseVariance",
        "straightline_ratio": "straightlineRatio",
        "extreme_response_ratio": "extremeResponseRatio",
        "duplicate_response_id": "duplicateResponseId",
        "duplicate_ip": "duplicateIp",
        "duplicate_device": "duplicateDevice",
        "attention_check_failed": "attentionCheckFailed",
        "duplicate_text": "duplicateText",
        "empty_text": "emptyText",
        "mahalanobis_distance": "mahalanobisDistance",
    }[metric]


_BOOLEAN_METRICS = {
    "duplicate_response_id",
    "duplicate_ip",
    "duplicate_device",
    "attention_check_failed",
    "duplicate_text",
    "empty_text",
}


def _rule_mask(series: PandasSeries, rule: ExclusionRuleInput) -> PandasSeries:
    threshold: object = rule.threshold
    if threshold is None and rule.metric in _BOOLEAN_METRICS:
        threshold = True
    if rule.operator == "in":
        values = threshold if isinstance(threshold, list) else [threshold]
        return series.isin(values)
    if threshold is None:
        raise DataQualityError(f"规则 {rule.id} 缺少 threshold")
    if rule.metric not in _BOOLEAN_METRICS:
        series = pd.to_numeric(series, errors="coerce")
        try:
            threshold = float(threshold)
        except (TypeError, ValueError) as error:
            raise DataQualityError(f"规则 {rule.id} 的 threshold 必须是数值") from error
    if rule.operator == "lt":
        return series.lt(threshold).fillna(False)
    if rule.operator == "lte":
        return series.le(threshold).fillna(False)
    if rule.operator == "gt":
        return series.gt(threshold).fillna(False)
    if rule.operator == "gte":
        return series.ge(threshold).fillna(False)
    if rule.operator == "eq":
        return series.eq(threshold).fillna(False)
    if rule.operator == "neq":
        return series.ne(threshold).fillna(False)
    raise DataQualityError(f"不支持的规则操作符: {rule.operator}")


def _boundary_mask(series: PandasSeries, rule: ExclusionRuleInput) -> PandasSeries:
    if rule.threshold is None or isinstance(rule.threshold, list):
        return pd.Series(False, index=series.index)
    if rule.metric in _BOOLEAN_METRICS:
        return series.eq(rule.threshold).fillna(False)
    numeric = pd.to_numeric(series, errors="coerce")
    return pd.Series(
        np.isclose(numeric.to_numpy(dtype=float), float(rule.threshold), equal_nan=False),
        index=series.index,
    )


def create_analysis_sample(
    dataset_id: str,
    request: AnalysisSampleVersionRequest,
    settings: Settings,
    repository: DatasetRepository,
) -> AnalysisSampleVersion:
    dataset = repository.get_dataset(dataset_id)
    quality_run = repository.get_data_quality_run(dataset_id, request.quality_run_id)
    quality_path = repository.get_data_quality_case_path(dataset_id, request.quality_run_id)
    cases: PandasFrame = pd.read_parquet(quality_path)
    enabled_rules = [rule for rule in request.rules if rule.enabled]
    masks: list[PandasSeries] = []
    boundaries: list[PandasSeries] = []
    for rule in enabled_rules:
        column = _rule_column(rule.metric)
        if column not in cases.columns:
            raise DataQualityError(f"质量运行缺少规则所需指标: {rule.metric}")
        masks.append(_rule_mask(cases[column], rule))
        boundaries.append(_boundary_mask(cases[column], rule))

    if masks:
        combined = masks[0].copy()
        boundary = boundaries[0].copy()
        matched = [
            [enabled_rules[0].id] if bool(combined.iloc[index]) else []
            for index in range(len(cases))
        ]
        for rule, mask, boundary_mask in zip(
            enabled_rules[1:], masks[1:], boundaries[1:], strict=False
        ):
            if request.combine_operator == "and":
                combined &= mask
            else:
                combined |= mask
            boundary |= boundary_mask
            for index, value in enumerate(mask.tolist()):
                if value:
                    matched[index].append(rule.id)
    else:
        combined = pd.Series(False, index=cases.index)
        boundary = pd.Series(False, index=cases.index)
        matched = [[] for _ in range(len(cases))]

    sample_cases: PandasFrame = pd.DataFrame(
        {
            "caseIndex": cases["caseIndex"].astype(int),
            "caseId": cases["caseId"].map(_as_json_value),
            "included": (~combined).astype(bool),
            "boundary": boundary.astype(bool),
            "matchedRuleIds": [json.dumps(items, ensure_ascii=False) for items in matched],
        }
    )
    sample_id = f"sample_{uuid.uuid4().hex[:16]}"
    sample_root = (
        settings.state_root
        / "projects"
        / "default"
        / "datasets"
        / dataset_id
        / "quality"
        / "samples"
        / sample_id
    )
    case_path = sample_root / "cases.parquet"
    sample_path = sample_root / "sample.json"
    _write_parquet_atomic(sample_cases, case_path)
    case_hash = _sha256_bytes(case_path.read_bytes())
    request_dump = request.model_dump(by_alias=True)
    sample_hash = _sha256_bytes(
        _canonical_json(
            {
                "datasetSha256": dataset["originalFile"]["sha256"],
                "qualityCaseMetricsHash": quality_run["caseMetricsHash"],
                "request": request_dump,
                "caseRecordsHash": case_hash,
            }
        ).encode("utf-8")
    )
    invalidated = repository.invalidate_dataset_results(
        dataset_id, sample_id, sample_hash, reason="AnalysisSampleVersion changed"
    )
    payload = AnalysisSampleVersion(
        id=sample_id,
        dataset_version_id=dataset_id,
        dataset_sha256=str(dataset["originalFile"]["sha256"]),
        quality_run_id=request.quality_run_id,
        created_at=pd.Timestamp.utcnow().isoformat(),
        label=request.label,
        combine_operator=request.combine_operator,
        rules=request.rules,
        row_count=len(sample_cases),
        included_count=int(sample_cases["included"].sum()),
        excluded_count=int((~sample_cases["included"]).sum()),
        boundary_count=int(sample_cases["boundary"].sum()),
        sample_hash=sample_hash,
        case_records_path=case_path.relative_to(settings.state_root).as_posix(),
        case_records_hash=case_hash,
        invalidated_analysis_ids=invalidated,
    )
    _write_json_atomic(sample_path, payload.model_dump(by_alias=True))
    repository.record_analysis_sample(payload.model_dump(by_alias=True), sample_path)
    return payload


def read_quality_case_page(
    dataset_id: str,
    quality_run_id: str,
    settings: Settings,
    repository: DatasetRepository,
    offset: int,
    limit: int,
) -> QualityCasePage:
    if offset < 0 or limit < 1 or limit > 1000:
        raise DataQualityError("分页参数超出范围")
    path = repository.get_data_quality_case_path(dataset_id, quality_run_id)
    cases: PandasFrame = pd.read_parquet(path)
    page = cases.iloc[offset : offset + limit].copy()
    return QualityCasePage(
        items=[
            {str(key): _as_json_value(value) for key, value in row.items()}
            for row in page.to_dict("records")
        ],
        offset=offset,
        limit=limit,
        total=len(cases),
    )


def read_sample_case_page(
    dataset_id: str,
    sample_id: str,
    settings: Settings,
    repository: DatasetRepository,
    offset: int,
    limit: int,
) -> QualityCasePage:
    if offset < 0 or limit < 1 or limit > 1000:
        raise DataQualityError("分页参数超出范围")
    path = repository.get_analysis_sample_case_path(dataset_id, sample_id)
    cases: PandasFrame = pd.read_parquet(path)
    page = cases.iloc[offset : offset + limit].copy()
    items: list[dict[str, object]] = []
    for row in page.to_dict("records"):
        rendered = {str(key): _as_json_value(value) for key, value in row.items()}
        try:
            rendered["matchedRuleIds"] = json.loads(str(row.get("matchedRuleIds", "[]")))
        except json.JSONDecodeError:
            rendered["matchedRuleIds"] = []
        items.append(rendered)
    return QualityCasePage(items=items, offset=offset, limit=limit, total=len(cases))
