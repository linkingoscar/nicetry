from unittest.mock import MagicMock, patch

from app.services.advanced_jobs import AdvancedJobManager


def test_recover_interrupted_jobs():
    mock_repository = MagicMock()
    # 模拟有一个带 PID 和一个不带 PID 的未完成任务
    mock_repository.list_unfinished_advanced_jobs.return_value = [
        {"id": "job_1", "status": "running"},
        {"id": "job_2", "status": "running", "pid": 99999},
    ]

    mock_settings = MagicMock()
    mock_settings.r_worker_count = 2
    mock_settings.analysis_queue_capacity = 2

    # Patch subprocess.run
    with patch("subprocess.run") as mock_run:
        with patch("os.name", "nt"):
            AdvancedJobManager(mock_repository, mock_settings)

            # _recover_interrupted_jobs 会在 __init__ 被调用
            # 应该只有 job_2 有 PID，会被尝试 taskkill
            mock_run.assert_called_once_with(
                ["taskkill", "/F", "/T", "/PID", "99999"], capture_output=True
            )

            # 断言 save 被调用两次，状态皆为 failed
            assert mock_repository.save_advanced_job.call_count == 2
            args_list = mock_repository.save_advanced_job.call_args_list
            job1_state = args_list[0][0][0]
            job2_state = args_list[1][0][0]

            assert job1_state["status"] == "failed"
            assert job1_state["error"] == "分析服务重启，原后台进程已中断；请重新运行。"

            assert job2_state["status"] == "failed"
            assert job2_state["error"] == "分析服务重启，原后台进程已中断；请重新运行。"
