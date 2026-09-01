from __future__ import annotations

from app.capability_catalog import ACTIVE_CAPABILITIES, CapabilityDefinition
from app.services.repository_io import JsonObject


class CapabilityApplicabilityRegistry:
    def __init__(self, definitions: tuple[CapabilityDefinition, ...] = ACTIVE_CAPABILITIES):
        self._definitions = definitions

    @staticmethod
    def _profile_allows(profile: dict[str, object] | None, requirement: str) -> bool:
        if profile is None:
            return False
        if requirement in {"two_level", "cross_classified"}:
            return profile.get("nestingClassification") == requirement
        points = profile.get("timePointCount")
        if requirement == "panel_min_3":
            return isinstance(points, int) and points >= 3
        if requirement == "panel_min_5":
            return isinstance(points, int) and points >= 5
        if requirement == "diary_min_20":
            observations = profile.get("observationsPerSubject")
            return isinstance(observations, dict) and float(observations.get("maximum", 0)) >= 20
        return True

    def evaluate(
        self,
        definition: CapabilityDefinition,
        context: JsonObject,
        *,
        require_artifacts: bool = True,
    ) -> JsonObject:
        missing: list[str] = []
        study = context.get("studyContext")
        structure = context.get("structure")
        if not isinstance(study, dict):
            missing.append("studyContext")
        if not isinstance(structure, dict) and ("structure" in definition.required_artifacts or definition.required_roles):
            missing.append("structure")
        value = study.get("value", {}) if isinstance(study, dict) else {}
        if isinstance(value, dict):
            for name, allowed in (
                ("timeStructure", definition.time_structures),
                ("dependenceStructure", definition.dependence_structures),
                ("design", definition.designs),
            ):
                if value.get(name) not in allowed:
                    missing.append(f"{name}={value.get(name)}")
        roles = structure.get("roles", {}) if isinstance(structure, dict) else {}
        roles = roles if isinstance(roles, dict) else {}
        defaults = {role: str(roles[role]) for role in ("subjectId", "clusterId", "timeId", "groupId", "treatmentId") if roles.get(role)}
        required_roles = list(definition.required_roles)
        if value.get("timeStructure") == "panel" and roles.get("dataLayout") == "wide":
            required_roles = [role for role in required_roles if role != "timeId"]
        # A single observed treatment/group column is a valid identifier for a
        # simple two-arm design. The catalog keeps both names so the UI can
        # preserve their semantics, while the applicability gate expresses the
        # actual OR requirement instead of forcing users to duplicate one role.
        if {"groupId", "treatmentId"}.issubset(required_roles):
            required_roles = [
                role for role in required_roles if role not in {"groupId", "treatmentId"}
            ]
            if not (roles.get("groupId") or roles.get("treatmentId")):
                missing.append("groupId or treatmentId")
        missing.extend(role for role in required_roles if not roles.get(role))
        if require_artifacts:
            artifacts = {
                key: context.get(key)
                for key in ("dataset", "structure", "measurement", "sample", "imputation")
            }
            missing.extend(key for key in definition.required_artifacts if artifacts[key] is None)
        if definition.profile_requirement:
            profile = structure.get("profile") if isinstance(structure, dict) else None
            if not self._profile_allows(profile if isinstance(profile, dict) else None, definition.profile_requirement):
                missing.append(f"profile={definition.profile_requirement}")
        return {
            "family": definition.family,
            "sliceId": definition.slice_id,
            "label": definition.label,
            "status": definition.status,
            "executionAvailable": definition.execution_available,
            "validationLevel": definition.validation_level,
            "maturityLevel": definition.maturity_level,
            "publicationEligibility": definition.publication_eligibility,
            "publicationEligibilityReason": definition.publication_eligibility_reason,
            "validationEvidence": definition.validation_evidence.to_dict(),
            "applicable": not missing,
            "requiresRevalidation": True,
            "productVisible": definition.product_visible,
            "requiredRoles": list(definition.required_roles),
            "optionalRoles": list(definition.optional_roles),
            "requiredArtifacts": list(definition.required_artifacts),
            "defaultBindings": defaults,
            "missingRequirements": missing,
            "blockedReason": "；".join(missing) if missing else None,
            "supportBoundary": definition.support_boundary,
        }

    def list(self, context: JsonObject) -> list[JsonObject]:
        return [self.evaluate(definition, context) for definition in self._definitions]

    def definition_for(self, slice_id: str) -> CapabilityDefinition | None:
        return next((definition for definition in self._definitions if definition.slice_id == slice_id), None)

    def evaluate_slice(
        self,
        slice_id: str,
        context: JsonObject,
        *,
        require_artifacts: bool = True,
    ) -> JsonObject:
        definition = self.definition_for(slice_id)
        if definition is None:
            return {
                "sliceId": slice_id,
                "executionAvailable": False,
                "validationLevel": "unvalidated",
                "maturityLevel": "experimental",
                "publicationEligibility": "ineligible",
                "publicationEligibilityReason": "当前分析切片没有活动能力登记，因此不具备论文主分析资格。",
                "validationEvidence": {
                    "contractTests": False,
                    "applicabilityTests": False,
                    "failureFixtures": False,
                    "externalOracle": None,
                    "numericGoldenId": None,
                },
                "applicable": False,
                "productVisible": False,
                "missingRequirements": ["registeredCapability"],
                "blockedReason": "当前分析切片没有上下文适用性登记。",
            }
        return self.evaluate(definition, context, require_artifacts=require_artifacts)

    def contains(self, slice_id: str) -> bool:
        return self.definition_for(slice_id) is not None


applicable_capability_registry = CapabilityApplicabilityRegistry()
