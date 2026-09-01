from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.empirical_options_validator import EmpiricalAnalysisError
from app.services.owned_resources import (
    resolve_derived_dataset_path,
    resolve_normalized_dataset_path,
)
from app.settings import Settings


def prepare_empirical_data(
    dataset: dict[str, Any], measurement: dict[str, Any] | None, settings: Settings
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Prepare DataFrame and variable/construct metadata for empirical analysis execution."""
    derived_path = (resolve_derived_dataset_path(settings.state_root, measurement) if measurement is not None
                    else resolve_normalized_dataset_path(settings.state_root, dataset))
    if not derived_path.exists():
        raise EmpiricalAnalysisError(f"派生数据不存在: {derived_path}")
    source = pd.read_parquet(derived_path)
    constructs = measurement["constructs"] if measurement is not None else []
    prepared = pd.DataFrame(index=source.index)
    item_ids = {
        item_id for construct in constructs for item_id in construct["itemIds"]
    }
    variables = []
    for variable in dataset["variables"]:
        variable_id = variable["id"]
        original_name = variable["originalName"]
        if original_name not in source.columns:
            continue
        confirmed_type = variable.get("confirmedType")
        if confirmed_type in {"continuous", "ordinal", "likert"}:
            prepared[variable_id] = pd.to_numeric(source[original_name], errors="coerce")
        elif confirmed_type == "binary":
            numeric = pd.to_numeric(source[original_name], errors="coerce")
            prepared[variable_id] = (
                numeric
                if int(numeric.notna().sum()) == int(source[original_name].notna().sum())
                else source[original_name].astype("string")
            )
        else:
            prepared[variable_id] = source[original_name].astype("string")
        variables.append(
            {
                "id": variable_id,
                "label": variable["label"],
                "originalName": original_name,
                "type": confirmed_type,
                "isItem": variable_id in item_ids,
            }
        )

    construct_metadata = []
    report_by_construct = {report["constructId"]: report for report in measurement["reports"]} if measurement is not None else {}
    variable_by_id = {variable["id"]: variable for variable in dataset["variables"]}
    for construct in constructs:
        output_id = construct["outputVariableId"]
        prepared[output_id] = pd.to_numeric(source[output_id], errors="coerce")
        for item_id in construct["reverseItemIds"]:
            prepared[item_id] = (
                construct["theoreticalMinimum"]
                + construct["theoreticalMaximum"]
                - pd.to_numeric(prepared[item_id], errors="coerce")
            )
        measurement_report = report_by_construct.get(construct["id"], {})
        construct_metadata.append(
            {
                "id": construct["id"],
                "label": construct["name"],
                "scoreId": output_id,
                "itemIds": construct["itemIds"],
                "items": [
                    {
                        "id": item_id,
                        "label": variable_by_id[item_id]["label"],
                        "reversed": item_id in construct["reverseItemIds"],
                    }
                    for item_id in construct["itemIds"]
                ],
                "alpha": measurement_report.get("alpha"),
                "omega": measurement_report.get("omega"),
                "theoreticalMinimum": construct["theoreticalMinimum"],
                "theoreticalMaximum": construct["theoreticalMaximum"],
                "aggregation": construct["aggregation"],
                "itemCount": len(construct["itemIds"]),
            }
        )
    return prepared, {"variables": variables, "constructs": construct_metadata}
