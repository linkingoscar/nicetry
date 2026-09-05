from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from app.services.dataset_repository import DatasetRepository
from app.services.repository_io import JsonObject

_TOKEN = re.compile(r"^[A-Za-z0-9._-]{1,180}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:20]
    return f"{prefix}_{digest}"


def _measurement_id(state: JsonObject) -> str | None:
    direct = state.get("measurementVersionId")
    if isinstance(direct, str) and _TOKEN.fullmatch(direct):
        return direct
    for key in ("metadata", "contextLineage"):
        container = state.get(key)
        if not isinstance(container, dict):
            continue
        direct = container.get("measurementVersionId")
        if isinstance(direct, str) and _TOKEN.fullmatch(direct):
            return direct
        measurement = container.get("measurement")
        nested = measurement.get("id") if isinstance(measurement, dict) else None
        if isinstance(nested, str) and _TOKEN.fullmatch(nested):
            return nested
    return None


class AnalysisIndexRecoveryMixin:
    repository: DatasetRepository

    def _recovery_document(
        self,
        project_id: str,
        analysis_id: str,
        title: str,
        method_id: str,
        category_id: str,
        source: str,
        dataset_id: str,
        measurement_id: str | None,
        created_at: str,
        procedure: str | None = None,
    ) -> JsonObject:
        raise NotImplementedError

    @staticmethod
    def _existing_run(runs: dict[str, JsonObject], run_id: str) -> JsonObject:
        return runs.get(run_id) or {}

    @staticmethod
    def _existing_analysis_id(
        runs: dict[str, JsonObject],
        run_id: str,
    ) -> str | None:
        run = runs.get(run_id)
        analysis_id = run.get("analysisId") if run else None
        return (
            analysis_id
            if isinstance(analysis_id, str) and _TOKEN.fullmatch(analysis_id)
            else None
        )

    def _merge_model_and_empirical_jobs(
        self,
        project_id: str,
        documents: dict[str, JsonObject],
        runs: dict[str, JsonObject],
    ) -> bool:
        changed = False
        for state in self.repository.list_analysis_jobs_for_index():
            run_id = str(state.get("id", ""))
            dataset_id = str(state.get("datasetId", ""))
            if not _TOKEN.fullmatch(run_id) or not _TOKEN.fullmatch(dataset_id):
                continue
            source = "empirical" if state.get("jobKind") == "empirical" else "model"
            created_at = str(state.get("createdAt") or _now())
            measurement_id = _measurement_id(state)
            raw_options = state.get("options")
            options: JsonObject = raw_options if isinstance(raw_options, dict) else {}
            procedure = str(options.get("procedure")) if options.get("procedure") else None
            existing_run = self._existing_run(runs, run_id)
            existing_method = existing_run.get("methodId")
            if isinstance(existing_method, str):
                method_id = existing_method
            elif options.get("methodId"):
                method_id = str(options["methodId"])
            elif source == "empirical" and procedure:
                method_id = f"empirical.{procedure}"
            else:
                method_id = "model.process"
            if not _TOKEN.fullmatch(method_id):
                method_id = "model.process" if source == "model" else "empirical.unknown"

            explicit_analysis_id = options.get("analysisId") if source == "empirical" else None
            analysis_id = self._existing_analysis_id(runs, run_id)
            if (
                analysis_id is None
                and isinstance(explicit_analysis_id, str)
                and _TOKEN.fullmatch(explicit_analysis_id)
            ):
                analysis_id = explicit_analysis_id
            elif analysis_id is None and source == "model":
                analysis_id = _stable_id(
                    "analysis_model", state.get("modelId"), dataset_id
                )
            elif analysis_id is None:
                analysis_id = _stable_id(
                    "analysis_empirical",
                    dataset_id,
                    measurement_id,
                    procedure,
                    method_id,
                )

            if analysis_id not in documents:
                title = procedure or ("模型分析" if source == "model" else "历史实证分析")
                if source == "model":
                    try:
                        frozen = self.repository.get_model_version(
                            str(state.get("modelId")),
                            int(state.get("modelVersion", 0)),
                        )
                        spec = frozen.get("modelSpec") if isinstance(frozen, dict) else None
                        if isinstance(spec, dict):
                            title = str(spec.get("name") or title)
                            estimation = spec.get("estimation")
                            if (
                                isinstance(estimation, dict)
                                and estimation.get("family") == "sem"
                            ):
                                method_id = "model.sem"
                    except (LookupError, ValueError, TypeError):
                        pass
                documents[analysis_id] = self._recovery_document(
                    project_id,
                    analysis_id,
                    title,
                    method_id,
                    source,
                    source,
                    dataset_id,
                    measurement_id,
                    created_at,
                    procedure,
                )
                changed = True

            label = existing_run.get("label")
            recovered: JsonObject = {
                "id": run_id,
                "analysisId": analysis_id,
                "projectId": project_id,
                "source": source,
                "methodId": method_id,
                "label": label if isinstance(label, str) else documents[analysis_id]["title"],
                "datasetVersionId": dataset_id,
                "measurementVersionId": measurement_id,
                "createdAt": created_at,
                "status": str(state.get("status") or "indexed"),
            }
            if state.get("modelId"):
                recovered["modelId"] = str(state["modelId"])
            if state.get("reportId"):
                recovered["reportId"] = str(state["reportId"])
            merged = {**runs.get(run_id, {}), **recovered}
            if runs.get(run_id) != merged:
                runs[run_id] = merged
                changed = True
        return changed

    def _merge_advanced_jobs(
        self,
        project_id: str,
        documents: dict[str, JsonObject],
        runs: dict[str, JsonObject],
    ) -> bool:
        changed = False
        for state in self.repository.list_advanced_jobs_for_index():
            run_id = str(state.get("id", ""))
            dataset_id = str(state.get("datasetVersionId") or "")
            if not _TOKEN.fullmatch(run_id) or not _TOKEN.fullmatch(dataset_id):
                continue
            family = str(state.get("family") or "advanced")
            existing_run = self._existing_run(runs, run_id)
            existing_method = existing_run.get("methodId")
            method_id = existing_method if isinstance(existing_method, str) else family
            if not _TOKEN.fullmatch(method_id):
                method_id = family if _TOKEN.fullmatch(family) else "advanced"

            raw_analysis_id = state.get("analysisId")
            analysis_id = self._existing_analysis_id(runs, run_id)
            if analysis_id is None:
                analysis_id = (
                    str(raw_analysis_id)
                    if isinstance(raw_analysis_id, str)
                    and _TOKEN.fullmatch(raw_analysis_id)
                    else _stable_id("analysis_advanced", family, dataset_id, run_id)
                )

            existing_measurement = existing_run.get("measurementVersionId")
            measurement_id = (
                str(existing_measurement)
                if isinstance(existing_measurement, str)
                else _measurement_id(state)
            )
            created_at = str(state.get("createdAt") or _now())
            if analysis_id not in documents:
                existing_label = existing_run.get("label")
                title = (
                    str(existing_label)
                    if isinstance(existing_label, str)
                    else family.replace("_", " ")
                )
                documents[analysis_id] = self._recovery_document(
                    project_id,
                    analysis_id,
                    title,
                    method_id,
                    family if _TOKEN.fullmatch(family) else "advanced",
                    "advanced",
                    dataset_id,
                    measurement_id,
                    created_at,
                )
                changed = True

            existing_label = existing_run.get("label")
            existing_family = existing_run.get("family")
            recovered: JsonObject = {
                "id": run_id,
                "analysisId": analysis_id,
                "projectId": project_id,
                "source": "advanced",
                "methodId": method_id,
                "label": (
                    existing_label
                    if isinstance(existing_label, str)
                    else documents[analysis_id]["title"]
                ),
                "family": (
                    existing_family
                    if isinstance(existing_family, str)
                    else family
                ),
                "datasetVersionId": dataset_id,
                "measurementVersionId": measurement_id,
                "createdAt": created_at,
                "status": str(state.get("status") or "indexed"),
            }
            merged = {**runs.get(run_id, {}), **recovered}
            if runs.get(run_id) != merged:
                runs[run_id] = merged
                changed = True
        return changed

    @staticmethod
    def _clean_index_links(
        documents: dict[str, JsonObject],
        runs: dict[str, JsonObject],
    ) -> bool:
        changed = False
        referenced = {
            str(run.get("analysisId"))
            for run in runs.values()
            if isinstance(run.get("analysisId"), str)
        }
        for analysis_id, document in list(documents.items()):
            if (
                document.get("source") in {"model", "advanced"}
                and analysis_id not in referenced
            ):
                del documents[analysis_id]
                changed = True

        for document in documents.values():
            document_runs = sorted(
                (
                    run
                    for run in runs.values()
                    if run.get("analysisId") == document.get("id")
                ),
                key=lambda item: str(item.get("createdAt", "")),
                reverse=True,
            )
            latest = document_runs[0] if document_runs else None
            if latest and document.get("latestRunId") != latest.get("id"):
                document["latestRunId"] = latest["id"]
                changed = True
            primary = document.get("primaryRunId")
            if primary and not any(run.get("id") == primary for run in document_runs):
                document.pop("primaryRunId", None)
                changed = True
        return changed

    def _merge_reconstructed_jobs(self, project_id: str, index: JsonObject) -> bool:
        documents = self._document_map(index)
        runs = self._run_map(index)
        changed = self._merge_model_and_empirical_jobs(project_id, documents, runs)
        changed = self._merge_advanced_jobs(project_id, documents, runs) or changed
        changed = self._clean_index_links(documents, runs) or changed
        index["documents"] = sorted(
            documents.values(),
            key=lambda item: str(item.get("updatedAt", "")),
            reverse=True,
        )
        index["runs"] = sorted(
            runs.values(),
            key=lambda item: str(item.get("createdAt", "")),
            reverse=True,
        )
        index["rebuiltFromServerJobs"] = True
        return changed

    @staticmethod
    def _document_map(index: JsonObject) -> dict[str, JsonObject]:
        raise NotImplementedError

    @staticmethod
    def _run_map(index: JsonObject) -> dict[str, JsonObject]:
        raise NotImplementedError
