"""Explicit single-procedure selection; None preserves historical bundle requests."""
from typing import Literal

EmpiricalProcedure = Literal[
    "descriptives", "frequencies", "missing", "correlation", "reliability",
    "efa", "cfa", "validity", "common_method", "invariance", "groups",
    "aggregation", "regression", "relative_importance", "response_surface", "longitudinal", "diary",
]

PROCEDURE_SLICES = {
    **dict.fromkeys(
        ("descriptives", "frequencies", "missing", "correlation"),
        "empirical.cross_sectional.overview",
    ),
    **dict.fromkeys(
        ("reliability", "efa", "cfa", "validity", "common_method", "invariance"),
        "empirical.cross_sectional.measurement",
    ),
    "groups": "empirical.cross_sectional.group_comparison",
    "aggregation": "multilevel_model.aggregation.icc_rwg",
    "relative_importance": "empirical.cross_sectional.hierarchical_regression",
    "regression": "empirical.cross_sectional.hierarchical_regression",
    "response_surface": "empirical.cross_sectional.response_surface",
}
