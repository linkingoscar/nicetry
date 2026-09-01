from __future__ import annotations

from app.contracts import validate_contract
from app.semantics import validate_m0_mediation
from app.services.r_engine import run_mediation
from app.services.r_workers import RWorkerPool
from app.services.repository_io import JsonObject
from app.settings import Settings


class DemoDatasetNotFound(ValueError):
    pass


def run_demo_mediation(
    *,
    dataset_id: str,
    model_spec: JsonObject,
    settings: Settings,
    worker_pool: RWorkerPool,
) -> JsonObject:
    """Execute the M0 mediation demo for the pinned demo dataset only."""
    if dataset_id != "mediation-demo":
        raise DemoDatasetNotFound("M0 仅提供 mediation-demo 数据集")
    validate_contract(model_spec, settings.model_schema_path)
    validate_m0_mediation(model_spec)
    return run_mediation(
        model_spec,
        settings.demo_data_path,
        settings,
        worker_pool,
    )
