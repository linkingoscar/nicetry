from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.contract_model import _to_camel


class StudyContextInput(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    time_structure: Literal["cross_sectional", "panel", "intensive_longitudinal"]
    dependence_structure: Literal["independent", "nested"]
    design: Literal["observational", "randomized", "quasi_experimental"]


class StudyContextRecord(StudyContextInput):
    project_id: str
    revision: int = Field(ge=1)
    updated_at: datetime


class DatasetStructureInput(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    context: StudyContextInput
    subject_id: str | None = None
    cluster_id: str | None = None
    time_id: str | None = None
    group_id: str | None = None
    treatment_id: str | None = None
    data_layout: Literal["long", "wide"] = "long"
    wave_count: int | None = Field(default=None, ge=2, le=10)
    override_reason: str | None = None

    @model_validator(mode="after")
    def validate_required_roles(self) -> "DatasetStructureInput":
        required: list[tuple[str, str | None]] = []
        if self.context.time_structure == "intensive_longitudinal":
            required.extend([("subjectId", self.subject_id), ("timeId", self.time_id)])
        elif self.context.time_structure == "panel":
            required.append(("subjectId", self.subject_id))
            if self.data_layout == "long":
                required.append(("timeId", self.time_id))
            elif self.wave_count is None:
                raise ValueError("DATA_STRUCTURE_WAVE_COUNT_REQUIRED")
        if self.context.dependence_structure == "nested":
            required.append(("clusterId", self.cluster_id))
        if self.context.design in {"randomized", "quasi_experimental"} and not (
            self.group_id or self.treatment_id
        ):
            raise ValueError("DATA_STRUCTURE_GROUP_OR_TREATMENT_REQUIRED")
        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError("DATA_STRUCTURE_ROLES_REQUIRED: " + ", ".join(missing))
        assigned = [
            value
            for value in (self.subject_id, self.cluster_id, self.time_id, self.group_id, self.treatment_id)
            if value
        ]
        if len(assigned) != len(set(assigned)):
            raise ValueError("DATA_STRUCTURE_ROLES_MUST_BE_DISTINCT")
        return self


class DatasetStructureRecord(DatasetStructureInput):
    dataset_version_id: str
    revision: int = Field(ge=1)
    updated_at: datetime

