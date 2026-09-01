from __future__ import annotations

import pytest
from test_advanced_gold_standards import _run_r

from app.services.advanced_runner import _translate_r_failure
from app.services.repository_io import JsonObject


@pytest.mark.parametrize(
    ("predictor", "expected_code"),
    [
        ("DaysScaled100", "MLM_NONCONVERGENCE"),
        ("DaysScaled1e7", "MLM_RANDOM_EFFECTS_MATRIX_NOT_POSITIVE_DEFINITE"),
    ],
)
def test_multilevel_numerical_failures_have_stable_codes(
    predictor: str, expected_code: str
) -> None:
    completed, actual = _run_r(
        "sleepstudy-random-slope.spec.json",
        "sleepstudy.csv",
        mutate_spec={
            "fixedEffectIds": [predictor],
            "randomEffects": [
                {
                    "groupingVariableId": "Subject",
                    "intercept": True,
                    "slopeVariableIds": [predictor],
                    "covariance": "correlated",
                }
            ],
        },
    )
    assert completed.returncode != 0
    assert actual is None
    details = completed.stdout + completed.stderr
    assert expected_code in details
    translated = _translate_r_failure(details)
    assert translated.code == expected_code
    assert translated.details == details


@pytest.mark.parametrize(
    ("spec_name", "data_name", "mutate_spec", "expected_code"),
    [
        (
            "obrien-kaiser-phase.spec.json",
            "obrien-kaiser-incomplete-wave.csv",
            None,
            "EXPERIMENT_INCOMPLETE_WITHIN_SUBJECT_CELLS",
        ),
        (
            "obrien-kaiser-phase.spec.json",
            "obrien-kaiser-duplicate-cell.csv",
            None,
            "EXPERIMENT_DUPLICATE_SUBJECT_CELL",
        ),
        (
            "toothgrowth-factorial.spec.json",
            "toothgrowth-empty-cell.csv",
            None,
            "EXPERIMENT_EMPTY_CELL",
        ),
        (
            "moore-ancova.spec.json",
            "moore-ancova.csv",
            {"covariateIds": ["fscore", "fscore_duplicate"]},
            "EXPERIMENT_DESIGN_MATRIX_RANK_DEFICIENT",
        ),
    ],
)
def test_experimental_layout_and_estimability_failures_have_stable_codes(
    spec_name: str,
    data_name: str,
    mutate_spec: JsonObject | None,
    expected_code: str,
) -> None:
    completed, actual = _run_r(spec_name, data_name, mutate_spec=mutate_spec)
    assert completed.returncode != 0
    assert actual is None
    details = completed.stdout + completed.stderr
    assert expected_code in details
    assert _translate_r_failure(details).code == expected_code


def test_multilevel_singular_boundary_is_not_reported_as_clean_convergence() -> None:
    predictor = "DaysScaled1e4"
    completed, actual = _run_r(
        "sleepstudy-random-slope.spec.json",
        "sleepstudy.csv",
        mutate_spec={
            "fixedEffectIds": [predictor],
            "randomEffects": [
                {
                    "groupingVariableId": "Subject",
                    "intercept": True,
                    "slopeVariableIds": [predictor],
                    "covariance": "correlated",
                }
            ],
        },
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert actual is not None
    assert "SINGULAR_FIT" in {warning["code"] for warning in actual["warnings"]}
    convergence = next(
        item for item in actual["diagnostics"] if item["code"] == "MODEL_CONVERGENCE"
    )
    assert convergence["severity"] == "warning"
    assert "singular boundary" in convergence["message"]


def test_longitudinal_non_positive_definite_matrix_never_produces_success() -> None:
    completed, actual = _run_r(
        "demo-growth-fiml.spec.json",
        "longitudinal-non-positive-definite.csv",
        mutate_spec={"missing": "complete_cases"},
    )
    assert completed.returncode != 0
    assert actual is None
    details = completed.stdout + completed.stderr
    expected_codes = {
        "LONGITUDINAL_SAMPLE_COVARIANCE_NOT_POSITIVE_DEFINITE",
        "LONGITUDINAL_NONCONVERGENCE",
        "LONGITUDINAL_POST_ESTIMATION_INVALID",
    }
    matched = expected_codes.intersection(details.split())
    assert len(matched) == 1, details
    translated = _translate_r_failure(details)
    assert translated.code == matched.pop()
