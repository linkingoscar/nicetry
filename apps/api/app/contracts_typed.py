from __future__ import annotations

from typing import TypedDict


class EmpiricalVariableMetadata(TypedDict, total=False):
    id: str
    label: str
    originalName: str
    type: str | None
    isItem: bool


class EmpiricalConstructMetadata(TypedDict, total=False):
    id: str
    label: str
    scoreId: str
    itemIds: list[str]
    items: list[dict[str, object]]
    alpha: float | None
    omega: float | None
    theoreticalMinimum: float
    theoreticalMaximum: float
    aggregation: str
    itemCount: int


class EmpiricalDatasetMetadata(TypedDict):
    variables: list[EmpiricalVariableMetadata]
    constructs: list[EmpiricalConstructMetadata]
