from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": "warning", "message": message}


def _model_variables(
    dataset: dict[str, Any], measurement: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    cache_key = (
        dataset.get("id", ""),
        dataset.get("dictionary", {}).get("version", 0),
        measurement.get("id", ""),
        measurement.get("version", 0),
    )
    from app.services.dataset_repository import DatasetRepository

    if cache_key in DatasetRepository._model_variables_cache:
        return DatasetRepository._model_variables_cache[cache_key]

    variable_map: dict[str, dict[str, Any]] = {}
    type_map = {
        "continuous": "continuous",
        "binary": "binary",
        "nominal": "nominal",
        "ordinal": "ordinal",
        "likert": "ordinal",
    }
    for variable in dataset["variables"]:
        confirmed_type = variable.get("confirmedType")
        if confirmed_type in type_map:
            variable_map[variable["id"]] = {
                "id": variable["id"],
                "label": variable["label"],
                "kind": "observed",
                "dataType": type_map[confirmed_type],
                "column": variable["originalName"],
            }
    for variable in measurement["derivedDataset"]["scoreVariables"]:
        variable_map[variable["id"]] = {
            "id": variable["id"],
            "label": variable["label"],
            "kind": "scale_score",
            "dataType": "continuous",
            "column": variable["id"],
        }
    DatasetRepository._model_variables_cache[cache_key] = variable_map
    return variable_map
