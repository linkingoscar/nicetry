from __future__ import annotations

import uuid
from typing import Literal

from app.contracts import validate_contract
from app.services.dataset_import import import_dataset
from app.services.dataset_repository import DatasetRepository
from app.services.measurement import build_measurement_version
from app.services.repository_io import JsonObject
from app.settings import Settings


class DemoProjectError(RuntimeError):
    pass


DemoTimeStructure = Literal["cross_sectional", "panel", "intensive_longitudinal"]


def load_demo_project(
    repository: DatasetRepository,
    settings: Settings,
    time_structure: DemoTimeStructure = "cross_sectional",
) -> JsonObject:
    if time_structure == "cross_sectional":
        return _load_questionnaire_demo_project(repository, settings)

    filename = (
        "longitudinal-panel-demo.csv"
        if time_structure == "panel"
        else "daily-diary-demo.csv"
    )
    dataset = _load_structured_dataset(repository, settings, filename)
    constructs = (
        _panel_constructs(dataset)
        if time_structure == "panel"
        else _diary_constructs(dataset)
    )
    measurement = build_measurement_version(
        dataset["id"],
        constructs,
        repository,
        "一键加载当前时间结构示例项目自动生成",
    )
    validate_contract(measurement, settings.measurement_schema_path)
    return {
        "dataset": dataset,
        "measurement": measurement,
        "modelSpec": _structured_demo_model_spec(dataset, measurement, time_structure),
    }


def _load_questionnaire_demo_project(
    repository: DatasetRepository,
    settings: Settings,
) -> JsonObject:
    demo_csv_path = settings.project_root / "samples" / "data" / "questionnaire-demo.csv"
    if not demo_csv_path.exists():
        raise DemoProjectError("演示数据文件不存在")

    with demo_csv_path.open("rb") as source:
        dataset = import_dataset(
            source=source,
            filename="questionnaire-demo.csv",
            settings=settings,
            repository=repository,
        )

    variable_types = {
        variable["id"]: (
            "id"
            if variable["originalName"] == "respondent_id"
            else "binary"
            if variable["originalName"] == "group"
            else "continuous"
            if variable["originalName"] == "age"
            else "likert"
        )
        for variable in dataset["variables"]
    }
    dataset = repository.confirm_dictionary(dataset["id"], variable_types)
    validate_contract(dataset, settings.dataset_schema_path)

    variables = {variable["originalName"]: variable["id"] for variable in dataset["variables"]}
    constructs = [
        _construct("construct_autonomy", "工作自主性", variables, "autonomy"),
        _construct("construct_engagement", "工作投入", variables, "engagement"),
        _construct("construct_purchase", "购买意向", variables, "purchase"),
    ]
    measurement = build_measurement_version(
        dataset["id"], constructs, repository, "一键加载演示项目自动生成"
    )
    validate_contract(measurement, settings.measurement_schema_path)
    return {
        "dataset": dataset,
        "measurement": measurement,
        "modelSpec": _demo_model_spec(dataset, measurement),
    }


def _load_structured_dataset(
    repository: DatasetRepository,
    settings: Settings,
    filename: str,
) -> JsonObject:
    path = settings.project_root / "samples" / "data" / filename
    if not path.exists():
        raise DemoProjectError(f"演示数据文件不存在：{filename}")

    with path.open("rb") as source:
        dataset = import_dataset(
            source=source,
            filename=filename,
            settings=settings,
            repository=repository,
        )
    variable_types = {
        variable["id"]: _structured_variable_type(variable["originalName"])
        for variable in dataset["variables"]
    }
    dataset = repository.confirm_dictionary(dataset["id"], variable_types)
    validate_contract(dataset, settings.dataset_schema_path)
    return dataset


def _structured_variable_type(original_name: str) -> str:
    if original_name in {"subject_id", "person_id"}:
        return "id"
    if original_name in {"group", "intervention", "purchase"}:
        return "binary"
    if original_name == "scenario":
        return "nominal"
    if "_i" in original_name:
        return "likert"
    return "continuous"


def _panel_constructs(dataset: JsonObject) -> list[JsonObject]:
    variables = {variable["originalName"]: variable["id"] for variable in dataset["variables"]}
    constructs: list[JsonObject] = []
    for wave in range(1, 6):
        for prefix, label in (("x", "X"), ("y", "Y")):
            names = [f"{prefix}_t{wave}_i{index}" for index in range(1, 4)]
            constructs.append(
                _construct_from_names(
                    f"construct_{prefix}_t{wave}",
                    f"{label} · T{wave}",
                    variables,
                    names,
                )
            )
    return constructs


def _diary_constructs(dataset: JsonObject) -> list[JsonObject]:
    variables = {variable["originalName"]: variable["id"] for variable in dataset["variables"]}
    return [
        _construct_from_names(
            f"construct_{prefix}",
            label,
            variables,
            [f"{prefix}_i1", f"{prefix}_i2"],
        )
        for prefix, label in (
            ("stress", "每日压力"),
            ("recovery", "每日恢复"),
            ("engagement", "每日投入"),
        )
    ]


def _structured_demo_model_spec(
    dataset: JsonObject,
    measurement: JsonObject,
    time_structure: DemoTimeStructure,
) -> JsonObject:
    return {
        "schemaVersion": "1.0.0",
        "modelId": f"model_demo_{uuid.uuid4().hex[:8]}",
        "name": "时间结构示例项目",
        "description": "与当前时间结构匹配的示例数据与测量版本。",
        "datasetVersionId": measurement["derivedDataset"]["id"],
        "design": {
            "timeStructure": time_structure,
            "clustering": "none",
            "claimMode": "associational",
        },
        "nodes": [],
        "edges": [],
        "moderations": [],
        "covariates": [],
        "estimation": {},
    }


def _construct(
    construct_id: str,
    name: str,
    variables: dict[str, str],
    prefix: str,
) -> JsonObject:
    return _construct_from_names(
        construct_id,
        name,
        variables,
        [f"{prefix}_{index}" for index in range(1, 4)],
    )


def _construct_from_names(
    construct_id: str,
    name: str,
    variables: dict[str, str],
    item_names: list[str],
) -> JsonObject:
    return {
        "id": construct_id,
        "name": name,
        "itemIds": [variables[item_name] for item_name in item_names],
        "reverseItemIds": [],
        "theoreticalMinimum": 1,
        "theoreticalMaximum": 5,
        "aggregation": "mean",
        "minimumValidProportion": 0.8,
    }


def _demo_model_spec(dataset: JsonObject, measurement: JsonObject) -> JsonObject:
    score_by_id = {
        construct["id"]: construct["outputVariableId"] for construct in measurement["constructs"]
    }
    observed = {variable["originalName"]: variable["id"] for variable in dataset["variables"]}
    return {
        "schemaVersion": "1.0.0",
        "modelId": f"model_demo_{uuid.uuid4().hex[:8]}",
        "name": "经典中介路径分析示例",
        "description": "工作自主性（X）通过工作投入（M）影响购买意向（Y）的经典中介分析模型（含控制变量）。",
        "datasetVersionId": measurement["derivedDataset"]["id"],
        "design": {
            "timeStructure": "cross_sectional",
            "clustering": "none",
            "claimMode": "associational",
        },
        "nodes": [
            _model_node(
                "node_x", score_by_id["construct_autonomy"], "工作自主性 (X)", "scale_score", "x"
            ),
            _model_node(
                "node_m", score_by_id["construct_engagement"], "工作投入 (M)", "scale_score", "m"
            ),
            _model_node(
                "node_y", score_by_id["construct_purchase"], "购买意向 (Y)", "scale_score", "y"
            ),
            _model_node("node_cov_age", observed["age"], "年龄", "observed", "covariate"),
        ],
        "edges": [
            {
                "id": "edge_x_m",
                "from": "node_x",
                "to": "node_m",
                "kind": "regression",
                "label": "a",
                "hypothesis": "H1",
            },
            {
                "id": "edge_x_y",
                "from": "node_x",
                "to": "node_y",
                "kind": "regression",
                "label": "c_prime",
            },
            {
                "id": "edge_m_y",
                "from": "node_m",
                "to": "node_y",
                "kind": "regression",
                "label": "b",
                "hypothesis": "H2",
            },
        ],
        "moderations": [],
        "covariates": [{"nodeId": "node_cov_age", "outcomeNodeIds": ["node_m", "node_y"]}],
        "estimation": {
            "family": "ols",
            "standardErrors": "classical",
            "confidenceLevel": 0.95,
            "bootstrap": {
                "enabled": True,
                "replicates": 1000,
                "method": "percentile",
                "seed": 20260714,
            },
            "missing": "complete_cases_per_model",
            "centering": {"method": "none", "nodeIds": []},
            "reportScale": "unstandardized_primary",
        },
        "canvas": {
            "positions": {
                "node_x": {"x": 80, "y": 140},
                "node_m": {"x": 350, "y": 50},
                "node_y": {"x": 620, "y": 140},
                "node_cov_age": {"x": 350, "y": 280},
            }
        },
    }


def _model_node(node_id: str, variable_id: str, label: str, kind: str, role: str) -> dict[str, str]:
    return {
        "id": node_id,
        "variableId": variable_id,
        "label": label,
        "kind": kind,
        "role": role,
        "dataType": "continuous",
    }
