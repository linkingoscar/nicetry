from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from jsonschema import Draft202012Validator

from app.services.capability_applicability import applicable_capability_registry
from app.services.dataset_repository import DatasetRepository
from app.services.study_plans import StudyPlanService


class _Repository(DatasetRepository):
    def __init__(self, plan: dict[str, object], dataset: dict[str, object]) -> None:
        self.plan = plan
        self.dataset = dataset

    def get_study_plan(self, plan_id: str) -> dict[str, object] | None:
        return self.plan if self.plan["id"] == plan_id else None

    def get_dataset(self, dataset_id: str) -> dict[str, object]:
        assert dataset_id == self.dataset["id"]
        return self.dataset


def _frozen_plan() -> dict[str, object]:
    return {
        "id": "study_plan_" + "a" * 32,
        "projectId": "project_graph",
        "revision": 1,
        "status": "frozen",
        "planHash": "b" * 64,
        "schemaVersion": "2.0.0",
        "title": "Evidence graph plan",
        "researchQuestion": "Does the declared effect replicate in this sample?",
        "hypotheses": [{
            "id": "H1",
            "label": "The declared effect is present.",
            "analysisRole": "primary",
            "declarationTiming": "preregistered",
            "direction": "two_sided",
            "estimandIds": ["e1"],
        }],
        "estimands": [{
            "id": "e1",
            "quantity": "regression_coefficient",
            "outcomeScale": "original",
            "population": "analysis_sample",
            "contrast": None,
            "conditioning": None,
            "causalTarget": False,
        }],
        "analysisDeclarations": [{
            "id": "analysis_primary",
            "role": "primary",
            "estimandIds": ["e1"],
            "capabilitySliceId": "empirical.cross_sectional.overview",
            "requestedMethod": "ordinary_ols",
            "robustnessAnalysisIds": [],
            "parameters": {"confidenceLevel": 0.90},
        }],
        "multiplicityFamilies": [],
        "sampleDefinition": {"roles": []},
        "measurementPlan": {"constructs": []},
        "missingDataPlan": {
            "strategy": "complete cases",
            "sensitivityAnalysisIds": [],
            "reportMissingness": True,
        },
        "powerPlan": None,
        "context": {
            "schemaVersion": "1.0.0",
            "timeStructure": "cross_sectional",
            "dependenceStructure": "independent",
            "design": "observational",
        },
        "createdAt": "2026-08-13T00:00:00+00:00",
    }


def test_deviated_execution_is_explicit_and_not_publication_eligible() -> None:
    plan = _frozen_plan()
    repository = _Repository(
        plan,
        {"id": "dataset_graph", "projectId": "project_graph", "originalFile": {"sha256": "c" * 64}},
    )
    plans = StudyPlanService(repository, applicable_capability_registry)
    identity: dict[str, object] = {
        "datasetSha256": "c" * 64,
        "sampleVersionId": "sample_all_graph",
        "sampleHash": "d" * 64,
        "measurementVersionId": "measurement_graph",
        "measurementHash": "e" * 64,
    }
    binding = plans.bind_for_execution(
        "dataset_graph",
        {
            "studyPlanVersionId": plan["id"],
            "studyPlanHash": plan["planHash"],
            "hypothesisId": "H1",
            "estimandId": "e1",
            "analysisDeclarationId": "analysis_primary",
        },
        execution_spec={"confidenceLevel": 0.95},
        identity=identity,
        spec_hash="f" * 64,
    )
    assert binding["declarationStatus"] == "deviated"
    assert "confidenceLevel" in str(binding["deviationReason"])
    assert binding["publicationEligible"] is False

    result: dict[str, object] = {
        "publicationEligible": True,
        "provenance": {},
        "evidenceGraph": {"modelVersionId": "modelversion_graph", "edges": [], "effectBindings": []},
    }
    plans.binding.attach_result_binding(result, binding)
    assert result["publicationEligible"] is False
    graph = cast(dict[str, object], result["evidenceGraph"])
    schema_path = Path(__file__).parents[3] / "specs" / "result-bundle.schema.json"
    schema = json.loads(schema_path.resolve().read_text(encoding="utf-8"))
    graph_schema = {"$defs": schema["$defs"], **schema["properties"]["evidenceGraph"]}
    Draft202012Validator(graph_schema).validate(graph)
    assert graph["schemaVersion"] == "2.0.0"
    result_binding = cast(dict[str, object], graph["resultBinding"])
    assert result_binding["declarationStatus"] == "deviated"
