from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile, ZipInfo

from app.services.repository_io import is_link_or_reparse_point


class WorkspaceArchiveError(RuntimeError):
    pass


ARCHIVE_SCHEMA_VERSION = "1.0.0"
MANIFEST_NAME = "backup-manifest.json"
MAX_ARCHIVE_BYTES = 4 * 1024 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 10_000
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_MEMBER_BYTES = 512 * 1024 * 1024
MAX_TOTAL_EXPANDED_BYTES = 2 * 1024 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1_000


def _replace_directory_with_windows_retry(source: Path, destination: Path) -> None:
    for attempt in range(8):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.05 * (2**attempt))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_archive_file_size(path: Path) -> None:
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise WorkspaceArchiveError("备份压缩文件大小超过限制")


def _safe_member_path(name: str) -> PurePosixPath:
    if not isinstance(name, str) or not name or name.endswith("/"):
        raise WorkspaceArchiveError(f"备份包含不安全路径: {name}")
    if "\x00" in name or "\\" in name or ":" in name:
        raise WorkspaceArchiveError(f"备份包含不安全路径: {name}")
    if any(part in {"", ".", ".."} for part in name.split("/")):
        raise WorkspaceArchiveError(f"备份包含不安全路径: {name}")
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise WorkspaceArchiveError(f"备份包含不安全路径: {name}")
    return path


def _bounded_member_bytes(archive: ZipFile, name: str, limit: int) -> bytes:
    info = archive.getinfo(name)
    _validate_member_metadata(info, limit)
    output = bytearray()
    with archive.open(info) as source:
        for chunk in iter(lambda: source.read(min(1024 * 1024, limit + 1 - len(output))), b""):
            output.extend(chunk)
            if len(output) > limit:
                raise WorkspaceArchiveError(f"备份成员超过展开大小限制: {name}")
    return bytes(output)


def _validate_member_metadata(info: ZipInfo, limit: int) -> None:
    name = info.filename
    if info.file_size > limit:
        raise WorkspaceArchiveError(f"备份成员超过展开大小限制: {name}")
    if info.flag_bits & 0x1:
        raise WorkspaceArchiveError(f"备份成员不能加密: {name}")
    if info.compress_type not in {ZIP_STORED, ZIP_DEFLATED}:
        raise WorkspaceArchiveError(f"备份成员使用不支持的压缩算法: {name}")
    compressed = max(info.compress_size, 1)
    if info.file_size / compressed > MAX_COMPRESSION_RATIO:
        raise WorkspaceArchiveError(f"备份成员压缩比过高: {name}")
    if stat.S_ISLNK((info.external_attr >> 16) & 0o170000):
        raise WorkspaceArchiveError(f"备份成员不能是符号链接: {name}")


def _stream_member(
    archive: ZipFile,
    info: ZipInfo,
    *,
    limit: int,
    destination: Path | None = None,
) -> tuple[int, str]:
    _validate_member_metadata(info, limit)
    digest = hashlib.sha256()
    size = 0
    target = destination.open("wb") if destination is not None else None
    try:
        with archive.open(info) as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                size += len(chunk)
                if size > limit:
                    raise WorkspaceArchiveError(f"备份成员超过展开大小限制: {info.filename}")
                digest.update(chunk)
                if target is not None:
                    target.write(chunk)
    finally:
        if target is not None:
            target.close()
    return size, digest.hexdigest()


def _snapshot_database(source: Path, destination: Path) -> int:
    with closing(sqlite3.connect(source)) as source_connection:
        with closing(sqlite3.connect(destination)) as destination_connection:
            source_connection.backup(destination_connection)
        return int(source_connection.execute("PRAGMA user_version").fetchone()[0])


def create_workspace_backup(state_root: Path, archive_path: Path) -> dict[str, Any]:
    state_root = state_root.resolve()
    archive_path = archive_path.resolve()
    if not state_root.is_dir():
        raise WorkspaceArchiveError(f"工作区不存在: {state_root}")
    if archive_path.is_relative_to(state_root):
        raise WorkspaceArchiveError("备份文件不能写入被备份的工作区内部")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        raise WorkspaceArchiveError(f"备份文件已经存在: {archive_path}")

    with tempfile.TemporaryDirectory(prefix="researchpath-backup-") as temporary:
        staging = Path(temporary)
        database_source = state_root / "metadata.sqlite3"
        database_version: int | None = None
        if database_source.exists():
            database_version = _snapshot_database(database_source, staging / "metadata.sqlite3")

        files: list[dict[str, Any]] = []
        for source in sorted(state_root.rglob("*")):
            if is_link_or_reparse_point(source):
                raise WorkspaceArchiveError(f"工作区包含符号链接或 reparse point: {source}")
            if not source.is_file():
                continue
            relative = source.relative_to(state_root)
            if relative.parts[0] == "tmp":
                continue
            if source.name in {"metadata.sqlite3", "metadata.sqlite3-wal", "metadata.sqlite3-shm"}:
                continue
            if source.suffix in {".tmp", ".part"}:
                continue
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        for source in sorted(staging.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(staging).as_posix()
            files.append(
                {
                    "path": relative,
                    "sizeBytes": source.stat().st_size,
                    "sha256": _sha256(source),
                }
            )
        if len(files) + 1 > MAX_ARCHIVE_ENTRIES:
            raise WorkspaceArchiveError("工作区文件数量超过备份限制")
        manifest = {
            "schemaVersion": ARCHIVE_SCHEMA_VERSION,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "databaseUserVersion": database_version,
            "fileCount": len(files),
            "files": files,
        }
        temporary_archive = archive_path.with_suffix(archive_path.suffix + ".tmp")
        try:
            with ZipFile(temporary_archive, "w", compression=ZIP_DEFLATED) as archive:
                archive.writestr(
                    MANIFEST_NAME,
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                )
                for entry in files:
                    archive.write(staging / entry["path"], arcname=entry["path"])
            os.replace(temporary_archive, archive_path)
        finally:
            temporary_archive.unlink(missing_ok=True)
    try:
        verification = verify_workspace_backup(archive_path)
    except Exception:
        archive_path.unlink(missing_ok=True)
        raise
    return {**verification, "archivePath": str(archive_path)}


def verify_workspace_backup(archive_path: Path) -> dict[str, Any]:
    archive_path = archive_path.resolve()
    if not archive_path.is_file():
        raise WorkspaceArchiveError(f"备份文件不存在: {archive_path}")
    _validate_archive_file_size(archive_path)
    try:
        with ZipFile(archive_path) as archive:
            names = archive.namelist()
            if len(names) > MAX_ARCHIVE_ENTRIES:
                raise WorkspaceArchiveError("备份成员数量超过限制")
            if len(names) != len(set(names)):
                raise WorkspaceArchiveError("备份包含重复成员")
            for name in names:
                _safe_member_path(name)
            if MANIFEST_NAME not in names:
                raise WorkspaceArchiveError("备份缺少 manifest")
            manifest_payload = _bounded_member_bytes(archive, MANIFEST_NAME, MAX_MANIFEST_BYTES)
            manifest = json.loads(manifest_payload)
            if manifest.get("schemaVersion") != ARCHIVE_SCHEMA_VERSION:
                raise WorkspaceArchiveError("不支持的备份格式版本")
            entries = manifest.get("files")
            if (
                not isinstance(entries, list)
                or len(entries) > MAX_ARCHIVE_ENTRIES
                or manifest.get("fileCount") != len(entries)
            ):
                raise WorkspaceArchiveError("备份 manifest 文件数量不一致")
            expected_names = {MANIFEST_NAME}
            total_expanded = 0
            for entry in entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                    raise WorkspaceArchiveError("备份 manifest 包含无效文件条目")
                member = _safe_member_path(entry["path"]).as_posix()
                if member in expected_names:
                    raise WorkspaceArchiveError(f"备份 manifest 包含重复文件: {member}")
                expected_names.add(member)
                declared_size = entry.get("sizeBytes")
                if (
                    not isinstance(declared_size, int)
                    or declared_size < 0
                    or declared_size > MAX_MEMBER_BYTES
                ):
                    raise WorkspaceArchiveError(f"备份成员大小不合法: {member}")
                total_expanded += declared_size
                if total_expanded > MAX_TOTAL_EXPANDED_BYTES:
                    raise WorkspaceArchiveError("备份总展开大小超过限制")
                info = archive.getinfo(member)
                actual_size, digest = _stream_member(archive, info, limit=MAX_MEMBER_BYTES)
                if actual_size != entry.get("sizeBytes"):
                    raise WorkspaceArchiveError(f"备份文件大小不一致: {member}")
                if digest != entry.get("sha256"):
                    raise WorkspaceArchiveError(f"备份文件哈希不一致: {member}")
            if set(names) != expected_names:
                raise WorkspaceArchiveError("备份包含未登记成员或缺少已登记文件")
    except (BadZipFile, KeyError, json.JSONDecodeError) as error:
        raise WorkspaceArchiveError(f"备份格式损坏: {error}") from error
    return {
        "valid": True,
        "archiveSha256": _sha256(archive_path),
        "fileCount": manifest["fileCount"],
        "databaseUserVersion": manifest.get("databaseUserVersion"),
        "createdAt": manifest["createdAt"],
    }


def restore_workspace_backup(archive_path: Path, target_root: Path) -> dict[str, Any]:
    verification = verify_workspace_backup(archive_path)
    target_root = target_root.resolve()
    if target_root.exists():
        raise WorkspaceArchiveError(f"恢复目标必须不存在: {target_root}")
    target_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target_root.name}-restore-", dir=target_root.parent))
    try:
        _validate_archive_file_size(archive_path)
        with ZipFile(archive_path) as archive:
            names = archive.namelist()
            if len(names) > MAX_ARCHIVE_ENTRIES or len(names) != len(set(names)):
                raise WorkspaceArchiveError("恢复包成员数量或唯一性不合法")
            for name in names:
                _safe_member_path(name)
            manifest = json.loads(_bounded_member_bytes(archive, MANIFEST_NAME, MAX_MANIFEST_BYTES))
            if manifest.get("schemaVersion") != ARCHIVE_SCHEMA_VERSION:
                raise WorkspaceArchiveError("不支持的备份格式版本")
            entries = manifest.get("files")
            if not isinstance(entries, list) or manifest.get("fileCount") != len(entries):
                raise WorkspaceArchiveError("恢复包 manifest 文件数量不一致")
            expected_names = {MANIFEST_NAME}
            total_expanded = 0
            for entry in manifest["files"]:
                if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                    raise WorkspaceArchiveError("恢复包 manifest 包含无效文件条目")
                relative = _safe_member_path(entry["path"])
                member = relative.as_posix()
                if member in expected_names:
                    raise WorkspaceArchiveError(f"恢复包 manifest 包含重复文件: {member}")
                expected_names.add(member)
                declared_size = entry.get("sizeBytes")
                if not isinstance(declared_size, int) or declared_size < 0:
                    raise WorkspaceArchiveError(f"备份成员大小不合法: {member}")
                total_expanded += declared_size
                if total_expanded > MAX_TOTAL_EXPANDED_BYTES:
                    raise WorkspaceArchiveError("备份总展开大小超过限制")
                staging_root = staging.resolve()
                destination = staging.joinpath(*relative.parts).resolve(strict=False)
                if not destination.is_relative_to(staging_root):
                    raise WorkspaceArchiveError(f"恢复目标越出 staging: {entry['path']}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                actual_size, digest = _stream_member(
                    archive,
                    archive.getinfo(member),
                    limit=MAX_MEMBER_BYTES,
                    destination=destination,
                )
                if actual_size != declared_size or digest != entry.get("sha256"):
                    raise WorkspaceArchiveError(f"恢复成员与 manifest 不一致: {member}")
            if set(names) != expected_names:
                raise WorkspaceArchiveError("恢复包包含未登记成员或缺少已登记文件")
        _replace_directory_with_windows_retry(staging, target_root)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {**verification, "restoredTo": str(target_root)}


def drill_workspace_backup(archive_path: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="researchpath-recovery-drill-") as temporary:
        restored = Path(temporary) / "workspace"
        verification = restore_workspace_backup(archive_path, restored)
        database_path = restored / "metadata.sqlite3"
        database_check: list[str] | None = None
        foreign_key_violations: list[tuple[Any, ...]] | None = None
        if database_path.exists():
            with closing(sqlite3.connect(database_path)) as connection:
                database_check = [str(row[0]) for row in connection.execute("PRAGMA quick_check")]
                foreign_key_violations = [
                    tuple(row) for row in connection.execute("PRAGMA foreign_key_check")
                ]
            if database_check != ["ok"] or foreign_key_violations:
                raise WorkspaceArchiveError("恢复演练后的数据库完整性检查失败")
        return {
            **verification,
            "recoveryDrill": "passed",
            "databaseQuickCheck": database_check,
            "foreignKeyViolations": foreign_key_violations,
        }
