from __future__ import annotations

from typing import cast

from app.services.canonical_identity import canonical_sha256
from app.services.dataset_repository import DatasetRepository
from app.services.repository_errors import MeasurementNotFoundError


class AnalysisContextResolutionError(ValueError):
    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        self.code = code
        self.details = details or {}
        super().__init__(f"{code}: {message}")


class AnalysisContextService:
    """Resolve one immutable, server-generated analysis context."""

    def __init__(self, repository: DatasetRepository) -> None:
        self.repository = repository

    @staticmethod
    def _sample_reference(dataset_sha256: str) -> dict[str, str]:
        sample_hash = canonical_sha256(
            {"datasetSha256": dataset_sha256, "rule": "all_rows"}
        )
        return {
            "id": f"sample_all_{dataset_sha256[:16]}",
            "hash": sample_hash,
        }

    def _measurement_reference(
        self, dataset_id: str, measurement_version: int | None
    ) -> dict[str, str] | None:
        try:
            measurement = self.repository.get_measurement(dataset_id, measurement_version)
        except MeasurementNotFoundError:
            if measurement_version is None:
                return None
            raise AnalysisContextResolutionError(
                "ARTIFACT_DATASET_MISMATCH",
                f"测量版本不存在或不属于当前数据版本: {measurement_version}",
            ) from None
        return {
            "id": str(measurement["id"]),
            "hash": canonical_sha256(measurement),
        }

    def _sample_reference_for_id(
        self, dataset_id: str, sample_version_id: str | None, dataset_sha256: str
    ) -> dict[str, str]:
        if sample_version_id is None:
            return self._sample_reference(dataset_sha256)
        try:
            sample = self.repository.get_analysis_sample(dataset_id, sample_version_id)
        except LookupError as error:
            raise AnalysisContextResolutionError(
                "ARTIFACT_DATASET_MISMATCH",
                f"分析样本不存在或不属于当前数据版本: {sample_version_id}",
            ) from error
        return {
            "id": str(sample["id"]),
            "hash": str(sample["sampleHash"]),
        }

    def _imputation_reference(
        self, dataset_id: str, imputation_version_id: str | None
    ) -> dict[str, str] | None:
        if imputation_version_id is None:
            return None
        artifact = self.repository.get_imputation_dataset(dataset_id, imputation_version_id)
        if artifact is None:
            raise AnalysisContextResolutionError(
                "ARTIFACT_DATASET_MISMATCH",
                f"插补产物不存在或不属于当前数据版本: {imputation_version_id}",
            )
        return {"id": str(artifact["id"]), "hash": str(artifact["hash"])}

    def resolve(
        self,
        dataset_id: str,
        *,
        measurement_version: int | None = None,
        sample_version_id: str | None = None,
        imputation_version_id: str | None = None,
        include_measurement: bool = True,
    ) -> dict[str, object]:
        dataset = self.repository.get_dataset(dataset_id)
        dataset_sha256 = str(cast(dict[str, object], dataset["originalFile"])["sha256"])
        context_record = self.repository.get_study_context(str(dataset["projectId"]))
        structure_record = self.repository.get_dataset_structure(dataset_id)
        measurement = self._measurement_reference(dataset_id, measurement_version) if include_measurement else None
        sample = self._sample_reference_for_id(dataset_id, sample_version_id, dataset_sha256)
        imputation = self._imputation_reference(dataset_id, imputation_version_id)

        study_context: dict[str, object] | None = None
        study_context_hash: str | None = None
        if context_record is not None:
            study_context_hash = str(context_record["contextHash"])
            study_context = {
                "id": context_record["id"],
                "hash": study_context_hash,
                "revision": context_record["revision"],
                "value": {
                    "schemaVersion": context_record["schemaVersion"],
                    "timeStructure": context_record["timeStructure"],
                    "dependenceStructure": context_record["dependenceStructure"],
                    "design": context_record["design"],
                },
            }

        study_value = study_context.get("value", {}) if isinstance(study_context, dict) else {}
        structure_required = not (
            isinstance(study_value, dict)
            and study_value.get("timeStructure") == "cross_sectional"
            and study_value.get("dependenceStructure") == "independent"
            and study_value.get("design") == "observational"
        )

        structure: dict[str, object] | None = None
        structure_hash: str | None = None
        if structure_record is not None:
            structure_hash = str(structure_record["structureHash"])
            structure = {
                "id": structure_record["id"],
                "hash": structure_hash,
                "revision": structure_record["revision"],
                "studyContextVersionId": structure_record["studyContextVersionId"],
                "roles": {
                    "subjectId": structure_record.get("subjectId"),
                    "clusterId": structure_record.get("clusterId"),
                    "timeId": structure_record.get("timeId"),
                    "groupId": structure_record.get("groupId"),
                    "treatmentId": structure_record.get("treatmentId"),
                    "dataLayout": structure_record.get("dataLayout", "long"),
                    "waveCount": structure_record.get("waveCount"),
                },
                "status": structure_record["status"],
                "profile": structure_record.get("profile"),
                "warnings": structure_record.get("warnings", []),
                "overrideReason": structure_record.get("overrideReason"),
            }

        context_hash = canonical_sha256(
            {
                "datasetSha256": dataset_sha256,
                "studyContextHash": study_context_hash,
                "structureHash": structure_hash,
                "measurementHash": None if measurement is None else measurement["hash"],
                "sampleHash": sample["hash"],
                "imputationHash": None if imputation is None else imputation["hash"],
            }
        )
        missing: list[str] = []
        if study_context is None:
            missing.append("studyContext")
        if structure is None and structure_required:
            missing.append("structure")
        validity = "ready" if not missing else "incomplete"
        warnings: list[dict[str, str]] = []
        if structure_record is not None and structure_record["status"] == "warning":
            warnings.extend(cast(list[dict[str, str]], structure_record["warnings"]))

        invalidation: dict[str, object] | None = None
        if missing or warnings:
            upstream_changes: list[str] = []
            affected_objects: list[str] = []
            if "studyContext" in missing:
                upstream_changes.append("研究上下文版本尚未确认")
                affected_objects.extend(["结构角色", "方法适用性目录", "分析草稿"])
            if "structure" in missing:
                upstream_changes.append("数据结构版本尚未确认")
                affected_objects.extend(["结构依赖方法", "实验/纵向角色绑定", "分析草稿"])
            if warnings:
                upstream_changes.append("当前结构画像包含未处理警告")
                affected_objects.extend(["依赖结构的方法", "需要披露结构限制的结果"])
            invalidation = {
                "upstreamChanges": list(dict.fromkeys(upstream_changes)),
                "affectedObjects": list(dict.fromkeys(affected_objects)),
                "historyStatus": "available",
                "requiredAction": "confirm",
            }

        return {
            "schemaVersion": "1.0.0",
            "projectId": dataset["projectId"],
            "dataset": {
                "id": dataset_id,
                "hash": dataset_sha256,
                "sha256": dataset_sha256,
            },
            "studyContext": study_context,
            "structure": structure,
            "measurement": measurement,
            "sample": sample,
            "imputation": imputation,
            "contextHash": context_hash,
            "validity": validity,
            "missingRequirements": missing,
            "warnings": warnings,
            "invalidation": invalidation,
        }
