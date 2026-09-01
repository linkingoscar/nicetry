from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ModelSpec = dict[str, Any]


class ContractValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def load_json(path: Path) -> ModelSpec:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


_schema_cache: dict[Path, Draft202012Validator] = {}


def validate_contract(document: ModelSpec, schema_path: Path) -> None:
    if schema_path not in _schema_cache:
        schema = load_json(schema_path)
        _schema_cache[schema_path] = Draft202012Validator(schema)
    validator = _schema_cache[schema_path]
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        rendered = []
        for error in errors:
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            rendered.append(f"{path}: {error.message}")
        raise ContractValidationError(rendered)


def _normalize_model_spec_for_hash(
    model_spec: ModelSpec, *, strip_metadata: bool = False
) -> ModelSpec:
    spec = copy.deepcopy(model_spec)
    spec.pop("canvas", None)
    if strip_metadata:
        spec.pop("name", None)
        spec.pop("description", None)
        if isinstance(spec.get("nodes"), list):
            for node in spec["nodes"]:
                if isinstance(node, dict):
                    node.pop("label", None)
        if isinstance(spec.get("edges"), list):
            for edge in spec["edges"]:
                if isinstance(edge, dict):
                    edge.pop("label", None)
                    edge.pop("hypothesis", None)

    for key in ("nodes", "edges", "moderations", "latents"):
        if isinstance(spec.get(key), list):
            if key == "latents":
                for latent in spec[key]:
                    if isinstance(latent, dict) and isinstance(latent.get("indicators"), list):
                        latent["indicators"] = sorted(latent["indicators"])
            spec[key] = sorted(
                spec[key],
                key=lambda item: str(item.get("id", "")) if isinstance(item, dict) else "",
            )

    if isinstance(spec.get("covariates"), list):
        for assignment in spec["covariates"]:
            if isinstance(assignment, dict) and isinstance(assignment.get("outcomeNodeIds"), list):
                assignment["outcomeNodeIds"] = sorted(assignment["outcomeNodeIds"])
        spec["covariates"] = sorted(
            spec["covariates"],
            key=lambda item: str(item.get("nodeId", "")) if isinstance(item, dict) else "",
        )

    centering = spec.get("estimation", {}).get("centering", {})
    if isinstance(centering, dict) and isinstance(centering.get("nodeIds"), list):
        centering["nodeIds"] = sorted(centering["nodeIds"])
    releases = (
        spec.get("estimation", {}).get("multiGroup", {}).get("partialInvarianceReleases")
    )
    if isinstance(releases, list):
        releases.sort(
            key=lambda item: (
                str(item.get("stage", "")),
                str(item.get("constraint", "")),
                str(item.get("latentId", "")),
                str(item.get("indicatorId", "")),
            )
        )
    return spec


def _sha256_canonical_spec(spec: ModelSpec) -> str:
    payload = json.dumps(
        spec,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_model_hash(model_spec: ModelSpec) -> str:
    return _sha256_canonical_spec(_normalize_model_spec_for_hash(model_spec, strip_metadata=False))


def compute_analysis_signature(model_spec: ModelSpec) -> str:
    return _sha256_canonical_spec(_normalize_model_spec_for_hash(model_spec, strip_metadata=True))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class EstimandCausalTargetError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "ESTIMAND_CAUSAL_TARGET_INVALID"


def validate_estimand_causal_target(spec: dict[str, object]) -> None:
    """Validates EstimandSpec anti-counterfeiting rules for causal claims."""
    estimand = spec.get("estimandSpec")
    if not isinstance(estimand, dict):
        return

    is_causal = estimand.get("causalTarget") is True
    if not is_causal:
        return

    assumptions = estimand.get("identificationAssumptions", [])
    design = spec.get("design", {})
    time_structure = design.get("timeStructure") if isinstance(design, dict) else None

    if time_structure == "cross_sectional" or not time_structure:
        if not assumptions or not isinstance(assumptions, list) or len(assumptions) == 0:
            raise EstimandCausalTargetError(
                "横截面观测数据设置 causalTarget=True 时，必须显式在 identificationAssumptions 中提供至少一条识别假设 (如 'unconfoundedness')"
            )
