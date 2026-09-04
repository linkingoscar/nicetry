from __future__ import annotations

import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.services.analysis_index_recovery import AnalysisIndexRecoveryMixin
from app.services.dataset_repository import DatasetRepository
from app.services.repository_io import JsonObject, _read_json_safe, _write_json_atomic
from app.settings import Settings

_INDEX_LOCK = threading.RLock()
_TOKEN = re.compile(r"^[A-Za-z0-9._-]{1,180}$")
_SOURCES = {"empirical", "model", "advanced"}
_MAX_DOCUMENTS = 1000
_MAX_RUNS = 6000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token(value: object, label: str, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError(f"{label} 格式无效")
    return value


def _source(value: object) -> str:
    if value not in _SOURCES:
        raise ValueError("analysis source 必须为 empirical/model/advanced")
    return str(value)


def _text(value: object, label: str, *, maximum: int = 240) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} 必须为字符串")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{label} 长度无效")
    return normalized


def _empty(project_id: str) -> JsonObject:
    return {
        "schemaVersion": "1.0.0",
        "projectId": project_id,
        "documents": [],
        "runs": [],
        "rebuiltFromServerJobs": False,
    }


class AnalysisIndexService(AnalysisIndexRecoveryMixin):
    """Server-owned navigation metadata; statistical stores remain authoritative."""

    def __init__(self, repository: DatasetRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def _path(self, project_id: str) -> Path:
        project = _token(project_id, "project id")
        if project != "default":
            raise ValueError("当前本地工作台只支持 default 项目索引")
        return self.settings.state_root / "projects" / project / "analysis-index.json"

    def _read(self, project_id: str) -> JsonObject:
        path = self._path(project_id)
        if not path.exists():
            return _empty(project_id)
        value = _read_json_safe(path)
        valid = (
            value.get("schemaVersion") == "1.0.0"
            and value.get("projectId") == project_id
            and isinstance(value.get("documents"), list)
            and isinstance(value.get("runs"), list)
        )
        if not valid:
            raise LookupError("AnalysisIndex 文件损坏或身份不匹配")
        return value

    def _write(self, project_id: str, index: JsonObject) -> None:
        documents = index.get("documents")
        runs = index.get("runs")
        if not isinstance(documents, list) or not isinstance(runs, list):
            raise ValueError("AnalysisIndex 结构无效")
        index["documents"] = documents[:_MAX_DOCUMENTS]
        index["runs"] = runs[:_MAX_RUNS]
        _write_json_atomic(self._path(project_id), index)

    @staticmethod
    def _document_map(index: JsonObject) -> dict[str, JsonObject]:
        documents = index.get("documents")
        if not isinstance(documents, list):
            return {}
        return {
            str(item["id"]): item
            for item in documents
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }

    @staticmethod
    def _run_map(index: JsonObject) -> dict[str, JsonObject]:
        runs = index.get("runs")
        if not isinstance(runs, list):
            return {}
        return {
            str(item["id"]): item
            for item in runs
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }

    def _normalize_document(self, project_id: str, payload: JsonObject) -> JsonObject:
        source = _source(payload.get("source"))
        analysis_id = _token(payload.get("id"), "analysis id")
        dataset_id = _token(payload.get("datasetVersionId"), "dataset version id")
        measurement_id = _token(
            payload.get("measurementVersionId"),
            "measurement version id",
            required=False,
        )
        method_id = _token(payload.get("methodId"), "method id")
        category_id = _token(payload.get("categoryId") or source, "category id")
        procedure = payload.get("procedure")
        if procedure is not None:
            procedure = _token(procedure, "procedure")
        created_at = (
            payload.get("createdAt")
            if isinstance(payload.get("createdAt"), str)
            else _now()
        )
        updated_at = (
            payload.get("updatedAt")
            if isinstance(payload.get("updatedAt"), str)
            else created_at
        )
        document: JsonObject = {
            "id": analysis_id,
            "projectId": project_id,
            "title": _text(payload.get("title") or method_id, "analysis title"),
            "methodId": method_id,
            "categoryId": category_id,
            "source": source,
            "datasetVersionId": dataset_id,
            "measurementVersionId": measurement_id,
            "createdAt": created_at,
            "updatedAt": updated_at,
            "pinned": bool(payload.get("pinned", False)),
            "archived": bool(payload.get("archived", False)),
        }
        if procedure is not None:
            document["procedure"] = procedure
        for key in ("currentDraftId", "latestRunId", "primaryRunId"):
            value = payload.get(key)
            if value is not None:
                document[key] = _token(value, key)
        return document

    def _normalize_run(self, project_id: str, payload: JsonObject) -> JsonObject:
        source = _source(payload.get("source"))
        run_id = _token(payload.get("id") or payload.get("runId"), "run id")
        analysis_id = _token(payload.get("analysisId"), "analysis id")
        dataset_id = _token(payload.get("datasetVersionId"), "dataset version id")
        measurement_id = _token(
            payload.get("measurementVersionId"),
            "measurement version id",
            required=False,
        )
        method_id = _token(payload.get("methodId"), "method id")
        created_at = (
            payload.get("createdAt")
            if isinstance(payload.get("createdAt"), str)
            else _now()
        )
        run: JsonObject = {
            "id": run_id,
            "analysisId": analysis_id,
            "projectId": project_id,
            "source": source,
            "methodId": method_id,
            "label": _text(payload.get("label") or method_id, "run label"),
            "datasetVersionId": dataset_id,
            "measurementVersionId": measurement_id,
            "createdAt": created_at,
            "status": str(payload.get("status") or "indexed"),
        }
        for key in ("family", "modelId", "resultId", "reportId"):
            value = payload.get(key)
            if value is not None:
                run[key] = _token(value, key)
        return run

    def upsert_document(self, project_id: str, payload: JsonObject) -> JsonObject:
        with _INDEX_LOCK:
            index = self._read(project_id)
            normalized = self._normalize_document(project_id, payload)
            documents = self._document_map(index)
            existing = documents.get(str(normalized["id"]))
            if existing:
                normalized["createdAt"] = existing.get(
                    "createdAt", normalized["createdAt"]
                )
                for key in ("latestRunId", "primaryRunId"):
                    if key not in normalized and existing.get(key) is not None:
                        normalized[key] = existing[key]
            documents[str(normalized["id"])] = normalized
            index["documents"] = sorted(
                documents.values(),
                key=lambda item: str(item.get("updatedAt", "")),
                reverse=True,
            )
            self._write(project_id, index)
            return normalized

    def patch_document(
        self,
        project_id: str,
        analysis_id: str,
        patch: JsonObject,
    ) -> JsonObject:
        with _INDEX_LOCK:
            index = self._read(project_id)
            documents = self._document_map(index)
            document = documents.get(str(_token(analysis_id, "analysis id")))
            if document is None:
                raise LookupError(f"AnalysisDocument 不存在: {analysis_id}")
            if "title" in patch:
                document["title"] = _text(patch.get("title"), "analysis title")
            if "pinned" in patch:
                document["pinned"] = bool(patch.get("pinned"))
            if "archived" in patch:
                document["archived"] = bool(patch.get("archived"))
            if "primaryRunId" in patch:
                run_id = patch.get("primaryRunId")
                if run_id is None:
                    document.pop("primaryRunId", None)
                else:
                    run_id = _token(run_id, "primary run id")
                    run = self._run_map(index).get(str(run_id))
                    if run is None or run.get("analysisId") != analysis_id:
                        raise ValueError("主要结果必须属于当前 AnalysisDocument")
                    document["primaryRunId"] = run_id
            document["updatedAt"] = _now()
            index["documents"] = list(documents.values())
            self._write(project_id, index)
            return document

    def register_run(self, project_id: str, payload: JsonObject) -> JsonObject:
        with _INDEX_LOCK:
            index = self._read(project_id)
            run = self._normalize_run(project_id, payload)
            runs = self._run_map(index)
            existing = self._existing_run(runs, str(run["id"]))
            if existing:
                existing_analysis_id = existing.get("analysisId")
                if isinstance(existing_analysis_id, str) and _TOKEN.fullmatch(
                    existing_analysis_id
                ):
                    run["analysisId"] = existing_analysis_id
                run = {
                    **existing,
                    **run,
                    "createdAt": existing.get("createdAt", run["createdAt"]),
                }
            documents = self._document_map(index)
            analysis_id = str(run["analysisId"])
            if analysis_id not in documents:
                documents[analysis_id] = self._normalize_document(
                    project_id,
                    {
                        "id": analysis_id,
                        "projectId": project_id,
                        "title": run["label"],
                        "methodId": run["methodId"],
                        "categoryId": payload.get("categoryId") or run["source"],
                        "source": run["source"],
                        "datasetVersionId": run["datasetVersionId"],
                        "measurementVersionId": run.get("measurementVersionId"),
                        "procedure": payload.get("procedure"),
                        "createdAt": run["createdAt"],
                        "updatedAt": run["createdAt"],
                        "pinned": False,
                    },
                )
            runs[str(run["id"])] = run
            document = documents[analysis_id]
            document["latestRunId"] = run["id"]
            if str(run["createdAt"]) > str(document.get("updatedAt", "")):
                document["updatedAt"] = run["createdAt"]
            index["documents"] = list(documents.values())
            index["runs"] = sorted(
                runs.values(),
                key=lambda item: str(item.get("createdAt", "")),
                reverse=True,
            )
            self._write(project_id, index)
            return run

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
        payload: JsonObject = {
            "id": analysis_id,
            "projectId": project_id,
            "title": title,
            "methodId": method_id,
            "categoryId": category_id,
            "source": source,
            "datasetVersionId": dataset_id,
            "measurementVersionId": measurement_id,
            "createdAt": created_at,
            "updatedAt": created_at,
            "pinned": False,
        }
        if procedure:
            payload["procedure"] = procedure
        return self._normalize_document(project_id, payload)

    def get_index(self, project_id: str = "default") -> JsonObject:
        with _INDEX_LOCK:
            index = self._read(project_id)
            changed = self._merge_reconstructed_jobs(project_id, index)
            if changed or not self._path(project_id).exists():
                self._write(project_id, index)
            return index
