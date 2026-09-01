from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Literal

PROCESS_CATALOG_VERSION = "5.0"
PROCESS_REFERENCE_SOURCE = "external user-provided PROCESS for R 5.0 macro"

# These are the nine columns in the official PROCESS 5.0 ``modelmat``
# (X→M·W, X→M·Z, X→M·W·Z, M→Y·W, M→Y·Z, M→Y·W·Z,
#  X→Y·W, X→Y·Z, X→Y·W·Z).  Keep this manifest in one place so the canvas
# matcher and the R execution adapter cannot silently drift apart.

# PROCESS 5.0 exposes these numbered, preprogrammed models to users. Model 74
# is deliberately absent: version 5 rejects it as a direct model selection and
# uses an internal Model 4 + XMINT path instead.
PROCESS_MODEL_BITS: dict[int, tuple[int, ...]] = {
    1: (0, 0, 0, 0, 0, 0, 1, 0, 0),
    2: (0, 0, 0, 0, 0, 0, 1, 1, 0),
    3: (0, 0, 0, 0, 0, 0, 1, 1, 1),
    4: (0, 0, 0, 0, 0, 0, 0, 0, 0),
    5: (0, 0, 0, 0, 0, 0, 1, 0, 0),
    6: (0, 0, 0, 0, 0, 0, 0, 0, 0),
    7: (1, 0, 0, 0, 0, 0, 0, 0, 0),
    8: (1, 0, 0, 0, 0, 0, 1, 0, 0),
    9: (1, 1, 0, 0, 0, 0, 0, 0, 0),
    10: (1, 1, 0, 0, 0, 0, 1, 1, 0),
    11: (1, 1, 1, 0, 0, 0, 0, 0, 0),
    12: (1, 1, 1, 0, 0, 0, 1, 1, 1),
    13: (1, 1, 1, 0, 0, 0, 1, 0, 0),
    14: (0, 0, 0, 1, 0, 0, 0, 0, 0),
    15: (0, 0, 0, 1, 0, 0, 1, 0, 0),
    16: (0, 0, 0, 1, 1, 0, 0, 0, 0),
    17: (0, 0, 0, 1, 1, 0, 1, 1, 0),
    18: (0, 0, 0, 1, 1, 1, 0, 0, 0),
    19: (0, 0, 0, 1, 1, 1, 1, 1, 1),
    20: (0, 0, 0, 1, 1, 1, 1, 0, 0),
    21: (1, 0, 0, 0, 1, 0, 0, 0, 0),
    22: (1, 0, 0, 0, 1, 0, 1, 0, 0),
    28: (1, 0, 0, 0, 1, 0, 0, 1, 0),
    29: (1, 0, 0, 0, 1, 0, 1, 1, 0),
    58: (1, 0, 0, 1, 0, 0, 0, 0, 0),
    59: (1, 0, 0, 1, 0, 0, 1, 0, 0),
    60: (1, 1, 0, 1, 0, 0, 0, 0, 0),
    61: (1, 1, 0, 1, 0, 0, 1, 0, 0),
    62: (1, 1, 0, 1, 0, 0, 0, 1, 0),
    63: (1, 1, 0, 1, 0, 0, 1, 1, 0),
    64: (1, 0, 0, 1, 1, 0, 0, 0, 0),
    65: (1, 0, 0, 1, 1, 0, 1, 0, 0),
    66: (1, 0, 0, 1, 1, 0, 0, 1, 0),
    67: (1, 0, 0, 1, 1, 0, 1, 1, 0),
    68: (1, 1, 1, 1, 0, 0, 0, 0, 0),
    69: (1, 1, 1, 1, 0, 0, 1, 1, 1),
    70: (1, 0, 0, 1, 1, 1, 0, 0, 0),
    71: (1, 0, 0, 1, 1, 1, 1, 1, 1),
    72: (1, 1, 1, 1, 1, 1, 0, 0, 0),
    73: (1, 1, 1, 1, 1, 1, 1, 1, 1),
    75: (1, 1, 0, 1, 1, 0, 0, 0, 0),
    76: (1, 1, 0, 1, 1, 0, 1, 1, 0),
    80: (0, 0, 0, 0, 0, 0, 0, 0, 0),
    81: (0, 0, 0, 0, 0, 0, 0, 0, 0),
    82: (0, 0, 0, 0, 0, 0, 0, 0, 0),
    83: (1, 0, 0, 0, 0, 0, 0, 0, 0),
    84: (1, 0, 0, 0, 0, 0, 0, 0, 0),
    85: (1, 0, 0, 0, 0, 0, 1, 0, 0),
    86: (1, 0, 0, 0, 0, 0, 1, 0, 0),
    87: (0, 0, 0, 1, 0, 0, 0, 0, 0),
    88: (0, 0, 0, 1, 0, 0, 0, 0, 0),
    89: (0, 0, 0, 1, 0, 0, 1, 0, 0),
    90: (0, 0, 0, 1, 0, 0, 1, 0, 0),
    91: (0, 0, 0, 0, 0, 0, 0, 0, 0),
    92: (1, 0, 0, 1, 0, 0, 1, 0, 0),
}

# PROCESS 5.0 applies a second, non-model-matrix rule to models 91 and 92:
# W also moderates every inter-mediator edge in the serial graph.  This is
# encoded by the official macro's ``wcmat`` block (lines 1280–1284), not by a
# ninth model-matrix bit.  Models 83/86 and 87/90 have analogous first/last
# mediator restrictions encoded below.
PROCESS_SPECIAL_RULES: dict[str, tuple[int, ...]] = {
    "firstMediatorOnlyForW": (83, 86),
    "lastMediatorOnlyForW": (87, 90),
    "serialEdgesModeratedByW": (91, 92),
}

EXECUTABLE_PROCESS_MODELS = frozenset(PROCESS_MODEL_BITS)

MatchStatus = Literal["exact", "custom", "sem", "invalid"]
Edge = tuple[str, str]
Moderation = tuple[str, str, str]


@dataclass(frozen=True)
class ProcessCatalogMatch:
    match_status: MatchStatus
    model_number: int | None
    display_name: str
    execution_available: bool
    unsupported_reason: str | None

    def as_dict(self) -> dict[str, object]:
        template = (
            f"model_{self.model_number}"
            if self.model_number is not None
            else ("sem" if self.match_status == "sem" else None)
        )
        return {
            "catalogVersion": PROCESS_CATALOG_VERSION,
            "matchStatus": self.match_status,
            "processModelNumber": self.model_number,
            "displayName": self.display_name,
            "executionAvailable": self.execution_available,
            "unsupportedReason": self.unsupported_reason,
            "template": template,
        }


def _mediator_limits(model_number: int) -> tuple[int, int]:
    if model_number < 4:
        return (0, 0)
    if model_number in {80, 81}:
        return (3, 6)
    if model_number == 82:
        return (4, 4)
    if model_number == 6 or 83 <= model_number <= 92:
        return (2, 6)
    return (1, 10)


def _base_edges(model_number: int, mediators: tuple[str, ...]) -> set[Edge]:
    x, y = "x", "y"
    if model_number < 4:
        return {(x, y)}
    edges = {(x, mediator) for mediator in mediators}
    edges.update((mediator, y) for mediator in mediators)
    edges.add((x, y))
    if model_number == 6 or 83 <= model_number <= 92:
        edges.update(
            (mediators[source], mediators[target])
            for target in range(1, len(mediators))
            for source in range(target)
        )
    elif model_number == 80:
        final_mediator = mediators[-1]
        edges.update((mediator, final_mediator) for mediator in mediators[:-1])
    elif model_number == 81:
        first_mediator = mediators[0]
        edges.update((first_mediator, mediator) for mediator in mediators[1:])
    elif model_number == 82:
        edges.update({(mediators[0], mediators[1]), (mediators[2], mediators[3])})
    return edges


def _add_moderations(
    target: set[Moderation],
    moderator: str,
    edges: set[Edge],
) -> None:
    target.update((moderator, source, outcome) for source, outcome in edges)


def _model_moderations(model_number: int, mediators: tuple[str, ...]) -> set[Moderation]:
    bits = PROCESS_MODEL_BITS[model_number]
    x_to_m = {("x", mediator) for mediator in mediators}
    m_to_y = {(mediator, "y") for mediator in mediators}
    direct = {("x", "y")}
    moderations: set[Moderation] = set()

    if model_number in PROCESS_SPECIAL_RULES["firstMediatorOnlyForW"]:
        x_to_m_for_w = {("x", mediators[0])}
    else:
        x_to_m_for_w = x_to_m
    if model_number in PROCESS_SPECIAL_RULES["lastMediatorOnlyForW"]:
        m_to_y_for_w = {(mediators[-1], "y")}
    else:
        m_to_y_for_w = m_to_y

    groups = (
        ("w", x_to_m_for_w),
        ("z", x_to_m),
        ("wz", x_to_m),
        ("w", m_to_y_for_w),
        ("z", m_to_y),
        ("wz", m_to_y),
        ("w", direct),
        ("z", direct),
        ("wz", direct),
    )
    for enabled, (moderator, target_edges) in zip(bits, groups, strict=True):
        if enabled:
            _add_moderations(moderations, moderator, target_edges)

    if model_number in PROCESS_SPECIAL_RULES["serialEdgesModeratedByW"]:
        serial_edges = {
            (mediators[source], mediators[target])
            for target in range(1, len(mediators))
            for source in range(target)
        }
        _add_moderations(moderations, "w", serial_edges)
    return moderations


def _observed_topology(
    model_spec: dict,
) -> tuple[set[Edge], set[Moderation], list[str]]:
    nodes = model_spec.get("nodes", [])
    node_by_id = {str(node.get("id")): node for node in nodes}
    edge_by_id = {str(edge.get("id")): edge for edge in model_spec.get("edges", [])}
    role_by_id = {
        node_id: str(node.get("role"))
        for node_id, node in node_by_id.items()
    }
    mediator_ids = [
        node_id for node_id, role in role_by_id.items() if role == "m"
    ]
    edges = {
        (str(edge.get("from")), str(edge.get("to")))
        for edge in model_spec.get("edges", [])
    }
    moderations: set[Moderation] = set()
    for item in model_spec.get("moderations", []):
        target_edge = edge_by_id.get(str(item.get("targetEdgeId")))
        if target_edge is None:
            continue
        primary_role = role_by_id.get(str(item.get("moderatorNodeId")), "")
        secondary_id = item.get("secondaryModeratorNodeId")
        moderator = primary_role
        if secondary_id:
            roles = {primary_role, role_by_id.get(str(secondary_id), "")}
            moderator = "wz" if roles == {"w", "z"} else ""
        moderations.add(
            (
                moderator,
                str(target_edge.get("from")),
                str(target_edge.get("to")),
            )
        )
    return edges, moderations, mediator_ids


def _supports_execution(model_number: int, mediator_count: int) -> bool:
    minimum, maximum = _mediator_limits(model_number)
    return (
        model_number in EXECUTABLE_PROCESS_MODELS
        and minimum <= mediator_count <= maximum
    )


def match_process_model(model_spec: dict) -> ProcessCatalogMatch:
    if model_spec.get("estimation", {}).get("family") == "sem":
        return ProcessCatalogMatch("sem", None, "SEM 自定义结构", True, None)

    role_nodes: dict[str, list[dict]] = {}
    for node in model_spec.get("nodes", []):
        role_nodes.setdefault(str(node.get("role")), []).append(node)
    if len(role_nodes.get("x", [])) != 1 or len(role_nodes.get("y", [])) != 1:
        return ProcessCatalogMatch("invalid", None, "结构尚未完成", False, "需要恰好一个 X 和一个 Y")

    observed_edges, observed_moderations, mediator_ids = _observed_topology(model_spec)
    x_id = str(role_nodes["x"][0].get("id"))
    y_id = str(role_nodes["y"][0].get("id"))
    mediator_count = len(mediator_ids)

    for model_number in PROCESS_MODEL_BITS:
        minimum, maximum = _mediator_limits(model_number)
        if not minimum <= mediator_count <= maximum:
            continue
        ordered_candidates = (
            permutations(mediator_ids)
            if model_number == 6 or 80 <= model_number <= 92
            else (tuple(mediator_ids),)
        )
        for ordered_mediators in ordered_candidates:
            symbolic_mediators = tuple(f"m{index + 1}" for index in range(mediator_count))
            symbol_to_id = {
                "x": x_id,
                "y": y_id,
                **dict(zip(symbolic_mediators, ordered_mediators, strict=True)),
            }
            expected_edges = {
                (symbol_to_id[source], symbol_to_id[target])
                for source, target in _base_edges(model_number, symbolic_mediators)
            }
            if expected_edges != observed_edges:
                continue
            expected_moderations = {
                (moderator, symbol_to_id[source], symbol_to_id[target])
                for moderator, source, target in _model_moderations(
                    model_number, symbolic_mediators
                )
            }
            if expected_moderations != observed_moderations:
                continue
            executable = _supports_execution(model_number, mediator_count)
            reason = None
            if not executable:
                reason = (
                    f"已匹配 PROCESS 5.0 Model {model_number}，"
                    "当前版本尚未开放该拓扑的估计器"
                )
            return ProcessCatalogMatch(
                "exact",
                model_number,
                f"PROCESS Model {model_number}",
                executable,
                reason,
            )

    return ProcessCatalogMatch(
        "custom",
        None,
        "PROCESS-compatible 自定义模型",
        False,
        "结构有效，但未匹配 PROCESS 5.0 预编程编号；当前版本暂不执行自定义矩阵模型",
    )
