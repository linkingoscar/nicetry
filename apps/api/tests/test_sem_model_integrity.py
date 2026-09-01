from __future__ import annotations

import pandas as pd
import pytest
from _sem_calculations_helpers import _sem_spec
from test_sem_calculations import _await_analysis, _model_dataset, client

from app.semantics import validate_model_semantics
from app.services.sem_compiler import compile_sem_model


@pytest.mark.parametrize("targets,observed_y", [
    (["latent_f2"], False), (["latent_f3"], False),
    (["latent_f2", "latent_f3"], False), ([], False), (["latent_f3"], True),
])
def test_explicit_covariate_targets_survive_freeze_and_real_estimation(targets, observed_y):
    dataset, measurement = _model_dataset()
    model = _sem_spec(dataset, measurement, group_variable=None, invariance=False)
    model["covariates"][0]["outcomeNodeIds"] = targets
    if observed_y:
        score_y = measurement["constructs"][2]["outputVariableId"]
        model["nodes"][2].update(kind="scale_score", variableId=score_y)
        model["latents"] = model["latents"][:2]
    node_by_id = {node["id"]: node for node in model["nodes"]}
    expected = {node_by_id[target].get("variableId", target) for target in targets}
    age_id = node_by_id["age"]["variableId"]
    frozen = client.post(
        f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/freeze",
        json={"model_spec": model},
    )
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()["modelSpec"]["covariates"] == model["covariates"]
    state = _await_analysis(client.post(
        f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/versions/{frozen.json()['version']}/analysis"
    ))
    paths = state["result"]["semResult"]["paths"]
    assert {path["to"] for path in paths if path["from"] == age_id} == expected


def test_sem_rejects_conflicting_missing_and_duplicate_measurement_definitions():
    base = {
        "nodes": [{"id": "factor", "kind": "observed", "variableId": "age"}],
        "latents": [{"id": "factor", "indicators": ["one", "two"]}],
        "estimation": {"family": "sem"},
    }
    assert any("冲突" in error for error in validate_model_semantics(base)["errors"])
    base["nodes"] = [{"id": "missing", "kind": "latent"}]
    assert any("缺少测量定义" in error for error in validate_model_semantics(base)["errors"])
    base["nodes"] = []
    assert validate_model_semantics(base)["valid"]
    base["latents"].append(base["latents"][0])
    assert "潜变量 ID 重复" in validate_model_semantics(base)["errors"]


def test_compiler_rejects_dangling_control_target():
    compiled = compile_sem_model({
        "nodes": [{"id": "age", "variableId": "age", "kind": "observed"}],
        "covariates": [{"nodeId": "age", "outcomeNodeIds": ["deleted"]}],
    }, pd.DataFrame(), {})
    assert not compiled["valid"]
    assert "无效目标" in compiled["errors"][0]


def test_three_factor_cfa_without_structural_paths_freezes_and_executes():
    dataset, measurement = _model_dataset()
    model = _sem_spec(dataset, measurement, group_variable=None, invariance=False)
    model.update(nodes=[], edges=[], covariates=[])
    frozen = client.post(
        f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/freeze",
        json={"model_spec": model},
    )
    assert frozen.status_code == 200, frozen.text
    state = _await_analysis(client.post(
        f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/versions/{frozen.json()['version']}/analysis"
    ))
    assert len(state['result']['semResult']['loadings']) == 6
    assert state['result']['semResult']['paths'] == []


@pytest.mark.parametrize('operation', ['delete', 'reassign'])
def test_removed_measurement_definition_stays_absent_after_freeze_and_estimation(operation):
    dataset, measurement = _model_dataset()
    model = _sem_spec(dataset, measurement, group_variable=None, invariance=False)
    model['latents'] = [latent for latent in model['latents'] if latent['id'] != 'latent_f2']
    if operation == 'delete':
        model['nodes'] = [node for node in model['nodes'] if node['id'] != 'latent_f2']
        model['edges'] = [edge for edge in model['edges'] if 'latent_f2' not in (edge['from'], edge['to'])]
        model['covariates'][0]['outcomeNodeIds'] = ['latent_f3']
    else:
        model['nodes'][1].update(kind='scale_score', variableId=measurement['constructs'][1]['outputVariableId'])
    frozen = client.post(f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/freeze", json={'model_spec': model})
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()['modelSpec']['latents'] == model['latents']
    state = _await_analysis(client.post(f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/versions/{frozen.json()['version']}/analysis"))
    assert {row['latentId'] for row in state['result']['semResult']['loadings']} == {'latent_f1', 'latent_f3'}
