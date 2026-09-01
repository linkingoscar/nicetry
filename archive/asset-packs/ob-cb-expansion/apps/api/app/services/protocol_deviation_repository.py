from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Literal, cast

from app.protocol_contracts import ProtocolDeviation, StudyProtocolSpec
from app.services.repository_io import _utc_now, safe_identifier
from app.settings import Settings


class ProtocolDeviationRepositoryMixin:
    settings: Settings

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def verify_protocol_deviation(
        self,
        program_id: str,
        study_id: str,
        version_id: str,
        analysis_spec: dict[str, object],
        analysis_id: str | None = None,
        reason: str | None = None,
    ) -> list[ProtocolDeviation]:
        protocol: StudyProtocolSpec = self.get_protocol_version(program_id, study_id, version_id)
        actual_outcome = analysis_spec.get("outcomeVariableId") or analysis_spec.get(
            "outcome_variable_id"
        )
        actual_predictors = (
            analysis_spec.get("predictorVariableIds")
            or analysis_spec.get("predictor_variable_ids")
            or []
        )
        actual_covariates = (
            analysis_spec.get("controlVariableIds")
            or analysis_spec.get("control_variable_ids")
            or analysis_spec.get("covariateVariableIds")
            or analysis_spec.get("covariate_variable_ids")
            or []
        )
        if not isinstance(actual_predictors, list):
            actual_predictors = []
        if not isinstance(actual_covariates, list):
            actual_covariates = []

        def actual_value(*keys: str) -> object:
            for key in keys:
                if key in analysis_spec:
                    return analysis_spec[key]
            return None

        def actual_has(*keys: str) -> bool:
            return any(key in analysis_spec for key in keys)

        actual_estimand_id = actual_value("estimandId", "estimand_id")
        actual_hypothesis_id = actual_value("hypothesisId", "hypothesis_id")
        actual_method = actual_value("analysisMethod", "analysis_method", "method")
        actual_comparison = actual_value("comparison")
        actual_effect_measure = actual_value("effectMeasure", "effect_measure")
        actual_analysis_unit = actual_value("analysisUnit", "analysis_unit")
        actual_timepoint = actual_value("timepoint")
        actual_stopping_rule = actual_value("stoppingRule", "stopping_rule")
        actual_exclusion_rules = actual_value("exclusionRuleIds", "exclusion_rule_ids") or []
        actual_contrasts = actual_value("contrastIds", "contrast_ids") or []
        if not isinstance(actual_exclusion_rules, list):
            actual_exclusion_rules = []
        if not isinstance(actual_contrasts, list):
            actual_contrasts = []

        plans = protocol.planned_estimands
        candidate = next(
            (plan for plan in plans if plan.estimand_id == actual_estimand_id),
            next(
                (plan for plan in plans if plan.outcome_variable_id == actual_outcome),
                plans[0] if plans else None,
            ),
        )
        deviations: list[ProtocolDeviation] = []
        if candidate is None:
            deviations.append(
                ProtocolDeviation(
                    deviation_type="estimand_mismatch",
                    field_path="planned_estimands",
                    expected_value=[],
                    actual_value=analysis_spec,
                    message="协议没有可对照的 planned estimand",
                )
            )
        else:
            comparisons: list[tuple[str, object, object, str, str]] = [
                (
                    "estimand_id",
                    candidate.estimand_id,
                    actual_estimand_id,
                    "estimand_mismatch",
                    "estimand",
                ),
                (
                    "hypothesis_id",
                    candidate.hypothesis_id,
                    actual_hypothesis_id,
                    "estimand_mismatch",
                    "假设",
                ),
                (
                    "outcome_variable_id",
                    candidate.outcome_variable_id,
                    actual_outcome,
                    "outcome_mismatch",
                    "因变量",
                ),
                (
                    "predictor_variable_ids",
                    sorted(candidate.predictor_variable_ids),
                    sorted(str(value) for value in actual_predictors),
                    "predictor_mismatch",
                    "自变量",
                ),
                (
                    "covariate_variable_ids",
                    sorted(candidate.covariate_variable_ids),
                    sorted(str(value) for value in actual_covariates),
                    "covariate_mismatch",
                    "控制变量",
                ),
                (
                    "analysis_method",
                    candidate.analysis_method,
                    actual_method,
                    "method_mismatch",
                    "分析方法",
                ),
                (
                    "comparison",
                    candidate.comparison,
                    actual_comparison,
                    "estimand_mismatch",
                    "比较",
                ),
                (
                    "effect_measure",
                    candidate.effect_measure,
                    actual_effect_measure,
                    "estimand_mismatch",
                    "效应量",
                ),
                (
                    "analysis_unit",
                    candidate.analysis_unit,
                    actual_analysis_unit,
                    "estimand_mismatch",
                    "分析单位",
                ),
                ("timepoint", candidate.timepoint, actual_timepoint, "estimand_mismatch", "时间点"),
                (
                    "exclusion_rule_ids",
                    sorted(candidate.exclusion_rule_ids),
                    sorted(str(value) for value in actual_exclusion_rules),
                    "sample_rule_mismatch",
                    "排除规则",
                ),
                (
                    "contrast_ids",
                    sorted(candidate.contrast_ids),
                    sorted(str(value) for value in actual_contrasts),
                    "estimand_mismatch",
                    "计划对比",
                ),
                (
                    "stopping_rule",
                    protocol.stopping_rule,
                    actual_stopping_rule,
                    "estimand_mismatch",
                    "停止规则",
                ),
            ]
            optional_actual_fields = {
                "estimand_id": actual_has("estimandId", "estimand_id"),
                "hypothesis_id": actual_has("hypothesisId", "hypothesis_id"),
                "comparison": actual_has("comparison"),
                "effect_measure": actual_has("effectMeasure", "effect_measure"),
                "analysis_unit": actual_has("analysisUnit", "analysis_unit"),
                "timepoint": actual_has("timepoint"),
                "stopping_rule": actual_has("stoppingRule", "stopping_rule"),
            }
            comparisons = [
                comparison
                for comparison in comparisons
                if optional_actual_fields.get(comparison[0], True)
            ]
            for field_path, expected, actual, deviation_type, label in comparisons:
                if expected is None and actual is None:
                    continue
                if expected == actual:
                    continue
                deviations.append(
                    ProtocolDeviation(
                        deviation_type=deviation_type,
                        field_path=field_path,
                        expected_value=expected,
                        actual_value=actual,
                        message=f"分析{label}与冻结协议中的计划不一致",
                    )
                )

        resolved_analysis_id = str(
            analysis_id
            or analysis_spec.get("analysisId")
            or analysis_spec.get("analysis_id")
            or f"audit_{uuid.uuid4().hex[:16]}"
        )
        created_at = _utc_now()
        persisted: list[ProtocolDeviation] = []
        with self._connect() as connection:
            for deviation in deviations:
                deviation_id = f"deviation_{uuid.uuid4().hex[:16]}"
                enriched = deviation.model_copy(
                    update={
                        "deviation_id": deviation_id,
                        "analysis_id": resolved_analysis_id,
                        "reason": reason,
                        "created_at": created_at,
                    }
                )
                connection.execute(
                    """
                    INSERT INTO study_deviations (
                        id, study_id, version_id, analysis_id, deviation_type,
                        field_path, expected_value, actual_value, reason,
                        created_at, program_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        deviation_id,
                        study_id,
                        version_id,
                        resolved_analysis_id,
                        enriched.deviation_type,
                        enriched.field_path,
                        json.dumps(enriched.expected_value, ensure_ascii=False),
                        json.dumps(enriched.actual_value, ensure_ascii=False),
                        reason,
                        created_at,
                        program_id,
                    ),
                )
                persisted.append(enriched)
        return persisted

    def list_protocol_deviations(
        self, program_id: str, study_id: str, version_id: str
    ) -> list[ProtocolDeviation]:
        program_id = safe_identifier(program_id, label="program id")
        study_id = safe_identifier(study_id, label="study id")
        version_id = safe_identifier(version_id, label="version id")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, analysis_id, deviation_type, field_path,
                       expected_value, actual_value, reason, created_at
                FROM study_deviations
                WHERE program_id = ? AND study_id = ? AND version_id = ?
                ORDER BY created_at, id
                """,
                (program_id, study_id, version_id),
            ).fetchall()
        return [
            ProtocolDeviation(
                deviation_type=cast(
                    Literal[
                        "outcome_mismatch",
                        "predictor_mismatch",
                        "covariate_mismatch",
                        "method_mismatch",
                        "sample_rule_mismatch",
                        "estimand_mismatch",
                    ],
                    row["deviation_type"],
                ),
                field_path=row["field_path"],
                expected_value=json.loads(row["expected_value"] or "null"),
                actual_value=json.loads(row["actual_value"] or "null"),
                message="已记录的协议偏离",
                deviation_id=row["id"],
                analysis_id=row["analysis_id"],
                reason=row["reason"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
