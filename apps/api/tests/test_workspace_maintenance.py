from __future__ import annotations

import json
import os
import sqlite3
import stat
from pathlib import Path

import pytest

from app.services.database_migrations import initialize_database
from app.services.workspace_archive import WorkspaceArchiveError, create_workspace_backup
from app.services.workspace_maintenance import (
    WorkspaceMaintenanceError,
    audit_workspace,
    clean_audited_orphan_datasets,
)


def _workspace_with_orphan(root: Path) -> tuple[Path, Path]:
    state_root = root / "workspace"
    keep = state_root / "projects" / "default" / "datasets" / "dataset_keep"
    orphan = state_root / "projects" / "default" / "datasets" / "dataset_orphan"
    keep.mkdir(parents=True)
    orphan.mkdir(parents=True)
    (keep / "manifest.json").write_text("{}", encoding="utf-8")
    (orphan / "raw.csv").write_text("x\n1\n", encoding="utf-8")
    (orphan / "raw.csv").chmod(stat.S_IREAD)

    database = state_root / "metadata.sqlite3"
    with sqlite3.connect(database) as connection:
        initialize_database(connection)
        connection.execute(
            """
            INSERT INTO dataset_versions (
                id, project_id, created_at, original_name, file_format,
                sha256, manifest_path, row_count, column_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "dataset_keep",
                "default",
                "2026-07-14T00:00:00+00:00",
                "keep.csv",
                "csv",
                "0" * 64,
                "projects/default/datasets/dataset_keep/manifest.json",
                1,
                1,
            ),
        )
    return state_root, orphan


def test_cleanup_requires_reference_audit_and_verified_backup(tmp_path: Path) -> None:
    state_root, orphan = _workspace_with_orphan(tmp_path)
    audit = audit_workspace(state_root)
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(json.dumps(audit), encoding="utf-8")
    backup = tmp_path / "backup.zip"
    create_workspace_backup(state_root, backup)

    result = clean_audited_orphan_datasets(state_root, audit_path, backup)

    assert result["deletedDatasetDirectories"] == 1
    assert result["deletedFiles"] == 1
    assert not orphan.exists()
    assert (state_root / "projects/default/datasets/dataset_keep").is_dir()


def test_cleanup_rejects_database_changed_after_audit(tmp_path: Path) -> None:
    state_root, orphan = _workspace_with_orphan(tmp_path)
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(json.dumps(audit_workspace(state_root)), encoding="utf-8")
    backup = tmp_path / "backup.zip"
    create_workspace_backup(state_root, backup)
    with sqlite3.connect(state_root / "metadata.sqlite3") as connection:
        connection.execute("CREATE TABLE changed_after_audit (id INTEGER)")

    with pytest.raises(WorkspaceMaintenanceError, match="数据库已变化"):
        clean_audited_orphan_datasets(state_root, audit_path, backup)

    assert orphan.is_dir()


def test_cleanup_rejects_file_changed_after_bound_backup(tmp_path: Path) -> None:
    state_root, orphan = _workspace_with_orphan(tmp_path)
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(json.dumps(audit_workspace(state_root)), encoding="utf-8")
    backup = tmp_path / "backup.zip"
    create_workspace_backup(state_root, backup)
    changed = orphan / "raw.csv"
    changed.chmod(stat.S_IWRITE)
    changed.write_text("x\n9\n", encoding="utf-8")

    with pytest.raises(WorkspaceMaintenanceError, match="备份未覆盖"):
        clean_audited_orphan_datasets(state_root, audit_path, backup)

    assert orphan.is_dir()


def test_backup_rejects_link_or_reparse_point(tmp_path: Path) -> None:
    state_root, _ = _workspace_with_orphan(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = state_root / "projects/default/datasets/dataset_orphan/linked.txt"
    try:
        os.symlink(outside, link)
    except OSError as error:
        pytest.skip(f"当前 Windows 配置不允许创建测试符号链接: {error}")

    with pytest.raises(WorkspaceArchiveError, match="符号链接|reparse point"):
        create_workspace_backup(state_root, tmp_path / "backup.zip")
