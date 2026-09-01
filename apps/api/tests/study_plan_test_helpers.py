from __future__ import annotations

from collections.abc import Mapping


def typed_plan_payload(
    context: Mapping[str, object],
    *,
    title: str = "Typed study plan",
    research_question: str = "Does the planned contrast change the outcome?",
    hypothesis_label: str = "The planned contrast changes the outcome.",
    slice_id: str = "power_analysis.analytic.regression",
    power_spec: dict[str, object] | None = None,
    roles: list[dict[str, object]] | None = None,
    robustness: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    robustness = robustness or []
    robustness_declarations = [
        {
            "id": f"analysis_robustness_{index + 1}",
            "role": "robustness",
            "estimandIds": ["estimand_primary"],
            "capabilitySliceId": item["sliceId"],
            "requestedMethod": str(item["sliceId"]).split(".", 1)[0],
            "parameters": {"rationale": item.get("rationale", "")},
        }
        for index, item in enumerate(robustness)
    ]
    return {
        "schemaVersion": "2.0.0",
        "title": title,
        "researchQuestion": research_question,
        "hypotheses": [{
            "id": "hypothesis_primary",
            "label": hypothesis_label,
            "analysisRole": "primary",
            "declarationTiming": "preregistered",
            "direction": "two_sided",
            "estimandIds": ["estimand_primary"],
        }],
        "estimands": [{
            "id": "estimand_primary",
            "quantity": "Adjusted outcome difference",
            "outcomeScale": "original",
            "population": "analysis_sample",
            "contrast": None,
            "conditioning": None,
            "causalTarget": False,
        }],
        "analysisDeclarations": [{
            "id": "analysis_primary",
            "role": "primary",
            "estimandIds": ["estimand_primary"],
            "capabilitySliceId": slice_id,
            "requestedMethod": slice_id.split(".", 1)[0],
            "robustnessAnalysisIds": [item["id"] for item in robustness_declarations],
            "parameters": {},
        }, *robustness_declarations],
        "multiplicityFamilies": [],
        "sampleDefinition": {"roles": roles or [{"key": "outcome", "label": "结果变量", "role": "outcome"}]},
        "measurementPlan": {"constructs": []},
        "missingDataPlan": {
            "strategy": "完整案例分析并报告缺失比例",
            "sensitivityAnalysisIds": [],
            "reportMissingness": True,
        },
        "powerPlan": power_spec,
        "context": context,
    }
