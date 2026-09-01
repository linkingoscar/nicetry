from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

import pandas as pd


def _safe_replace(source: Path, destination: Path) -> None:
    for attempt in range(5):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05 * (2**attempt))


def _write_parquet_atomic(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        dataframe.to_parquet(temporary, index=False, engine="pyarrow")
        _safe_replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
