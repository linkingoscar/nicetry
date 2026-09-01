from __future__ import annotations

import pandas as pd
from _sem_calculations_helpers import _context_refs
from test_sem_calculations import _await_analysis, _model_dataset, client

from app.semantics import validate_model_semantics
from app.services.sem_compiler import compile_sem_model


def test_higher_order_sem_compiles_latent_indicators_without_data_columns() -> None:
    model = {
        "nodes": [],
        "edges": [],
        "covariates": [],
        "latents": [
            {"id": "first_a", "name": "A", "level": "first_order", "indicators": ["a1", "a2"]},
            {"id": "first_b", "name": "B", "level": "first_order", "indicators": ["b1", "b2"]},
            {"id": "first_c", "name": "C", "level": "first_order", "indicators": ["c1", "c2"]},
            {
                "id": "higher_g",
                "name": "G",
                "level": "higher_order",
                "indicators": ["first_a", "first_b", "first_c"],
            },
        ],
        "estimation": {"family": "sem", "estimator": "ML"},
    }
    available = {
        name: {"dataType": "continuous", "column": name}
        for name in ("a1", "a2", "b1", "b2", "c1", "c2")
    }

    compiled = compile_sem_model(
        model,
        pd.DataFrame({name: [1.0, 2.0] for name in available}),
        available,
    )

    assert compiled["valid"] is True
    assert "higher_g =~ first_a + first_b + first_c" in compiled["lavaanSyntax"]
    assert set(compiled["requiredVariables"]) == set(available)


def test_higher_order_sem_rejects_measurement_cycles() -> None:
    model = {
        "nodes": [],
        "edges": [],
        "moderations": [],
        "covariates": [],
        "latents": [
            {"id": "factor_a", "name": "A", "level": "higher_order", "indicators": ["factor_b", "factor_c"]},
            {"id": "factor_b", "name": "B", "level": "higher_order", "indicators": ["factor_a", "factor_c"]},
            {"id": "factor_c", "name": "C", "level": "higher_order", "indicators": ["factor_a", "factor_b"]},
        ],
        "estimation": {"family": "sem"},
    }

    validation = validate_model_semantics(model)

    assert validation["valid"] is False
    assert "高阶潜变量测量层级中存在循环引用" in validation["errors"]


def test_partial_invariance_release_requires_matching_stage_and_measurement_parameter() -> None:
    model = {
        "nodes": [],
        "edges": [],
        "moderations": [],
        "covariates": [],
        "latents": [
            {
                "id": "factor_a",
                "name": "A",
                "level": "first_order",
                "indicators": ["item_one", "item_two", "item_three"],
            }
        ],
        "estimation": {
            "family": "sem",
            "groupVariableId": "group_node",
            "invariance": True,
            "multiGroup": {
                "compareStructuralPaths": False,
                "estimateLatentMeans": False,
                "partialInvarianceReleases": [
                    {
                        "stage": "strict",
                        "constraint": "loading",
                        "latentId": "missing_factor",
                        "indicatorId": "item_one",
                        "rationale": "测试错误约束阶段与悬空潜变量。",
                    }
                ],
            },
        },
    }

    validation = validate_model_semantics(model)

    assert validation["valid"] is False
    assert "释放参数 loading 必须位于 metric 阶段" in validation["errors"]
    assert "载荷释放必须引用有效测量关系: missing_factor=~item_one" in validation["errors"]


def test_multigroup_observed_single_predictor_emits_model_implied_lines() -> None:
    dataset, measurement = _model_dataset()
    item_ids = {variable["originalName"]: variable["id"] for variable in dataset["variables"]}
    score_y = next(
        construct["outputVariableId"]
        for construct in measurement["constructs"]
        if construct["id"] == "construct_y"
    )
    model = {
        "schemaVersion": "0.3.0",
        "modelId": "sem_prediction_plot_model",
        "name": "Observed prediction line eligibility",
        "datasetVersionId": measurement["derivedDataset"]["id"],
        "design": {
            "timeStructure": "cross_sectional",
            "clustering": "none",
            "claimMode": "associational",
        },
        "nodes": [
            {
                "id": "latent_measure",
                "label": "Measurement factor",
                "kind": "latent",
                "role": "m",
                "dataType": "continuous",
            },
            {
                "id": "observed_age",
                "variableId": item_ids["age"],
                "label": "Age",
                "kind": "observed",
                "role": "x",
                "dataType": "continuous",
            },
            {
                "id": "observed_score_y",
                "variableId": score_y,
                "label": "Y score",
                "kind": "scale_score",
                "role": "y",
                "dataType": "continuous",
            },
            {
                "id": "group",
                "variableId": item_ids["group"],
                "label": "Group",
                "kind": "observed",
                "role": "w",
                "dataType": "binary",
            },
        ],
        "edges": [
            {
                "id": "edge_age_score",
                "from": "observed_age",
                "to": "observed_score_y",
                "kind": "regression",
            }
        ],
        "moderations": [],
        "covariates": [],
        "latents": [
            {
                "id": "latent_measure",
                "name": "Measurement factor",
                "level": "first_order",
                "indicators": [item_ids["x1"], item_ids["x2"], item_ids["m1"]],
            }
        ],
        "estimation": {
            "family": "sem",
            "estimator": "ML",
            "groupVariableId": "group",
            "invariance": True,
            "multiGroup": {
                "compareStructuralPaths": True,
                "estimateLatentMeans": False,
                "partialInvarianceReleases": [],
            },
            "standardErrors": "standard",
            "confidenceLevel": 0.95,
            "bootstrap": {
                "enabled": False,
                "replicates": 1000,
                "method": "percentile",
                "seed": 12345,
            },
            "missing": "fiml",
            "centering": {"method": "none", "nodeIds": []},
            "reportScale": "unstandardized_primary",
        },
    }
    model.update(_context_refs(dataset))

    frozen = client.post(
        f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/freeze",
        json={"model_spec": model},
    )
    assert frozen.status_code == 200, frozen.text
    state = _await_analysis(
        client.post(
            f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/versions/{frozen.json()['version']}/analysis"
        )
    )

    plots = state["result"]["invarianceResult"]["predictionPlots"]
    assert len(plots) == 1
    assert plots[0]["from"] == item_ids["age"]
    assert plots[0]["to"] == score_y
    assert {line["group"] for line in plots[0]["groups"]} == {"A", "B"}
    assert all(len(line["xValues"]) == 25 for line in plots[0]["groups"])
