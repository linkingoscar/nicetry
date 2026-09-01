from __future__ import annotations

from typing import cast

from app.advanced_contracts import PowerAnalysisSpec
from app.services.capability_applicability import CapabilityApplicabilityRegistry
from app.services.causal_governance import validate_plan_causal_targets
from app.services.dataset_repository import DatasetRepository
from app.services.study_plan_binding import StudyPlanBindingService
from app.services.study_plan_migration import migrate_v1
from app.study_context_contracts import StudyContextInput
from app.study_plan_contracts import StudyPlanPayload


class StudyPlanService:
    """Validate typed StudyPlan v2 intent and its data boundary."""

    _PAYLOAD_KEYS = {
        "schemaVersion",
        "title",
        "researchQuestion",
        "hypotheses",
        "estimands",
        "analysisDeclarations",
        "multiplicityFamilies",
        "sampleDefinition",
        "measurementPlan",
        "missingDataPlan",
        "powerPlan",
        "context",
        "migration",
    }

    def __init__(self, repository: DatasetRepository, registry: CapabilityApplicabilityRegistry) -> None:
        self.repository = repository
        self.registry = registry
        self.binding = StudyPlanBindingService(repository)
    @staticmethod
    def _context_payload(payload: dict[str, object]) -> dict[str, object]:
        context = payload.get("context")
        if not isinstance(context, dict):
            context = {
                "schemaVersion": "1.0.0",
                "timeStructure": payload.get("timeStructure", "cross_sectional"),
                "dependenceStructure": payload.get("dependenceStructure", "independent"),
                "design": payload.get("design", "observational"),
            }
        try:
            return cast(
                dict[str, object],
                StudyContextInput.model_validate(context).model_dump(by_alias=True),
            )
        except ValueError as error:
            raise ValueError(f"STUDY_PLAN_CONTEXT_INVALID: {error}") from error

    @staticmethod
    def _role_key(role: dict[str, object]) -> str:
        value = role.get("key") or role.get("id") or role.get("role")
        return str(value).strip() if value is not None else ""

    @staticmethod
    def _string_list(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @classmethod
    def _migrate_v1(cls, payload: dict[str, object]) -> dict[str, object]:
        return migrate_v1(payload, cls._context_payload, cls._role_key, cls._string_list)

    @classmethod
    def _normalize_payload(cls, payload: dict[str, object]) -> dict[str, object]:
        if payload.get("schemaVersion") != "2.0.0":
            payload = cls._migrate_v1(payload)
        else:
            payload = {key: value for key, value in payload.items() if key in cls._PAYLOAD_KEYS}
            payload["context"] = cls._context_payload(payload)
        try:
            return cast(
                dict[str, object],
                StudyPlanPayload.model_validate(payload).model_dump(by_alias=True),
            )
        except ValueError as error:
            raise ValueError(f"STUDY_PLAN_SCHEMA_INVALID: {error}") from error

    @classmethod
    def _validate_payload(
        cls,
        payload: dict[str, object],
        *,
        require_hypothesis: bool = False,
    ) -> None:
        try:
            parsed = StudyPlanPayload.model_validate(payload)
        except ValueError as error:
            raise ValueError(f"STUDY_PLAN_SCHEMA_INVALID: {error}") from error
        for value, label, minimum in (
            (parsed.title, "计划标题", 3),
            (parsed.research_question, "研究问题", 10),
            (parsed.missing_data_plan.strategy, "缺失数据策略", 2),
        ):
            if len(value.strip()) < minimum:
                raise ValueError(f"STUDY_PLAN_FIELD_REQUIRED: {label}至少需要 {minimum} 个字符")
        if not parsed.estimands:
            raise ValueError("STUDY_PLAN_ESTIMAND_REQUIRED: 至少声明一个 estimand")
        if not parsed.analysis_declarations:
            raise ValueError("STUDY_PLAN_ANALYSIS_DECLARATION_REQUIRED: 至少声明一个分析")
        if require_hypothesis and not parsed.hypotheses:
            raise ValueError("STUDY_PLAN_HYPOTHESIS_REQUIRED: 冻结计划至少需要一个 hypothesis")

        def unique_ids(items: list[object], label: str) -> set[str]:
            ids: list[str] = []
            for item in items:
                item_id = str(getattr(item, "id", "")).strip()
                if not item_id:
                    raise ValueError(f"STUDY_PLAN_ID_REQUIRED: {label}必须有 id")
                ids.append(item_id)
            if len(ids) != len(set(ids)):
                raise ValueError(f"STUDY_PLAN_ID_DUPLICATE: {label} id 不得重复")
            return set(ids)

        hypothesis_ids = unique_ids(list(parsed.hypotheses), "hypothesis")
        estimand_ids = unique_ids(list(parsed.estimands), "estimand")
        analysis_ids = unique_ids(list(parsed.analysis_declarations), "analysis declaration")
        unique_ids(list(parsed.multiplicity_families), "multiplicity family")
        unique_ids(list(parsed.measurement_plan.constructs), "construct")

        primary = [item for item in parsed.analysis_declarations if item.role == "primary"]
        if len(primary) != 1:
            raise ValueError("STUDY_PLAN_PRIMARY_ANALYSIS_REQUIRED: 必须恰好声明一个 primary analysis")
        primary_ids = set(primary[0].robustness_analysis_ids)
        declared_robustness_ids = {
            item.id for item in parsed.analysis_declarations if item.role == "robustness"
        }
        if not primary_ids.issubset(declared_robustness_ids):
            raise ValueError("STUDY_PLAN_ROBUSTNESS_REFERENCE_INVALID: primary 引用了未声明的 robustness analysis")

        for hypothesis in parsed.hypotheses:
            if not set(hypothesis.estimand_ids).issubset(estimand_ids):
                raise ValueError(f"STUDY_PLAN_REFERENCE_INVALID: hypothesis {hypothesis.id} 引用了未知 estimand")
        for analysis in parsed.analysis_declarations:
            if not set(analysis.estimand_ids).issubset(estimand_ids):
                raise ValueError(f"STUDY_PLAN_REFERENCE_INVALID: analysis {analysis.id} 引用了未知 estimand")
            if analysis.role == "primary" and analysis.id in primary_ids:
                raise ValueError("STUDY_PLAN_ROBUSTNESS_REFERENCE_INVALID: analysis 不能引用自身")
        for family in parsed.multiplicity_families:
            if family.member_estimand_ids:
                available = estimand_ids
                member_ids = family.member_estimand_ids
            else:
                if family.member_type is None:
                    raise ValueError(f"STUDY_PLAN_MULTIPLICITY_REFERENCE_INVALID: family {family.id} 缺少 memberType")
                available = {
                    "hypothesis": hypothesis_ids,
                    "estimand": estimand_ids,
                    "analysis": analysis_ids,
                }[family.member_type]
                member_ids = family.member_ids
            if not set(member_ids).issubset(available):
                raise ValueError(f"STUDY_PLAN_MULTIPLICITY_REFERENCE_INVALID: family {family.id} 引用了未知成员")

        role_keys: set[str] = set()
        for role in parsed.sample_definition.roles:
            if role.key in role_keys:
                raise ValueError(f"STUDY_PLAN_ROLE_INVALID: 计划变量角色重复: {role.key}")
            role_keys.add(role.key)
            if len(set(role.accepted_types)) != len(role.accepted_types):
                raise ValueError(f"STUDY_PLAN_ROLE_INVALID: acceptedTypes 重复: {role.key}")

    @staticmethod
    def _payload_from_plan(plan: dict[str, object]) -> dict[str, object]:
        return {key: plan[key] for key in StudyPlanService._PAYLOAD_KEYS if key in plan}

    @staticmethod
    def _primary_analysis(payload: dict[str, object]) -> dict[str, object]:
        declarations = payload.get("analysisDeclarations")
        if not isinstance(declarations, list):
            raise ValueError("STUDY_PLAN_ANALYSIS_DECLARATION_REQUIRED: 分析声明损坏")
        primary = next(
            (item for item in declarations if isinstance(item, dict) and item.get("role") == "primary"),
            None,
        )
        if primary is None:
            raise ValueError("STUDY_PLAN_PRIMARY_ANALYSIS_REQUIRED: 必须声明主分析")
        return cast(dict[str, object], primary)

    @staticmethod
    def _planning_context(payload: dict[str, object]) -> dict[str, object]:
        context = cast(dict[str, object], payload["context"])
        roles: dict[str, str] = {}
        sample_definition = payload.get("sampleDefinition")
        planned_roles = sample_definition.get("roles", []) if isinstance(sample_definition, dict) else []
        if isinstance(planned_roles, list):
            for role in planned_roles:
                if not isinstance(role, dict):
                    continue
                structure_role = role.get("structureRole")
                variable_id = role.get("variableId")
                if isinstance(structure_role, str) and structure_role:
                    roles[structure_role] = (
                        str(variable_id)
                        if isinstance(variable_id, str) and variable_id
                        else f"planned:{structure_role}"
                    )
        return {
            "studyContext": {"value": context},
            "structure": {"roles": roles, "profile": None},
        }

    def create(self, project_id: str, payload: dict[str, object]) -> dict[str, object]:
        if not payload:
            raise ValueError("STUDY_PLAN_PAYLOAD_REQUIRED: 研究计划不能为空")
        normalized = self._normalize_payload(payload)
        self._validate_payload(normalized)
        return self.repository.create_study_plan(project_id, normalized)

    def update(
        self,
        plan_id: str,
        expected_revision: int,
        payload: dict[str, object],
    ) -> dict[str, object]:
        if not payload:
            raise ValueError("STUDY_PLAN_PAYLOAD_REQUIRED: 研究计划不能为空")
        current = self.repository.get_study_plan(plan_id)
        if current is None:
            raise LookupError("研究计划版本不存在")
        if current.get("status") == "frozen":
            raise ValueError("STUDY_PLAN_FROZEN: 冻结计划只能创建下一版本")
        normalized = self._normalize_payload(payload)
        self._validate_payload(normalized)
        return self.repository.update_study_plan(plan_id, expected_revision, normalized)

    def revise(
        self,
        plan_id: str,
        expected_revision: int,
        payload: dict[str, object],
    ) -> dict[str, object]:
        if not payload:
            raise ValueError("STUDY_PLAN_PAYLOAD_REQUIRED: 研究计划不能为空")
        current = self.repository.get_study_plan(plan_id)
        if current is None:
            raise LookupError("研究计划版本不存在")
        normalized = self._normalize_payload(payload)
        self._validate_payload(normalized)
        return self.repository.create_study_plan_revision(plan_id, expected_revision, normalized)

    def _validate_freeze(self, plan: dict[str, object]) -> None:
        payload = self._payload_from_plan(plan)
        if isinstance(payload.get("migration"), dict):
            raise ValueError(
                "STUDY_PLAN_MIGRATION_REQUIRES_REVIEW: v1 迁移草稿必须经人工补全并以 v2 载荷重新保存后才能冻结"
            )
        self._validate_payload(payload, require_hypothesis=True)
        validate_plan_causal_targets(payload, self.registry.definition_for)
        declarations = payload.get("analysisDeclarations")
        assert isinstance(declarations, list)
        for item in declarations:
            if not isinstance(item, dict):
                continue
            slice_id = str(item.get("capabilitySliceId", "")).strip()
            definition = self.registry.definition_for(slice_id)
            if definition is None or not definition.execution_available or not definition.product_visible:
                prefix = "ROBUSTNESS_ANALYSIS_NOT_EXECUTABLE" if item.get("role") == "robustness" else "PLANNED_ANALYSIS_NOT_EXECUTABLE"
                raise ValueError(f"{prefix}: {slice_id or '未声明 slice'}")
            applicability = self.registry.evaluate_slice(
                slice_id,
                self._planning_context(payload),
                require_artifacts=False,
            )
            if not applicability.get("applicable"):
                prefix = "ROBUSTNESS_ANALYSIS_NOT_APPLICABLE" if item.get("role") == "robustness" else "PLANNED_ANALYSIS_NOT_APPLICABLE"
                raise ValueError(
                    prefix + ": " + str(applicability.get("blockedReason") or slice_id)
                )

        primary_slice = str(self._primary_analysis(payload).get("capabilitySliceId", ""))
        if primary_slice.startswith("power_analysis"):
            power_plan = payload.get("powerPlan")
            if not isinstance(power_plan, dict):
                raise ValueError("POWER_SPEC_REQUIRED: 冻结功效计划必须包含可验证规格")
            try:
                PowerAnalysisSpec.model_validate(power_plan)
            except ValueError as error:
                raise ValueError(f"POWER_SPEC_INVALID: {error}") from error

    def freeze(self, plan_id: str) -> dict[str, object]:
        plan = self.repository.get_study_plan(plan_id)
        if plan is None:
            raise LookupError("研究计划版本不存在")
        if plan.get("status") == "frozen":
            return plan
        self._validate_freeze(plan)
        return self.repository.freeze_study_plan(plan_id)
    def bind_for_analysis(self, dataset_id: str, binding: dict[str, object]) -> dict[str, object]:
        return self.binding.bind_for_analysis(self, dataset_id, binding)

    def bind_for_execution(self, dataset_id: str, binding: dict[str, object], *, execution_spec: dict[str, object], identity: dict[str, object] | None, spec_hash: str | None = None) -> dict[str, object]:
        return self.binding.bind_for_analysis(self, dataset_id, binding, execution_spec=execution_spec, identity=identity, spec_hash=spec_hash)
    def result_binding_status(
        self,
        current_plan: dict[str, object] | None,
        binding: dict[str, object],
    ) -> tuple[str, list[str]]:
        return self.binding.result_binding_status(current_plan, binding)
    @staticmethod
    def _variable_id(value: object) -> str | None:
        if isinstance(value, dict):
            candidate = value.get("variableId")
        else:
            candidate = value
        return str(candidate) if candidate is not None and str(candidate).strip() else None
    @staticmethod
    def _contexts_differ(plan_context: object, dataset_context: object) -> bool:
        return not isinstance(plan_context, dict) or not isinstance(dataset_context, dict) or any(
            plan_context.get(key) != dataset_context.get(key)
            for key in ("timeStructure", "dependenceStructure", "design")
        )
    def map_dataset(
        self,
        plan_id: str,
        dataset_id: str,
        mapping: dict[str, object],
        status: str,
    ) -> dict[str, object]:
        plan = self.repository.get_study_plan(plan_id)
        if plan is None:
            raise LookupError("研究计划版本不存在")
        if plan.get("status") != "frozen":
            raise ValueError("STUDY_PLAN_NOT_FROZEN: 只有冻结后的研究计划才能映射数据")
        dataset = self.repository.get_dataset(dataset_id)
        if str(plan.get("projectId")) != str(dataset.get("projectId")):
            raise ValueError("PLAN_PROJECT_DATASET_MISMATCH: 计划与数据版本不属于同一研究项目")
        payload = self._payload_from_plan(plan)
        self._validate_freeze(plan)
        current_context = self.repository.get_study_context(str(dataset["projectId"]))
        if current_context is None:
            raise ValueError("PLAN_CONTEXT_INCOMPLETE: 数据项目尚未保存研究上下文")
        plan_context = payload.get("context")
        if self._contexts_differ(plan_context, {
            "timeStructure": current_context.get("timeStructure"),
            "dependenceStructure": current_context.get("dependenceStructure"),
            "design": current_context.get("design"),
        }):
            raise ValueError("PLAN_CONTEXT_MISMATCH: 当前数据上下文与冻结计划不一致，请创建新计划版本")

        sample_definition = payload.get("sampleDefinition")
        planned_roles = sample_definition.get("roles", []) if isinstance(sample_definition, dict) else []
        declared_keys: set[str] = set()
        if isinstance(planned_roles, list):
            for role in planned_roles:
                if isinstance(role, dict):
                    declared_keys.add(self._role_key(role))
        for key, _value in mapping.items():
            if key in {"deviationReason", "notes"}:
                continue
            if key not in declared_keys:
                raise ValueError(f"PLAN_MAPPING_ROLE_UNKNOWN: 映射中包含未声明的计划角色: {key}")

        variables = cast(list[dict[str, object]], dataset["variables"])
        by_id = {str(variable["id"]): variable for variable in variables}
        for key, value in mapping.items():
            if key in {"deviationReason", "notes"}:
                continue
            variable_id = self._variable_id(value)
            if variable_id is not None and variable_id not in by_id:
                raise ValueError(f"PLAN_DATASET_VARIABLE_UNKNOWN: {key}")
            role = next(
                (item for item in planned_roles if isinstance(item, dict) and self._role_key(item) == key),
                None,
            ) if isinstance(planned_roles, list) else None
            accepted = role.get("acceptedTypes") if isinstance(role, dict) else None
            if variable_id is not None and isinstance(accepted, list) and accepted:
                actual_type = by_id[variable_id].get("confirmedType") or by_id[variable_id].get("inferredType")
                if actual_type not in accepted:
                    raise ValueError(
                        f"PLAN_VARIABLE_TYPE_MISMATCH: {key} 需要 {', '.join(str(item) for item in accepted)}，"
                        f"当前为 {actual_type}"
                    )
            structure_role = role.get("structureRole") if isinstance(role, dict) else None
            if isinstance(structure_role, str):
                structure = self.repository.get_dataset_structure(dataset_id)
                actual_structure_role = structure.get(structure_role) if structure else None
                if variable_id != actual_structure_role:
                    raise ValueError(
                        f"PLAN_STRUCTURE_ROLE_MISMATCH: {key} 必须映射到已确认的结构角色 {structure_role}"
                    )

        if status == "ready":
            missing = [
                self._role_key(role)
                for role in planned_roles
                if isinstance(role, dict) and self._role_key(role) not in mapping
            ] if isinstance(planned_roles, list) else []
            if missing:
                raise ValueError(
                    f"PLAN_MAPPING_INCOMPLETE: 尚未为计划角色映射实际变量: {', '.join(missing)}"
                )
            if "deviationReason" in mapping:
                raise ValueError("PLAN_DEVIATION_STATUS_MISMATCH: 有偏离说明时状态必须为 deviated")
        if status == "deviated":
            reason = mapping.get("deviationReason")
            if not isinstance(reason, str) or len(reason.strip()) < 10:
                raise ValueError("PLAN_DEVIATION_REASON_REQUIRED: 偏离计划时必须记录至少 10 个字符的原因")
        return self.repository.map_study_plan_dataset(plan_id, dataset_id, mapping, status)
