from __future__ import annotations

import pandas as pd
import pytest

from app.services.study_structure_profile import profile_structure


def _frame(subjects: list[int], times: list[int], clusters: list[str] | None = None) -> pd.DataFrame:
    data: dict[str, object] = {"subject": subjects, "time": times}
    if clusters is not None:
        data["cluster"] = clusters
    return pd.DataFrame(data)


def test_cross_sectional_independent_roles_are_valid() -> None:
    frame = _frame([1, 2, 3, 4], [0, 0, 0, 0])
    profile, status, warnings = profile_structure(frame, {})
    assert status == "valid"
    assert warnings == []
    assert profile["nestingClassification"] == "none"


def test_cross_sectional_nested_combines_cluster_checks() -> None:
    many = _frame(
        list(range(1, 49)),
        [0] * 48,
        [f"c{i}" for i in range(1, 25)] * 2,
    )
    profile, status, warnings = profile_structure(many, {"clusterId": "cluster"})
    assert status == "valid"
    assert warnings == []
    assert profile["nestingClassification"] == "two_level"
    assert profile["clusterCount"] == 24

    few = _frame([1, 2, 3, 4], [0, 0, 0, 0], ["c1", "c2", "c1", "c2"])
    _, few_status, few_warnings = profile_structure(few, {"clusterId": "cluster"})
    assert few_status == "warning"
    assert any(
        warning["code"] == "FEW_CLUSTERS" and warning["severity"] == "warning"
        for warning in few_warnings
    )

    single = _frame([1, 2, 3], [0, 0, 0], ["c1", "c1", "c1"])
    _, single_status, single_warnings = profile_structure(single, {"clusterId": "cluster"})
    assert single_status == "invalid"
    assert any(
        warning["code"] == "INSUFFICIENT_CLUSTERS" and warning["severity"] == "error"
        for warning in single_warnings
    )


def test_panel_subject_time_duplicate_is_blocked() -> None:
    frame = _frame([1, 1, 2, 2], [1, 1, 1, 2])
    profile, status, warnings = profile_structure(
        frame, {"subjectId": "subject", "timeId": "time"}
    )
    assert status == "invalid"
    assert any(
        warning["code"] == "DUPLICATE_SUBJECT_TIME" and warning["severity"] == "error"
        for warning in warnings
    )
    assert profile["duplicateSubjectTimeCount"] == 2

    clean = _frame([1, 1, 2, 2], [1, 2, 1, 2])
    _, clean_status, _ = profile_structure(
        clean, {"subjectId": "subject", "timeId": "time"}
    )
    assert clean_status == "valid"
    assert profile["timePointCount"] == 2


def test_nested_panel_with_time_is_three_level() -> None:
    frame = _frame(
        list(range(1, 25)) + list(range(1, 25)),
        [1] * 24 + [2] * 24,
        [f"c{i}" for i in range(1, 25)] * 2,
    )
    profile, status, _ = profile_structure(
        frame, {"subjectId": "subject", "timeId": "time", "clusterId": "cluster"}
    )
    assert status == "valid"
    assert profile["nestingClassification"] == "three_level"


def test_cross_classified_detection() -> None:
    frame = _frame(
        [1, 1, 2, 2],
        [1, 2, 1, 2],
        ["c1", "c2", "c1", "c2"],
    )
    profile, _, _ = profile_structure(
        frame, {"subjectId": "subject", "timeId": "time", "clusterId": "cluster"}
    )
    assert profile["nestingClassification"] == "cross_classified"


def test_intensive_longitudinal_roles_are_valid_and_block_duplicates() -> None:
    frame = _frame([1, 1, 1, 2, 2], [1, 2, 3, 1, 2])
    profile, status, _ = profile_structure(
        frame, {"subjectId": "subject", "timeId": "time"}
    )
    assert status == "valid"
    assert profile["observationsPerSubject"] == {
        "minimum": 2,
        "median": 2.5,
        "maximum": 3,
    }

    duplicated = _frame([1, 1, 2], [1, 1, 1])
    _, duplicated_status, duplicated_warnings = profile_structure(
        duplicated, {"subjectId": "subject", "timeId": "time"}
    )
    assert duplicated_status == "invalid"
    assert any(
        warning["code"] == "DUPLICATE_SUBJECT_TIME" for warning in duplicated_warnings
    )


def test_missing_role_variable_is_rejected() -> None:
    frame = _frame([1, 2], [0, 0])
    with pytest.raises(ValueError, match="STRUCTURE_ROLE_INVALID"):
        profile_structure(frame, {"clusterId": "missing_column"})
