from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, cast

ResultAvailability = Literal["available", "unavailable", "not_requested"]


def _availability(*, requested: bool, available: bool) -> ResultAvailability:
    if not requested:
        return "not_requested"
    return "available" if available else "unavailable"


def _mapping(value: object) -> Mapping[str, object]:
    return cast(Mapping[str, object], value) if isinstance(value, dict) else {}


def _item_count(value: object) -> int:
    return len(value) if isinstance(value, list) else 0


def _has_usable_records(value: object) -> bool:
    """Treat persisted rows explicitly marked unavailable as unavailable evidence."""
    if not isinstance(value, list):
        return False
    return any(
        record.get("available", True) is not False
        for item in value
        if (record := _mapping(item))
    )


def _explicitly_available(value: object) -> bool:
    return _mapping(value).get("available") is True


def summarize_result_availability(
    report: Mapping[str, object],
) -> dict[str, ResultAvailability]:
    """Describe report sections from persisted options and outputs, not live UI state."""
    options = _mapping(report.get("options"))
    regression = _mapping(report.get("hierarchicalRegression"))

    group_requested = bool(options.get("groupVariableId") or options.get("aggregationVariableId"))
    regression_requested = bool(
        options.get("outcomeVariableId") and options.get("predictorVariableIds")
    )
    advanced_requested = bool(
        _item_count(options.get("responseSurfacePredictorIds")) == 2
        or _item_count(options.get("predictorVariableIds")) > 1
    )
    longitudinal_requested = bool(options.get("longitudinalPanel"))
    diary_requested = bool(options.get("diaryMultilevel"))
    if procedure := options.get("procedure"):
        group_requested = procedure in {"groups", "aggregation"}
        regression_requested = procedure in {"regression", "relative_importance"}
        advanced_requested = procedure in {"relative_importance", "response_surface"}

    longitudinal = _mapping(report.get("longitudinalPanel"))
    diary = _mapping(report.get("diaryMultilevel"))
    return {
        "groups": _availability(
            requested=group_requested,
            available=_has_usable_records(
                _mapping(report.get("groupComparison")).get("results")
            )
            or _has_usable_records(_mapping(report.get("aggregationDiagnostics")).get("constructs")),
        ),
        "regression": _availability(
            requested=regression_requested,
            available=_has_usable_records(regression.get("blocks")),
        ),
        "advanced": _availability(
            requested=advanced_requested,
            available=bool(_mapping(regression.get("relativeImportance")).get("available"))
            or bool(_mapping(report.get("responseSurface")).get("available")),
        ),
        "longitudinal": _availability(
            requested=longitudinal_requested,
            available=_explicitly_available(longitudinal),
        ),
        "diary": _availability(
            requested=diary_requested,
            available=_explicitly_available(diary),
        ),
    }


def project_segment(report: Mapping[str, object], segment: str) -> dict[str, object]:
    """Project one persisted empirical report segment for HTTP presentation."""
    cfa = _mapping(report.get("cfa"))
    efa = _mapping(report.get("efa"))
    if segment == "summary":
        return {
            "reliability": report.get("reliability"),
            "resultAvailability": summarize_result_availability(report),
            "sample": report.get("sample"),
            "sampleFlow": report.get("sampleFlow"),
            "publicationEligible": report.get("publicationEligible"),
            "requiresManualReview": report.get("requiresManualReview"),
            "publicationEligibilityReasons": report.get("publicationEligibilityReasons"),
            "missingDataReport": report.get("missingDataReport"),
            "descriptives": report.get("descriptives"),
            "frequencies": report.get("frequencies"),
            "commonMethodBias": report.get("commonMethodBias"),
            "factorability": report.get("factorability"),
            "cfa": {
                "available": cfa.get("available"),
                "reason": cfa.get("reason"),
                "validForConfirmatoryInterpretation": cfa.get(
                    "validForConfirmatoryInterpretation"
                ),
            },
            "efa": {"factorCount": efa.get("factorCount")},
            "academicInterpretation": report.get("academicInterpretation"),
            "apaTables": report.get("apaTables"),
        }
    if segment == "correlation":
        return {
            "correlations": report.get("correlations"),
            "paperSummaryTable": report.get("paperSummaryTable"),
        }
    if segment == "efa_cfa":
        return {
            "efa": report.get("efa"),
            "cfa": report.get("cfa"),
            "advancedMeasurementBoundary": report.get("advancedMeasurementBoundary"),
        }
    if segment == "validity":
        return {
            "validity": report.get("validity"),
            "measurementInvariance": report.get("measurementInvariance") or None,
        }
    if segment == "regression":
        return {
            "groupComparison": report.get("groupComparison") or None,
            "aggregationDiagnostics": report.get("aggregationDiagnostics") or None,
            "hierarchicalRegression": report.get("hierarchicalRegression") or None,
            "responseSurface": report.get("responseSurface") or None,
            "multiplicity": report.get("multiplicity") or None,
        }
    if segment == "longitudinal":
        return {
            "longitudinalPanel": report.get("longitudinalPanel") or None,
            "diaryMultilevel": report.get("diaryMultilevel") or None,
        }
    raise ValueError(f"不支持的片段: {segment}")
