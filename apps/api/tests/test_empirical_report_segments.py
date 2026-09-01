from app.services.empirical_report_segments import summarize_result_availability


def test_result_availability_uses_persisted_request_and_output() -> None:
    report = {
        "options": {
            "groupVariableId": "group",
            "outcomeVariableId": "y",
            "predictorVariableIds": ["x1", "x2"],
            "responseSurfacePredictorIds": [],
            "longitudinalPanel": {"modelType": "ri_clpm"},
            "diaryMultilevel": None,
        },
        "groupComparison": {"results": [{"id": "x1"}]},
        "hierarchicalRegression": {
            "blocks": [{"block": 1}],
            "relativeImportance": {"available": True},
        },
        "longitudinalPanel": {"available": True},
        "diaryMultilevel": None,
    }

    assert summarize_result_availability(report) == {
        "groups": "available",
        "regression": "available",
        "advanced": "available",
        "longitudinal": "available",
        "diary": "not_requested",
    }


def test_requested_section_without_usable_output_is_unavailable() -> None:
    report = {
        "options": {
            "groupVariableId": "group",
            "outcomeVariableId": "y",
            "predictorVariableIds": ["x"],
            "responseSurfacePredictorIds": ["x", "z"],
            "longitudinalPanel": None,
            "diaryMultilevel": {"analysisType": "lmm"},
        },
        "groupComparison": None,
        "aggregationDiagnostics": None,
        "hierarchicalRegression": None,
        "responseSurface": {"available": False},
        "longitudinalPanel": None,
        "diaryMultilevel": {"available": False},
    }

    assert summarize_result_availability(report) == {
        "groups": "unavailable",
        "regression": "unavailable",
        "advanced": "unavailable",
        "longitudinal": "not_requested",
        "diary": "unavailable",
    }


def test_cluster_aggregation_requests_groups_segment_without_group_comparisons() -> None:
    report = {
        "options": {
            "groupVariableId": None,
            "aggregationVariableId": "team_id",
            "outcomeVariableId": None,
            "predictorVariableIds": [],
            "responseSurfacePredictorIds": [],
            "longitudinalPanel": None,
            "diaryMultilevel": None,
        },
        "groupComparison": None,
        "aggregationDiagnostics": {"constructs": [{"id": "scale_x", "available": True}]},
        "hierarchicalRegression": None,
        "responseSurface": None,
        "longitudinalPanel": None,
        "diaryMultilevel": None,
    }

    result = summarize_result_availability(report)

    assert result["groups"] == "available"


def test_explicitly_unavailable_rows_and_partial_payloads_are_not_reported_as_results() -> None:
    report = {
        "options": {
            "groupVariableId": "group",
            "outcomeVariableId": "y",
            "predictorVariableIds": ["x1", "x2"],
            "responseSurfacePredictorIds": [],
            "longitudinalPanel": {"modelType": "clpm"},
            "diaryMultilevel": {"analysisType": "lmm"},
        },
        "groupComparison": {"results": [{"id": "x1", "available": False}]},
        "aggregationDiagnostics": {"constructs": [{"id": "x1", "available": False}]},
        "hierarchicalRegression": {"blocks": [{"block": 1, "available": False}]},
        "responseSurface": {"available": False, "reason": "insufficient usable rows"},
        "longitudinalPanel": {"reason": "did not converge"},
        "diaryMultilevel": {"available": None, "reason": "not estimated"},
    }

    assert summarize_result_availability(report) == {
        "groups": "unavailable",
        "regression": "unavailable",
        "advanced": "unavailable",
        "longitudinal": "unavailable",
        "diary": "unavailable",
    }
