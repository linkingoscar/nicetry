from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from app.capability_catalog import ACTIVE_CAPABILITIES

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = ROOT / "apps" / "web" / "src" / "methods" / "methodRegistry.json"


class MethodRegistryEntry(TypedDict):
    id: str
    label: str
    description: str
    aliases: list[str]
    keywords: list[str]
    visibilityTier: str
    adapter: str
    resultKind: str
    capabilitySliceIds: list[str]
    consumerCapabilitySliceIds: list[str]


class MethodRegistryDocument(TypedDict):
    methods: list[MethodRegistryEntry]


def _registry() -> MethodRegistryDocument:
    document: MethodRegistryDocument = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return document


def test_method_registry_covers_every_product_visible_capability() -> None:
    methods = _registry()["methods"]

    active_slice_ids = {definition.slice_id for definition in ACTIVE_CAPABILITIES}
    visible_slice_ids = {
        definition.slice_id for definition in ACTIVE_CAPABILITIES if definition.product_visible
    }
    internal_slice_ids = {
        definition.slice_id for definition in ACTIVE_CAPABILITIES if not definition.product_visible
    }

    method_ids = [method["id"] for method in methods]
    assert len(method_ids) == len(set(method_ids)), "MethodDefinition ids must be unique"

    mapped_visible: set[str] = set()
    mapped_consumers: set[str] = set()
    for method in methods:
        capability_ids = set(method["capabilitySliceIds"])
        consumer_ids = set(method["consumerCapabilitySliceIds"])
        assert capability_ids, f"{method['id']} must map at least one active capability"
        ghost = sorted((capability_ids | consumer_ids) - active_slice_ids)
        assert ghost == [], f"{method['id']} points at unknown capability slices: {ghost}"
        mapped_visible.update(capability_ids)
        mapped_consumers.update(consumer_ids)

    missing_visible = sorted(visible_slice_ids - mapped_visible)
    missing_internal_consumers = sorted(internal_slice_ids - mapped_consumers)
    assert missing_visible == []
    assert missing_internal_consumers == []


def test_visible_methods_resolve_a_current_execution_adapter_and_result_renderer() -> None:
    methods = _registry()["methods"]
    allowed_adapters = {
        "empirical-overview",
        "empirical-measurement",
        "empirical-groups",
        "empirical-regression",
        "empirical-advanced",
        "empirical-longitudinal",
        "empirical-diary",
        "model",
        "advanced-wizard",
    }
    allowed_result_kinds = {"empirical", "model", "advanced"}

    for method in methods:
        if method["visibilityTier"] == "internal":
            continue
        assert method["adapter"] in allowed_adapters
        assert method["resultKind"] in allowed_result_kinds
        assert method["label"].strip()
        assert method["description"].strip()
        assert isinstance(method["aliases"], list)
        assert isinstance(method["keywords"], list)


def test_internal_mice_slice_is_consumed_by_the_visible_multiple_imputation_method() -> None:
    methods = _registry()["methods"]
    mi_method = next(method for method in methods if method["id"] == "missing.multiple-imputation")
    assert "multiple_imputation.rubin_pooling" in mi_method["capabilitySliceIds"]
    assert "multiple_imputation.mice_dataset_generation" in mi_method["consumerCapabilitySliceIds"]
