from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.services.repository_io import (
    JsonObject,
    _read_json_safe,
    _write_json_atomic,
    safe_identifier,
)
from app.settings import Settings

_DRAFT_LOCK = threading.RLock()
_MAX_PAYLOAD_BYTES = 500_000


class EmpiricalDraftConflictError(RuntimeError):
    pass


class EmpiricalDraftStore:
    """Versioned editable analysis drafts bound to one local project and analysis."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _path(self, project_id: str, analysis_id: str) -> Path:
        project = safe_identifier(project_id, label="project id")
        analysis = safe_identifier(analysis_id, label="analysis id")
        if project != "default":
            raise ValueError("当前本地工作台只支持 default 项目草稿")
        return self.settings.state_root / "projects" / project / "analysis-drafts" / f"{analysis}.json"

    def read(self, project_id: str, analysis_id: str) -> JsonObject:
        path = self._path(project_id, analysis_id)
        if not path.exists():
            raise LookupError(f"AnalysisDraft 不存在: {analysis_id}")
        document = _read_json_safe(path)
        if document.get("projectId") != project_id or document.get("analysisId") != analysis_id:
            raise LookupError("AnalysisDraft 文件身份不匹配")
        return document

    def save(
        self,
        project_id: str,
        analysis_id: str,
        payload: JsonObject,
        expected_revision: int | None,
    ) -> JsonObject:
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
            raise ValueError("AnalysisDraft 超过 500 KB 上限")
        with _DRAFT_LOCK:
            path = self._path(project_id, analysis_id)
            current_revision = 0
            created_at = datetime.now(timezone.utc).isoformat()
            if path.exists():
                current = self.read(project_id, analysis_id)
                current_revision = int(current.get("revision", 0))
                created_at = str(current.get("createdAt", created_at))
            if expected_revision is not None and expected_revision != current_revision:
                raise EmpiricalDraftConflictError(
                    f"AnalysisDraft 已更新：期望修订 {expected_revision}，当前为 {current_revision}"
                )
            now = datetime.now(timezone.utc).isoformat()
            document: JsonObject = {
                "schemaVersion": "1.0.0",
                "projectId": project_id,
                "analysisId": analysis_id,
                "revision": current_revision + 1,
                "createdAt": created_at,
                "updatedAt": now,
                "payload": payload,
            }
            _write_json_atomic(path, document)
            return document
