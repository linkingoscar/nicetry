from __future__ import annotations

import os
import time

from app.services.runtime_cleanup import cleanup_expired_runtime


def _touch(path: os.PathLike[str], age_seconds: float) -> None:
    path_str = os.fspath(path)
    with open(path_str, "wb") as handle:
        handle.write(b"x")
    _age(path_str, age_seconds)


def _age(path: str, age_seconds: float) -> None:
    past = time.time() - age_seconds
    os.utime(path, (past, past))


def test_cleanup_removes_only_expired_named_artifacts(tmp_path) -> None:
    state_root = tmp_path / "workspace"
    tmp_root = state_root / "tmp"
    runs_root = state_root / "projects" / "default" / "runs"
    tmp_root.mkdir(parents=True)
    runs_root.mkdir(parents=True)

    stale_upload = tmp_root / "upload-abc123.part"
    fresh_upload = tmp_root / "upload-def456.part"
    foreign_file = tmp_root / "keep-me.txt"
    _touch(stale_upload, 48 * 3600)
    _touch(fresh_upload, 1 * 3600)
    _touch(foreign_file, 48 * 3600)

    stale_run = runs_root / "run_a1b2c3"
    fresh_run = runs_root / "run_d4e5f6"
    foreign_dir = runs_root / "user-notes"
    stale_run.mkdir()
    fresh_run.mkdir()
    foreign_dir.mkdir()
    (stale_run / "result.json").write_text("{}", encoding="utf-8")
    (fresh_run / "result.json").write_text("{}", encoding="utf-8")
    (foreign_dir / "notes.txt").write_text("keep", encoding="utf-8")
    _age(stale_run, 40 * 86400)
    _age(fresh_run, 1 * 86400)
    _age(foreign_dir, 40 * 86400)

    result = cleanup_expired_runtime(
        state_root,
        tmp_max_age_hours=24,
        runs_max_age_days=30,
    )

    assert result == {"tmpFiles": 1, "runDirectories": 1}
    assert not stale_upload.exists()
    assert fresh_upload.exists()
    assert foreign_file.exists()
    assert not stale_run.exists()
    assert fresh_run.exists()
    assert foreign_dir.exists()


def test_cleanup_tolerates_missing_roots(tmp_path) -> None:
    result = cleanup_expired_runtime(
        tmp_path / "absent",
        tmp_max_age_hours=24,
        runs_max_age_days=30,
    )
    assert result == {"tmpFiles": 0, "runDirectories": 0}
