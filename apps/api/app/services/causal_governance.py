from __future__ import annotations

from collections.abc import Callable

from app.capability_catalog import CapabilityDefinition


def supports_causal_target(
    declaration: dict[str, object],
    capability_definition: CapabilityDefinition | None,
) -> bool:
    """Return whether a registered capability can identify a causal estimand.

    ``causalTarget`` remains a valid planning value.  Freeze governance is
    intentionally decided by explicit capability metadata so adding a future
    causal toolkit does not require weakening this gate or treating a design
    label, indirect effect, or execution success as identification evidence.
    """
    if not declaration or capability_definition is None:
        return False
    return bool(
        capability_definition.execution_available
        and capability_definition.product_visible
        and capability_definition.supports_causal_target
    )


def validate_plan_causal_targets(
    payload: dict[str, object],
    definition_for: Callable[[str], CapabilityDefinition | None],
) -> None:
    estimands = payload.get("estimands")
    if not isinstance(estimands, list):
        return
    causal_estimand_ids = {
        str(item.get("id", "")).strip()
        for item in estimands
        if isinstance(item, dict) and item.get("causalTarget") is True
    }
    if not causal_estimand_ids:
        return

    declarations = payload.get("analysisDeclarations")
    declarations = declarations if isinstance(declarations, list) else []
    for estimand_id in sorted(causal_estimand_ids):
        supported = False
        for declaration in declarations:
            if not isinstance(declaration, dict):
                continue
            declared_estimands = declaration.get("estimandIds")
            if not isinstance(declared_estimands, list) or estimand_id not in {
                str(item).strip() for item in declared_estimands
            }:
                continue
            capability_definition = definition_for(
                str(declaration.get("capabilitySliceId", "")).strip()
            )
            if supports_causal_target(declaration, capability_definition):
                supported = True
                break
        if not supported:
            raise ValueError(
                "STUDY_PLAN_CAUSAL_TARGET_UNSUPPORTED: 当前活动能力目录未提供与该 causal estimand 对应的因果识别能力；"
                "请将 causalTarget 设为 false，或等待显式 causal-capability contract 开放。"
            )
