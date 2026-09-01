from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from test_process_catalog import _catalog_spec

from app.process_catalog import (
    EXECUTABLE_PROCESS_MODELS,
    _mediator_limits,
    _model_moderations,
)
from app.services.r_engine import EngineExecutionError, run_mediation
from app.settings import get_settings

GENERIC_PROCESS_MODELS = sorted(
    EXECUTABLE_PROCESS_MODELS - {1, 2, 3, 4, 5, 6, 7, 8, 14, 15, 21, 22, 58, 59}
)


def _write_catalog_data(path: Path, model_number: int, mediator_count: int) -> None:
    rng = np.random.default_rng(20260730 + model_number + mediator_count)
    size = 260
    columns: dict[str, np.ndarray] = {
        "var_x": rng.normal(size=size),
        "var_y": rng.normal(size=size),
        "var_w": rng.normal(size=size),
        "var_z": rng.normal(size=size),
    }
    for index in range(1, mediator_count + 1):
        columns[f"var_m{index}"] = rng.normal(size=size)
    pd.DataFrame(columns).to_csv(path, index=False)


def _assert_equations_match_numpy(result: dict, spec: dict, data_path: Path) -> None:
    source = pd.read_csv(data_path)
    values = {
        node["id"]: source[node["variableId"]].to_numpy(dtype=float) for node in spec["nodes"]
    }
    edge_by_id = {edge["id"]: edge for edge in spec["edges"]}
    for moderation in spec["moderations"]:
        edge = edge_by_id[moderation["targetEdgeId"]]
        primary = values[moderation["moderatorNodeId"]]
        secondary_id = moderation.get("secondaryModeratorNodeId")
        if secondary_id:
            secondary = values[secondary_id]
            values[moderation["moderatorProductTermId"]] = primary * secondary
            values[moderation["productTermId"]] = values[edge["from"]] * primary * secondary
        else:
            values[moderation["productTermId"]] = values[edge["from"]] * primary

    for equation in result["equations"]:
        outcome, predictor_text = (
            part.strip() for part in equation["formula"].split("~", maxsplit=1)
        )
        predictors = [part.strip() for part in predictor_text.split("+")]
        design = np.column_stack(
            [np.ones(len(values[outcome])), *(values[item] for item in predictors)]
        )
        expected = np.linalg.lstsq(design, values[outcome], rcond=None)[0]
        actual = {
            coefficient["term"]: coefficient["estimate"] for coefficient in equation["coefficients"]
        }
        for index, predictor in enumerate(predictors, start=1):
            assert actual[predictor] == pytest.approx(expected[index], abs=1e-8)


@pytest.mark.parametrize("model_number", GENERIC_PROCESS_MODELS)
def test_every_new_process_model_executes_through_generic_engine(
    model_number: int,
    tmp_path: Path,
) -> None:
    minimum, _maximum = _mediator_limits(model_number)
    spec = _catalog_spec(model_number, mediator_count=minimum)
    spec["estimation"]["bootstrap"]["enabled"] = False
    spec["estimation"]["standardErrors"] = "classical"
    data_path = tmp_path / f"process-model-{model_number}.csv"
    _write_catalog_data(data_path, model_number, minimum)

    result = run_mediation(spec, data_path, get_settings())

    assert result["run"]["template"] == f"model_{model_number}"
    reference = result["provenance"]["processReference"]
    assert reference["version"] == "5.0"
    assert reference["available"] is False
    assert len(result["equations"]) == minimum + 1
    assert len({equation["id"] for equation in result["equations"]}) == minimum + 1
    indirect = [
        effect for effect in result["effects"] if effect["type"] in {"indirect", "conditional"}
    ]
    assert indirect
    assert all(math.isfinite(effect["estimate"]) for effect in result["effects"])
    assert len({effect["id"] for effect in result["effects"]}) == len(result["effects"])
    assert any(effect["id"] == "effect_total" for effect in result["effects"])
    if not spec["moderations"]:
        assert any(effect["id"] == "effect_total_indirect" for effect in result["effects"])
    mediator_names = tuple(f"m{index}" for index in range(1, minimum + 1))
    if _model_moderations(model_number, mediator_names):
        assert any(effect["type"] == "index" for effect in result["effects"])
    _assert_equations_match_numpy(result, spec, data_path)


@pytest.mark.parametrize(
    ("model_number", "mediator_count"),
    [(4, 3), (6, 4), (80, 6), (81, 6), (83, 6), (92, 6)],
)
def test_variable_mediator_count_variants_execute(
    model_number: int,
    mediator_count: int,
    tmp_path: Path,
) -> None:
    spec = _catalog_spec(model_number, mediator_count=mediator_count)
    spec["estimation"]["bootstrap"]["enabled"] = False
    data_path = tmp_path / f"process-model-{model_number}-{mediator_count}.csv"
    _write_catalog_data(data_path, model_number, mediator_count)

    result = run_mediation(spec, data_path, get_settings())

    assert result["run"]["template"] == f"model_{model_number}"
    assert len(result["equations"]) == mediator_count + 1
    assert any(effect["type"] in {"indirect", "conditional"} for effect in result["effects"])
    _assert_equations_match_numpy(result, spec, data_path)


def test_binary_mediator_is_rejected_with_explicit_boundary_code(tmp_path: Path) -> None:
    spec = _catalog_spec(4)
    for node in spec["nodes"]:
        if node["role"] == "m":
            node["dataType"] = "binary"
            node["encoding"] = {"method": "binary_indicator"}
    spec["estimation"]["bootstrap"]["enabled"] = False
    data_path = tmp_path / "process-binary-mediator.csv"
    rng = np.random.default_rng(20260815)
    pd.DataFrame(
        {
            "var_x": rng.normal(size=300),
            "var_y": rng.normal(size=300),
            "var_m1": rng.integers(0, 2, size=300),
        }
    ).to_csv(data_path, index=False)

    with pytest.raises(EngineExecutionError, match="BINARY_MEDIATOR_NOT_SUPPORTED") as error:
        run_mediation(spec, data_path, get_settings())
    diagnostic = getattr(error.value, "diagnostic", {})
    assert "stderr" in diagnostic
    assert "BINARY_MEDIATOR_NOT_SUPPORTED" in diagnostic["stderr"]


@pytest.mark.parametrize("model_number", [9, 12, 19, 69, 73])
def test_joint_moderation_uses_full_two_moderator_probe_grid(
    model_number: int,
    tmp_path: Path,
) -> None:
    mediator_count, _maximum = _mediator_limits(model_number)
    spec = _catalog_spec(model_number, mediator_count=mediator_count)
    spec["estimation"]["bootstrap"]["enabled"] = False
    spec["estimation"]["standardErrors"] = "classical"
    data_path = tmp_path / f"process-joint-probes-{model_number}.csv"
    _write_catalog_data(data_path, model_number, mediator_count)

    result = run_mediation(spec, data_path, get_settings())

    moderation_counts = {
        target_edge_id: sum(
            moderation["targetEdgeId"] == target_edge_id for moderation in spec["moderations"]
        )
        for target_edge_id in {moderation["targetEdgeId"] for moderation in spec["moderations"]}
    }
    multi_moderator_targets = {
        target_edge_id for target_edge_id, count in moderation_counts.items() if count > 1
    }
    assert multi_moderator_targets
    for target_edge_id in multi_moderator_targets:
        target_probes = [
            probe for probe in result["probes"] if probe["targetEdgeId"] == target_edge_id
        ]
        assert len(target_probes) == 9
        assert {probe["label"] for probe in target_probes} == {
            f"W_{w_label}__Z_{z_label}"
            for w_label in ("percentile_16", "median", "percentile_84")
            for z_label in ("percentile_16", "median", "percentile_84")
        }
        assert all("secondaryModeratorValue" in probe for probe in target_probes)


def test_model_19_matches_process_50_official_numeric_reference(tmp_path: Path) -> None:
    """Golden values were generated with the supplied official PROCESS 5.0 R macro."""
    row = np.arange(1, 241, dtype=float)
    x = np.sin(row * 0.37) + np.cos(row * 0.11)
    w = np.cos(row * 0.23) + np.sin(row * 0.07)
    z = np.sin(row * 0.19) - np.cos(row * 0.13)
    mediator = 0.4 * x + 0.18 * w - 0.12 * z + np.sin(row * 1.31) * 0.55
    outcome = (
        0.22 * x
        + 0.36 * mediator
        + 0.14 * w
        - 0.09 * z
        + 0.17 * mediator * w
        - 0.11 * mediator * z
        + 0.08 * mediator * w * z
        + np.cos(row * 1.17) * 0.6
    )
    data_path = tmp_path / "process-50-model-19-reference.csv"
    pd.DataFrame(
        {
            "var_x": x,
            "var_m1": mediator,
            "var_y": outcome,
            "var_w": w,
            "var_z": z,
        }
    ).to_csv(data_path, index=False)
    spec = _catalog_spec(19)
    spec["estimation"]["bootstrap"]["enabled"] = False
    spec["estimation"]["standardErrors"] = "classical"
    spec["estimation"]["centering"] = {
        "method": "mean",
        "nodeIds": ["x", "m1", "w", "z"],
    }

    result = run_mediation(spec, data_path, get_settings())

    equations = {
        equation["formula"].split("~", maxsplit=1)[0].strip(): {
            coefficient["term"]: coefficient["estimate"] for coefficient in equation["coefficients"]
        }
        for equation in result["equations"]
    }
    assert equations["m1"]["x"] == pytest.approx(0.373650, abs=5e-7)
    assert equations["y"]["x"] == pytest.approx(0.188133, abs=5e-7)
    assert equations["y"]["m1"] == pytest.approx(0.418751, abs=5e-7)
    assert equations["y"]["w"] == pytest.approx(0.130397, abs=5e-7)
    assert equations["y"]["z"] == pytest.approx(-0.071452, abs=5e-7)

    expected_interactions = {
        ("w", "x"): 0.029830,
        ("w", "m1"): 0.087359,
        ("z", "x"): 0.179561,
        ("z", "m1"): -0.556786,
        ("wz", "x"): 0.021341,
        ("wz", "m1"): 0.073208,
    }
    edge_by_id = {edge["id"]: edge for edge in spec["edges"]}
    for moderation in spec["moderations"]:
        edge = edge_by_id[moderation["targetEdgeId"]]
        moderator = (
            "wz" if moderation.get("secondaryModeratorNodeId") else moderation["moderatorNodeId"]
        )
        expected = expected_interactions[(moderator, edge["from"])]
        assert equations["y"][moderation["productTermId"]] == pytest.approx(expected, abs=5e-7)

    official_conditional = [
        0.385130,
        0.114438,
        -0.118343,
        0.387646,
        0.151710,
        -0.051182,
        0.390155,
        0.188877,
        0.015789,
    ]
    conditional = [
        effect["estimate"]
        for effect in result["effects"]
        if effect["type"] == "conditional" and effect["label"].startswith("specific_indirect:")
    ]
    assert conditional == pytest.approx(official_conditional, abs=7e-7)
    wz_index = next(
        effect
        for effect in result["effects"]
        if effect["type"] == "index"
        and effect["label"].endswith("polynomial index W_x_Z")
        and effect["label"].startswith("specific_indirect:")
    )
    assert wz_index["estimate"] == pytest.approx(0.027354, abs=7e-7)


@pytest.mark.parametrize(
    "model_number",
    [19, 80, pytest.param(92, marks=pytest.mark.serial)],
)
def test_generic_engine_bootstraps_complex_process_families(
    model_number: int,
    tmp_path: Path,
) -> None:
    mediator_count, _maximum = _mediator_limits(model_number)
    if model_number == 92:
        mediator_count = 6
    spec = _catalog_spec(model_number, mediator_count=mediator_count)
    spec["estimation"]["bootstrap"].update(
        enabled=True,
        replicates=1000,
        method="percentile",
        seed=20260730,
    )
    data_path = tmp_path / f"process-bootstrap-{model_number}.csv"
    _write_catalog_data(data_path, model_number, mediator_count)

    result = run_mediation(spec, data_path, get_settings())

    bootstrapped = [
        effect
        for effect in result["effects"]
        if effect["type"] in {"indirect", "conditional", "index"}
    ]
    assert bootstrapped
    for effect in bootstrapped:
        interval = effect["confidenceInterval"]
        assert interval["replicates"] == 1000
        assert math.isfinite(effect["standardError"])
        assert interval["lower"] <= interval["upper"]
