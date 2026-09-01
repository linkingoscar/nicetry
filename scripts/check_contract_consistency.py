#!/usr/bin/env python3
"""Cross-layer contract consistency gate for JSON Schema, Pydantic and OpenAPI.

Coverage strategy: representative, data-driven checks for the schemas and
models where drift has already happened (advanced-analysis-spec power fields,
dataset/measurement/result response models) plus full required/enum parity
where the schema shape is a single object. OpenAPI parity is checked from the
same Pydantic models, which transitively pins the generated TypeScript.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import typing
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_models() -> dict[str, type]:
    sys.path.insert(0, str(API_ROOT))
    import app.advanced_contracts as advanced
    import app.api.responses as responses

    return {
        "PowerAnalysisSpec": advanced.PowerAnalysisSpec,
        "QuestionnaireMeasurementSpec": advanced.QuestionnaireMeasurementSpec,
        "MultipleImputationSpec": advanced.MultipleImputationSpec,
        "LongitudinalModelSpec": advanced.LongitudinalModelSpec,
        "ExperimentalDesignSpec": advanced.ExperimentalDesignSpec,
        "MultilevelModelSpec": advanced.MultilevelModelSpec,
        "DatasetVersionResponse": responses.DatasetVersionResponse,
        "MeasurementVersionResponse": responses.MeasurementVersionResponse,
        "ResultBundleResponse": responses.ResultBundleResponse,
    }


def literal_values(annotation: Any) -> set[str] | None:
    args = typing.get_args(annotation)
    if args and all(isinstance(arg, str) for arg in args):
        return set(args)
    return None


def pydantic_field_summary(model: type) -> tuple[set[str], dict[str, Any]]:
    required: set[str] = set()
    properties: dict[str, Any] = {}
    for name, field in model.model_fields.items():
        alias = field.alias or name
        if field.is_required():
            required.add(alias)
        summary: dict[str, Any] = {}
        values = literal_values(field.annotation)
        if values is not None:
            summary["enum"] = sorted(values)
        for metadata in field.metadata:
            pattern = getattr(metadata, "pattern", None)
            if pattern:
                summary["pattern"] = pattern
        properties[alias] = summary
    return required, properties


def resolve_schema_node(document: dict[str, Any], node: Any) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            assert ref.startswith("#/"), ref
            current: Any = document
            for part in ref[2:].split("/"):
                current = current[part]
            return resolve_schema_node(document, current)
        if "allOf" in node:
            merged = dict(node)
            del merged["allOf"]
            properties: dict[str, Any] = {}
            required: list[str] = list(merged.get("required", []))
            for part in node["allOf"]:
                resolved = resolve_schema_node(document, part)
                properties.update(resolved.get("properties", {}))
                required.extend(resolved.get("required", []))
            merged["properties"] = properties
            merged["required"] = sorted(set(required))
            return merged
    return node


def schema_object_summary(
    document: dict[str, Any], node: Any
) -> tuple[set[str], dict[str, Any]]:
    resolved = resolve_schema_node(document, node)
    required = set(resolved.get("required", []))
    properties: dict[str, Any] = {}
    for key, value in (resolved.get("properties") or {}).items():
        resolved_value = resolve_schema_node(document, value)
        summary: dict[str, Any] = {}
        if "enum" in resolved_value:
            summary["enum"] = list(resolved_value["enum"])
        if "const" in resolved_value:
            summary["const"] = resolved_value["const"]
        if "pattern" in resolved_value:
            summary["pattern"] = resolved_value["pattern"]
        properties[key] = summary
    return required, properties


def compare_object(
    document: dict[str, Any],
    schema_node: Any,
    model: type,
    *,
    check_properties: set[str] | None = None,
    check_patterns: set[str] | None = None,
    check_required: bool = True,
) -> list[str]:
    errors: list[str] = []
    model_name = model.__name__
    schema_required, schema_properties = schema_object_summary(document, schema_node)
    model_required, model_properties = pydantic_field_summary(model)

    if check_required:
        missing_in_schema = model_required - schema_required
        missing_in_model = schema_required - model_required
        if missing_in_schema:
            errors.append(
                f"{model_name} required-by-Pydantic but not in schema: {sorted(missing_in_schema)}"
            )
        if missing_in_model:
            errors.append(
                f"{model_name} required-by-schema but optional in Pydantic: {sorted(missing_in_model)}"
            )

    keys = check_properties if check_properties is not None else (
        set(schema_properties) & set(model_properties)
    )
    for key in sorted(keys):
        schema_summary = schema_properties.get(key, {})
        model_summary = model_properties.get(key, {})
        if "enum" in schema_summary and "enum" in model_summary:
            if sorted(schema_summary["enum"]) != sorted(model_summary["enum"]):
                errors.append(
                    f"{model_name}.{key} enum drift: schema={sorted(schema_summary['enum'])} "
                    f"pydantic={sorted(model_summary['enum'])}"
                )
        if "const" in schema_summary:
            model_enum = model_summary.get("enum") or []
            if model_enum and model_enum != [schema_summary["const"]]:
                errors.append(
                    f"{model_name}.{key} const drift: schema={schema_summary['const']!r} "
                    f"pydantic={model_enum}"
                )
        if check_patterns and key in check_patterns:
            if schema_summary.get("pattern") != model_summary.get("pattern"):
                errors.append(
                    f"{model_name}.{key} pattern drift: schema={schema_summary.get('pattern')!r} "
                    f"pydantic={model_summary.get('pattern')!r}"
                )
        if key in schema_properties and key not in model_properties:
            errors.append(f"{model_name}.{key} exists in schema but not in Pydantic")
        if key in model_properties and key not in schema_properties:
            errors.append(f"{model_name}.{key} exists in Pydantic but not in schema")
    return errors


def check_contract_model_singleton() -> list[str]:
    errors: list[str] = []
    sources = "\n".join(
        path.read_text(encoding="utf-8") for path in (API_ROOT / "app").rglob("*.py")
    )
    if sources.count("class ContractModel(") != 1:
        errors.append("expected exactly one `class ContractModel(` definition in apps/api/app")
    if sources.count("def _to_camel(") != 1:
        errors.append("expected exactly one `def _to_camel(` definition in apps/api/app")
    return errors


def check_openapi_parity(models: dict[str, type]) -> list[str]:
    errors: list[str] = []
    openapi = load_json(ROOT / "specs" / "openapi.json")
    schemas = openapi.get("components", {}).get("schemas", {})
    for name, model in models.items():
        if name not in ("DatasetVersionResponse", "MeasurementVersionResponse", "ResultBundleResponse"):
            continue
        openapi_schema = schemas.get(name)
        if openapi_schema is None:
            errors.append(f"OpenAPI is missing {name}")
            continue
        openapi_required = set(openapi_schema.get("required", []))
        model_required, _ = pydantic_field_summary(model)
        if model_required - openapi_required:
            errors.append(
                f"OpenAPI {name} missing required fields: {sorted(model_required - openapi_required)}"
            )
    return errors


def check_schema_entry_wiring() -> list[str]:
    errors: list[str] = []
    source = (API_ROOT / "app" / "api" / "routes" / "advanced.py").read_text(encoding="utf-8")
    if "advanced_spec_schema_path" not in source:
        errors.append("advanced.py does not use settings.advanced_spec_schema_path")
    if "validate_contract(" not in source:
        errors.append("advanced.py does not call validate_contract at the request entry")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    models = load_models()
    errors: list[str] = []
    errors.extend(check_contract_model_singleton())
    errors.extend(check_schema_entry_wiring())

    advanced = load_json(ROOT / "specs" / "advanced-analysis-spec.schema.json")
    definitions = advanced["$defs"]
    power_model = models["PowerAnalysisSpec"]
    errors.extend(
        compare_object(
            advanced,
            definitions["powerAnalysis"],
            power_model,
            check_properties={
                "solveFor",
                "targetCIWidth",
                "sd",
                "sampleSize",
                "effectSize",
                "effectSizeMetric",
            },
            check_required=True,
        )
    )
    questionnaire_model = models["QuestionnaireMeasurementSpec"]
    errors.extend(
        compare_object(
            advanced,
            definitions["questionnaireMeasurement"],
            questionnaire_model,
            check_required=True,
        )
    )
    for model in (
        models["MultipleImputationSpec"],
        models["LongitudinalModelSpec"],
        models["ExperimentalDesignSpec"],
        models["MultilevelModelSpec"],
    ):
        errors.extend(
            compare_object(
                advanced,
                {"$ref": "#/$defs/common"},
                model,
                check_properties=set(),
                check_required=False,
            )
        )

    dataset_schema = load_json(ROOT / "specs" / "dataset-version.schema.json")
    measurement_schema = load_json(ROOT / "specs" / "measurement-version.schema.json")
    result_schema = load_json(ROOT / "specs" / "result-bundle.schema.json")
    errors.extend(
        compare_object(
            dataset_schema,
            dataset_schema,
            models["DatasetVersionResponse"],
            check_patterns={"id", "projectId", "schemaVersion"},
        )
    )
    errors.extend(
        compare_object(
            measurement_schema,
            measurement_schema,
            models["MeasurementVersionResponse"],
            check_patterns={"id", "datasetVersionId"},
        )
    )
    errors.extend(
        compare_object(
            result_schema,
            result_schema,
            models["ResultBundleResponse"],
            check_properties={
                "schemaVersion",
                "run",
                "jobStatus",
                "estimationStatus",
                "inferenceStatus",
                "publicationEligibility",
                "sampleFlow",
                "effects",
                "warnings",
                "provenance",
            },
        )
    )
    errors.extend(check_openapi_parity(models))

    if errors:
        for error in errors:
            print(error)
        return 1
    if args.verbose:
        print("JSON Schema <-> Pydantic <-> OpenAPI representative parity passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
