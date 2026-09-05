from __future__ import annotations

import math

import pandas as pd

from app.services.dataset_repository import DatasetRepository
from app.services.repository_io import JsonObject


def read_dataset_rows(
    repository: DatasetRepository,
    dataset_id: str,
    *,
    offset: int,
    limit: int,
    search: str | None,
    sort_column: str | None,
    sort_direction: str,
) -> JsonObject:
    dataset = repository.get_dataset(dataset_id)
    frame = pd.read_parquet(repository.get_dataset_data_path(dataset_id))
    variable_names = {
        str(variable["id"]): str(variable["originalName"])
        for variable in dataset["variables"]
    }
    if search:
        needle = search.casefold()
        mask = frame.astype("string").apply(
            lambda column: column.str.casefold().str.contains(needle, regex=False, na=False)
        ).any(axis=1)
        frame = frame.loc[mask]
    if sort_column:
        column = variable_names.get(sort_column, sort_column)
        if column not in frame.columns:
            raise ValueError("排序变量不存在")
        frame = frame.sort_values(column, ascending=sort_direction == "asc", kind="stable", na_position="last")
    total = len(frame)
    page = frame.iloc[offset : offset + limit].copy().where(lambda value: pd.notna(value), None)
    rows = [{str(key): _json_value(value) for key, value in row.items()} for row in page.to_dict(orient="records")]
    return {"offset": offset, "limit": limit, "total": total, "rows": rows}


def _json_value(value: object) -> object:
    if value is None or isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    item = getattr(value, "item", None)
    return item() if callable(item) else value
