from __future__ import annotations

from app.services.status_model import apply_status_model


def test_normal_result_is_completed_with_reliable_conditional_inference() -> None:
    result = {
        "run": {"status": "succeeded"},
        "publicationEligible": True,
        "publicationEligibilityReasons": [],
    }
    apply_status_model(result)
    assert result["jobStatus"] == "completed"
    assert result["estimationStatus"] == "succeeded"
    assert result["inferenceStatus"] == "reliable"
    assert result["publicationEligibility"] == "conditional"


def test_sem_fit_failure_separates_job_completion_from_estimation_failure() -> None:
    result = {
        "run": {"status": "succeeded"},
        "semResult": {
            "publicationEligible": False,
            "requiresManualReview": True,
            "publicationEligibilityReasons": ["SEM_FIT_FAILED"],
        },
        "publicationEligibilityReasons": ["SEM_FIT_FAILED"],
    }
    apply_status_model(result)
    assert result["jobStatus"] == "completed"
    assert result["estimationStatus"] == "failed"
    assert result["inferenceStatus"] == "not_available"
    assert result["publicationEligibility"] == "ineligible"
    assert result["semResult"]["estimationStatus"] == "failed"  # type: ignore[index]


def test_regression_and_dsem_boundaries_are_explicit() -> None:
    regression = {
        "run": {"status": "succeeded"},
        "hierarchicalRegression": {
            "underdetermined": True,
            "publicationEligible": False,
            "publicationEligibilityReasons": ["REGRESSION_UNDERDETERMINED"],
        },
        "publicationEligibilityReasons": ["REGRESSION_UNDERDETERMINED"],
    }
    apply_status_model(regression)
    assert regression["estimationStatus"] == "not_run"
    assert regression["inferenceStatus"] == "not_available"

    dsem = {
        "run": {"status": "succeeded"},
        "diaryMultilevel": {
            "analysisType": "bayesian_dsem",
            "available": True,
            "validForInterpretation": False,
            "diagnostics": [{"code": "DSEM_RHAT_FAILED"}],
        },
    }
    apply_status_model(dsem)
    assert dsem["estimationStatus"] == "succeeded"
    assert dsem["inferenceStatus"] == "needs_review"
    assert dsem["publicationEligibility"] == "ineligible"
    assert dsem["diaryMultilevel"]["inferenceStatus"] == "needs_review"  # type: ignore[index]


def test_sem_boundary_solution_is_not_reported_as_successful_estimation() -> None:
    result = {
        "run": {"status": "succeeded"},
        "semResult": {
            "publicationEligible": False,
            "publicationEligibilityReasons": ["SEM_NEGATIVE_VARIANCE"],
        },
        "publicationEligibilityReasons": ["SEM_NEGATIVE_VARIANCE"],
    }
    apply_status_model(result)
    assert result["estimationStatus"] == "boundary_solution"
    assert result["inferenceStatus"] == "not_reliable"


def test_deviated_or_stale_study_plan_binding_blocks_publication_status() -> None:
    result = {
        "run": {"status": "succeeded"},
        "publicationEligible": True,
        "studyPlanBinding": {
            "status": "current",
            "declarationStatus": "deviated",
            "publicationEligible": False,
        },
    }
    apply_status_model(result)
    assert result["estimationStatus"] == "succeeded"
    assert result["inferenceStatus"] == "needs_review"
    assert result["publicationEligibility"] == "ineligible"
