from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.analysis_jobs import AnalysisJobManager


def recover_interrupted_jobs(manager: AnalysisJobManager) -> None:
    """Recover unfinished analysis jobs left behind by a service restart."""
    from app.services.process_ownership import is_process_owned_by_runtime, kill_process_tree

    for state in manager.repository.list_unfinished_analysis_jobs():
        pid = state.get("pid")
        if pid is not None and is_process_owned_by_runtime(int(pid), manager.settings):
            kill_process_tree(int(pid))
        state.update(
            status="failed",
            stage="failed",
            error="分析服务重启，原后台进程已中断；请重新运行。",
        )
        manager._save(state)
