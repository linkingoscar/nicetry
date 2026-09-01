from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from app.services.repository_io import remove_path_tree
from app.settings import Settings

logger = logging.getLogger("researchpath")

_RUN_DIR_PATTERN = re.compile(r"^(run|advanced)_[a-f0-9]+$")
_TMP_FILE_PATTERN = re.compile(r"^(upload-|\.).*\.part$")


def startup_cleanup(settings: Settings) -> None:
    """启动时的一次性清理：失败只记录日志，不中断启动。"""
    try:
        result = cleanup_expired_runtime(
            settings.state_root,
            tmp_max_age_hours=settings.runtime_tmp_max_age_hours,
            runs_max_age_days=settings.runtime_runs_max_age_days,
        )
        if result["tmpFiles"] or result["runDirectories"]:
            logger.info("Runtime cleanup removed: %s", result)
    except Exception:
        logger.exception("Runtime cleanup failed")


def cleanup_expired_runtime(
    state_root: Path,
    *,
    tmp_max_age_hours: int,
    runs_max_age_days: int,
) -> dict[str, int]:
    """清理过期的上传残留与 runs 结果目录。

    仅处理服务端命名约定的直接子项（tmp 的 `upload-*.part` 与 runs 的
    `run_*`/`advanced_*`），不递归删除其他数据；单项失败不影响其余清理，
    也不会抛出异常中断启动。
    """
    now = time.time()
    removed_tmp = 0
    removed_runs = 0

    tmp_root = state_root / "tmp"
    if tmp_root.is_dir():
        tmp_cutoff = now - tmp_max_age_hours * 3600
        for entry in tmp_root.iterdir():
            try:
                if (
                    entry.is_file()
                    and _TMP_FILE_PATTERN.match(entry.name)
                    and entry.stat().st_mtime < tmp_cutoff
                ):
                    entry.unlink()
                    removed_tmp += 1
            except OSError:
                continue

    runs_root = state_root / "projects" / "default" / "runs"
    if runs_root.is_dir():
        runs_cutoff = now - runs_max_age_days * 86400
        for entry in runs_root.iterdir():
            try:
                if (
                    entry.is_dir()
                    and _RUN_DIR_PATTERN.match(entry.name)
                    and entry.stat().st_mtime < runs_cutoff
                ):
                    remove_path_tree(entry)
                    removed_runs += 1
            except OSError:
                continue

    return {"tmpFiles": removed_tmp, "runDirectories": removed_runs}
