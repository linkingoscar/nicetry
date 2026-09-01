from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

from app.services.repository_io import (
    UnsafePathError,
    is_link_or_reparse_point,
    safe_relative_path,
)
from app.services.workspace_archive import MANIFEST_NAME, verify_workspace_backup


class WorkspaceMaintenanceError(RuntimeError):
    pass


REFERENCE_COLUMNS = (
    ("dataset_versions", "manifest_path"),
    ("dictionary_versions", "path"),
    ("measurement_versions", "definition_path"),
    ("measurement_versions", "derived_path"),
    ("model_drafts", "path"),
    ("model_versions", "path"),
    ("analysis_runs", "result_path"),
    ("analysis_jobs", "state_path"),
    ("analysis_jobs", "result_path"),
)


def _database_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    uri = path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        for statement in connection.iterdump():
            digest.update(statement.encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def _safe_relative_path(value: str) -> Path:
    try:
        return safe_relative_path(value, label="工作区路径")
    except UnsafePathError as error:
        raise WorkspaceMaintenanceError(str(error)) from error


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _database_references(database_path: Path) -> tuple[set[str], set[str]]:
    if not database_path.is_file():
        return set(), set()
    uri = database_path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        table_names = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        dataset_ids = (
            {str(row[0]) for row in connection.execute("SELECT id FROM dataset_versions")}
            if "dataset_versions" in table_names
            else set()
        )
        referenced_files: set[str] = set()
        for table, column in REFERENCE_COLUMNS:
            if table not in table_names:
                continue
            columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
            if column not in columns:
                continue
            for row in connection.execute(
                f"SELECT {column} FROM {table} WHERE {column} IS NOT NULL"
            ):
                relative = _safe_relative_path(str(row[0]))
                referenced_files.add(relative.as_posix())
    return dataset_ids, referenced_files


def audit_workspace(state_root: Path) -> dict[str, object]:
    state_root = state_root.resolve()
    if not state_root.is_dir():
        raise WorkspaceMaintenanceError(f"工作区不存在: {state_root}")
    database_path = state_root / "metadata.sqlite3"
    dataset_ids, referenced_files = _database_references(database_path)
    datasets_root = state_root / "projects" / "default" / "datasets"
    orphan_directories: list[str] = []
    if datasets_root.is_dir():
        for directory in sorted(path for path in datasets_root.iterdir() if path.is_dir()):
            if directory.name not in dataset_ids:
                orphan_directories.append(directory.relative_to(state_root).as_posix())

    protected_names = {
        "metadata.sqlite3",
        "metadata.sqlite3-wal",
        "metadata.sqlite3-shm",
    }
    all_files = {
        path.relative_to(state_root).as_posix()
        for path in state_root.rglob("*")
        if path.is_file() and path.name not in protected_names
    }
    orphan_files = {
        file
        for directory in orphan_directories
        for file in all_files
        if file == directory or file.startswith(directory + "/")
    }
    unreferenced_files = sorted(all_files - referenced_files)
    return {
        "schemaVersion": "1.0.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "stateRoot": str(state_root),
        "databaseSha256": (_database_sha256(database_path) if database_path.is_file() else None),
        "databaseDatasetCount": len(dataset_ids),
        "referencedFileCount": len(referenced_files),
        "orphanDatasetDirectoryCount": len(orphan_directories),
        "orphanDatasetFileCount": len(orphan_files),
        "orphanDatasetDirectories": orphan_directories,
        "unreferencedFileCount": len(unreferenced_files),
        "unreferencedFiles": unreferenced_files,
    }


def clean_audited_orphan_datasets(
    state_root: Path, audit_path: Path, backup_path: Path
) -> dict[str, object]:
    state_root = state_root.resolve()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("schemaVersion") != "1.0.0":
        raise WorkspaceMaintenanceError("不支持的维护审计格式版本")
    if Path(str(audit.get("stateRoot"))).resolve() != state_root:
        raise WorkspaceMaintenanceError("维护审计与目标工作区不一致")

    database_path = state_root / "metadata.sqlite3"
    current_database_hash = _database_sha256(database_path) if database_path.is_file() else None
    if current_database_hash != audit.get("databaseSha256"):
        raise WorkspaceMaintenanceError("审计后数据库已变化，请重新审计并备份")

    verify_workspace_backup(backup_path)
    with ZipFile(backup_path) as archive:
        manifest = json.loads(archive.read(MANIFEST_NAME))
    backed_up_files = {
        str(entry["path"]): entry
        for entry in manifest["files"]
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }
    if not backed_up_files:
        raise WorkspaceMaintenanceError("备份不包含可验证的文件清单")
    if database_path.is_file():
        database_entry = backed_up_files.get("metadata.sqlite3")
        if database_entry is None:
            raise WorkspaceMaintenanceError("备份缺少本次审计工作区的数据库快照")
        with tempfile.TemporaryDirectory(prefix="researchpath-backup-db-") as temporary:
            backup_database = Path(temporary) / "metadata.sqlite3"
            with (
                ZipFile(backup_path) as archive,
                archive.open("metadata.sqlite3") as source,
                backup_database.open("wb") as target,
            ):
                shutil.copyfileobj(source, target)
            if _database_sha256(backup_database) != current_database_hash:
                raise WorkspaceMaintenanceError("备份数据库不是本次审计工作区的数据库快照")

    current = audit_workspace(state_root)
    current_orphan_value = current["orphanDatasetDirectories"]
    if not isinstance(current_orphan_value, list) or not all(
        isinstance(item, str) for item in current_orphan_value
    ):
        raise WorkspaceMaintenanceError("当前工作区审计结果无效")
    current_orphans = set(current_orphan_value)
    scheduled = [str(path) for path in audit.get("orphanDatasetDirectories", [])]
    deleted_files = 0
    deleted_directories = 0
    for relative_text in scheduled:
        relative = _safe_relative_path(relative_text)
        relative_posix = relative.as_posix()
        if relative_posix not in current_orphans:
            raise WorkspaceMaintenanceError(
                f"待清理目录不再是孤儿目录，请重新审计: {relative_posix}"
            )
        target = (state_root / relative).resolve()
        if (
            not target.is_relative_to(state_root)
            or target == state_root
            or target.parent != state_root / "projects" / "default" / "datasets"
            or is_link_or_reparse_point(target)
        ):
            raise WorkspaceMaintenanceError(f"拒绝清理越界目标: {target}")
        target_files = []
        for path in target.rglob("*"):
            if is_link_or_reparse_point(path):
                raise WorkspaceMaintenanceError(f"清理目标包含符号链接或 reparse point: {path}")
            if path.is_file():
                target_files.append(path)
        missing_from_backup = [
            path.relative_to(state_root).as_posix()
            for path in target_files
            if (
                path.relative_to(state_root).as_posix() not in backed_up_files
                or backed_up_files[path.relative_to(state_root).as_posix()].get("sizeBytes")
                != path.stat().st_size
                or backed_up_files[path.relative_to(state_root).as_posix()].get("sha256")
                != _file_sha256(path)
            )
        ]
        if missing_from_backup:
            raise WorkspaceMaintenanceError(
                "备份未覆盖待清理文件: " + ", ".join(missing_from_backup[:10])
            )
        deleted_files += len(target_files)

        def remove_readonly(function, path, _error_info, root: Path = target) -> None:
            candidate = Path(path).resolve()
            if not candidate.is_relative_to(root):
                raise WorkspaceMaintenanceError(f"拒绝修改清理目标以外的只读路径: {candidate}")
            os.chmod(candidate, stat.S_IWRITE)
            function(path)

        shutil.rmtree(target, onerror=remove_readonly)
        deleted_directories += 1

    return {
        "schemaVersion": "1.0.0",
        "stateRoot": str(state_root),
        "backupPath": str(backup_path.resolve()),
        "deletedDatasetDirectories": deleted_directories,
        "deletedFiles": deleted_files,
        "remainingAudit": audit_workspace(state_root),
    }
