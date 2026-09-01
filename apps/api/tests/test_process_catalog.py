from __future__ import annotations

import pytest

from app.process_catalog import (
    EXECUTABLE_PROCESS_MODELS,
    PROCESS_CATALOG_VERSION,
    PROCESS_MODEL_BITS,
    PROCESS_REFERENCE_SOURCE,
    PROCESS_SPECIAL_RULES,
    _base_edges,
    _mediator_limits,
    _model_moderations,
    match_process_model,
)
from app.semantics import validate_model_semantics

EXPECTED_PROCESS_50_MODELS = {
    *range(1, 23),
    28,
    29,
    *range(58, 74),
    75,
    76,
    *range(80, 93),
}


def _catalog_spec(model_number: int, mediator_count: int | None = None) -> dict:
    minimum, _maximum = _mediator_limits(model_number)
    count = minimum if mediator_count is None else mediator_count
    mediators = tuple(f"m{index + 1}" for index in range(count))
    edges = sorted(_base_edges(model_number, mediators))
    moderations = sorted(_model_moderations(model_number, mediators))
    roles = {"x": "x", "y": "y", **{mediator: "m" for mediator in mediators}}
    if any(moderator in {"w", "wz"} for moderator, *_ in moderations):
        roles["w"] = "w"
    if any(moderator in {"z", "wz"} for moderator, *_ in moderations):
        roles["z"] = "z"
    edge_items = [
        {"id": f"edge_{source}_{target}", "from": source, "to": target, "kind": "regression"}
        for source, target in edges
    ]
    edge_id_by_pair = {
        (edge["from"], edge["to"]): edge["id"] for edge in edge_items
    }
    moderation_items = []
    for index, (moderator, source, target) in enumerate(moderations):
        moderation_items.append(
            {
                "id": f"mod_{index}",
                "moderatorNodeId": "z" if moderator == "z" else "w",
                **({"secondaryModeratorNodeId": "z"} if moderator == "wz" else {}),
                "targetEdgeId": edge_id_by_pair[(source, target)],
                "productTermId": f"term_{index}",
                **({"moderatorProductTermId": f"term_wz_{index}"} if moderator == "wz" else {}),
            }
        )
    return {
        "schemaVersion": "1.0.0",
        "modelId": f"catalog_model_{model_number}",
        "name": f"PROCESS Model {model_number}",
        "datasetVersionId": "derived_catalog",
        "design": {
            "timeStructure": "cross_sectional",
            "clustering": "none",
            "claimMode": "associational",
        },
        "nodes": [
            {
                "id": node_id,
                "variableId": f"var_{node_id}",
                "label": node_id.upper(),
                "kind": "observed",
                "role": role,
                "dataType": "continuous",
            }
            for node_id, role in roles.items()
        ],
        "edges": edge_items,
        "moderations": moderation_items,
        "covariates": [],
        "estimation": {
            "family": "ols",
            "standardErrors": "hc3",
            "confidenceLevel": 0.95,
            "bootstrap": {
                "enabled": True,
                "replicates": 5000,
                "method": "percentile",
                "seed": 20250730,
            },
            "missing": "complete_cases_per_model",
            "centering": {"method": "none", "nodeIds": []},
            "reportScale": "unstandardized_primary",
        },
    }


def test_process_50_catalog_has_authoritative_active_number_set() -> None:
    assert PROCESS_CATALOG_VERSION == "5.0"
    assert set(PROCESS_MODEL_BITS) == EXPECTED_PROCESS_50_MODELS
    assert len(PROCESS_MODEL_BITS) == 55
    assert 74 not in PROCESS_MODEL_BITS


@pytest.mark.parametrize("model_number", sorted(EXPECTED_PROCESS_50_MODELS))
def test_every_process_50_number_round_trips_from_its_topology(model_number: int) -> None:
    spec = _catalog_spec(model_number)
    match = match_process_model(spec)

    assert match.match_status == "exact"
    assert match.model_number == model_number
    assert match.execution_available is (model_number in EXECUTABLE_PROCESS_MODELS)


def test_parallel_mediator_variant_is_executable_when_the_catalog_allows_it() -> None:
    match = match_process_model(_catalog_spec(4, mediator_count=2))

    assert match.model_number == 4
    assert match.execution_available is True
    assert match.unsupported_reason is None


def test_valid_custom_topology_is_not_misreported_as_an_error() -> None:
    spec = _catalog_spec(4)
    spec["edges"].append(
        {"id": "edge_m1_x", "from": "m1", "to": "x", "kind": "regression"}
    )
    # Replace the invalid cycle with a valid, unnumbered topology: remove X→Y.
    spec["edges"] = [
        edge
        for edge in spec["edges"]
        if (edge["from"], edge["to"]) not in {("x", "y"), ("m1", "x")}
    ]

    validation = validate_model_semantics(spec)

    assert validation["valid"] is True
    assert validation["matchStatus"] == "custom"
    assert validation["executionAvailable"] is False
    assert validation["template"] is None


def test_model_82_and_92_keep_their_distinct_special_topologies() -> None:
    model_82 = _catalog_spec(82)
    model_92 = _catalog_spec(92)

    edges_82 = {(edge["from"], edge["to"]) for edge in model_82["edges"]}
    assert {("m1", "m2"), ("m3", "m4")} <= edges_82
    assert ("m1", "m3") not in edges_82

    serial_edges_92 = {
        (moderation["targetEdgeId"], moderation["moderatorNodeId"])
        for moderation in model_92["moderations"]
    }
    assert ("edge_m1_m2", "w") in serial_edges_92
    assert ("edge_x_y", "w") in serial_edges_92


def test_process_reference_is_declared_as_external() -> None:
    assert PROCESS_REFERENCE_SOURCE == "external user-provided PROCESS for R 5.0 macro"
    assert PROCESS_SPECIAL_RULES["serialEdgesModeratedByW"] == (91, 92)
