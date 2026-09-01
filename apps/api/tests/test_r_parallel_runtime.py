from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from app.services import r_engine
from app.services.r_engine import EngineExecutionError, run_mediation
from app.services.r_workers import (
    RWorkerCancelled,
    RWorkerPool,
    RWorkerTaskError,
    RWorkerUnavailable,
)
from app.settings import get_settings

# These tests create and benchmark their own resident R worker pools. Running
# them inside the outer xdist pool would measure unrelated suite contention
# rather than the worker concurrency/resource budgets they are designed to
# verify. scripts/test.ps1 executes this module in the dedicated serial lane.
pytestmark = pytest.mark.serial


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.wintypes.DWORD),
        ("page_fault_count", ctypes.wintypes.DWORD),
        ("peak_working_set_size", ctypes.c_size_t),
        ("working_set_size", ctypes.c_size_t),
        ("quota_peak_paged_pool_usage", ctypes.c_size_t),
        ("quota_paged_pool_usage", ctypes.c_size_t),
        ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
        ("quota_non_paged_pool_usage", ctypes.c_size_t),
        ("pagefile_usage", ctypes.c_size_t),
        ("peak_pagefile_usage", ctypes.c_size_t),
    ]


def _windows_process_metrics(pid: int) -> dict[str, int]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.OpenProcess.argtypes = [
        ctypes.wintypes.DWORD,
        ctypes.wintypes.BOOL,
        ctypes.wintypes.DWORD,
    ]
    kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
    kernel32.GetProcessHandleCount.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.POINTER(ctypes.wintypes.DWORD),
    ]
    kernel32.GetProcessHandleCount.restype = ctypes.wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCounters),
        ctypes.wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = ctypes.wintypes.BOOL

    process_query_information = 0x0400
    process_vm_read = 0x0010
    handle = kernel32.OpenProcess(
        process_query_information | process_vm_read,
        False,
        int(pid),
    )
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        handle_count = ctypes.wintypes.DWORD()
        if not kernel32.GetProcessHandleCount(handle, ctypes.byref(handle_count)):
            raise ctypes.WinError(ctypes.get_last_error())
        memory = _ProcessMemoryCounters()
        memory.cb = ctypes.sizeof(memory)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(memory), memory.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return {
            "handles": int(handle_count.value),
            "workingSet": int(memory.working_set_size),
        }
    finally:
        kernel32.CloseHandle(handle)


def test_resident_worker_is_reused_and_reports_runtime_mode() -> None:
    settings = replace(get_settings(), r_worker_count=1, r_parallel_workers=1)
    model = json.loads(settings.demo_model_path.read_text(encoding="utf-8"))
    model["estimation"]["bootstrap"]["replicates"] = 100
    pool = RWorkerPool(settings)
    try:
        pool.start()
        pid = pool._workers[0].process.pid
        first = run_mediation(model, settings.demo_data_path, settings, pool)
        second = run_mediation(model, settings.demo_data_path, settings, pool)
        assert pool._workers[0].process.pid == pid
        assert first["effects"] == second["effects"]
        assert second["provenance"]["executionMode"] == "resident_pool"
        assert second["provenance"]["parallelBackend"] == "sequential"
    finally:
        pool.close()
    assert pool._workers == []


def test_repeated_resident_runs_release_processes_and_temporary_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = replace(get_settings(), r_worker_count=1, r_parallel_workers=1)
    model = json.loads(settings.demo_model_path.read_text(encoding="utf-8"))
    model["estimation"]["bootstrap"]["replicates"] = 25
    temporary_root = tmp_path / "engine-temporary"
    temporary_root.mkdir()
    monkeypatch.setattr(r_engine.tempfile, "tempdir", str(temporary_root))
    before = {path.resolve() for path in temporary_root.glob("researchpath-*")}
    pool = RWorkerPool(settings)
    processes = []
    try:
        pool.start()
        processes = [worker.process for worker in pool._workers]
        worker_pid = processes[0].pid
        for _ in range(10):
            result = run_mediation(model, settings.demo_data_path, settings, pool)
            assert result["run"]["status"] == "succeeded"
            assert pool._workers[0].process.pid == worker_pid
    finally:
        pool.close()

    after = {path.resolve() for path in temporary_root.glob("researchpath-*")}
    assert after <= before
    assert all(process.poll() is not None for process in processes)


def test_crashed_worker_is_replaced_and_request_falls_back_to_rscript() -> None:
    settings = replace(get_settings(), r_worker_count=1, r_parallel_workers=1)
    model = json.loads(settings.demo_model_path.read_text(encoding="utf-8"))
    model["estimation"]["bootstrap"]["replicates"] = 100
    pool = RWorkerPool(settings)
    try:
        pool.start()
        crashed_pid = pool._workers[0].process.pid
        pool._workers[0].terminate()

        fallback = run_mediation(model, settings.demo_data_path, settings, pool)
        replacement_pid = pool._workers[0].process.pid
        resident = run_mediation(model, settings.demo_data_path, settings, pool)

        assert replacement_pid != crashed_pid
        assert fallback["provenance"]["executionMode"] == "rscript"
        assert resident["provenance"]["executionMode"] == "resident_pool"
    finally:
        pool.close()


def test_translate_r_error_does_not_leak_local_paths_or_raw_stderr() -> None:
    raw = (
        "Error in read.csv('C:\\Users\\someone\\Documents\\data.csv'): "
        "cannot open file 'C:\\Users\\someone\\Documents\\data.csv'"
    )
    translated = r_engine.translate_r_error(raw)
    assert "C:\\Users" not in translated
    assert "原始诊断" in translated
    binary = r_engine.translate_r_error("BINARY_MEDIATOR_NOT_SUPPORTED: m1")
    assert "BINARY_MEDIATOR_NOT_SUPPORTED" in binary
    assert "logit" in binary


def test_worker_preserves_original_task_error_instead_of_cancel_path_lookup(
    tmp_path,
) -> None:
    settings = replace(get_settings(), r_worker_count=1, r_parallel_workers=1)
    script = tmp_path / "failing.R"
    script.write_text('stop("task exploded with original error")\n', encoding="utf-8")
    input_path = tmp_path / "input.json"
    input_path.write_text("{}", encoding="utf-8")
    pool = RWorkerPool(settings)
    try:
        pool.start()
        with pytest.raises(RWorkerTaskError, match="task exploded with original error") as error:
            pool.run(
                script_path=script,
                input_path=input_path,
                output_path=tmp_path / "output.json",
                log_path=tmp_path / "worker.log",
                cancel_path=tmp_path / "cancel",
                timeout=10,
            )
        assert "cancel_path" not in str(error.value)
    finally:
        pool.close()


def test_worker_reports_cancellation_when_task_raises_cancel_code(tmp_path) -> None:
    settings = replace(get_settings(), r_worker_count=1, r_parallel_workers=1)
    script = tmp_path / "cancelled.R"
    script.write_text('stop("ANALYSIS_CANCELLED")\n', encoding="utf-8")
    input_path = tmp_path / "input.json"
    input_path.write_text("{}", encoding="utf-8")
    pool = RWorkerPool(settings)
    try:
        pool.start()
        with pytest.raises(RWorkerCancelled):
            pool.run(
                script_path=script,
                input_path=input_path,
                output_path=tmp_path / "output.json",
                log_path=tmp_path / "worker.log",
                cancel_path=tmp_path / "cancel",
                timeout=10,
            )
    finally:
        pool.close()


def test_cancelled_uncooperative_task_replaces_worker(tmp_path) -> None:
    settings = replace(get_settings(), r_worker_count=1, r_parallel_workers=1)
    script = tmp_path / "uncooperative.R"
    script.write_text("Sys.sleep(30)\n", encoding="utf-8")
    input_path = tmp_path / "input.json"
    input_path.write_text("{}", encoding="utf-8")
    pool = RWorkerPool(settings)
    cancel_event = threading.Event()
    try:
        pool.start()
        original_pid = pool._workers[0].process.pid
        timer = threading.Timer(0.2, cancel_event.set)
        timer.start()
        try:
            try:
                pool.run(
                    script_path=script,
                    input_path=input_path,
                    output_path=tmp_path / "output.json",
                    log_path=tmp_path / "worker.log",
                    cancel_event=cancel_event,
                    cancel_path=tmp_path / "cancel",
                    timeout=10,
                )
            except RWorkerCancelled:
                pass
            else:
                raise AssertionError("uncooperative task was not cancelled")
        finally:
            timer.cancel()
        assert not pool._workers
        pool._repair_capacity()
        assert pool._workers[0].process.pid != original_pid
    finally:
        pool.close()


def test_two_resident_workers_execute_concurrently(tmp_path) -> None:
    settings = replace(get_settings(), r_worker_count=2, r_parallel_workers=1)
    script = tmp_path / "echo.R"
    script.write_text(
        "args <- commandArgs(trailingOnly = TRUE)\n"
        "Sys.sleep(0.25)\n"
        "jsonlite::write_json(list(ok = TRUE), args[[2]], auto_unbox = TRUE)\n",
        encoding="utf-8",
    )
    pool = RWorkerPool(settings)

    def execute(index: int) -> dict[str, bool]:
        input_path = tmp_path / f"input-{index}.json"
        output_path = tmp_path / f"output-{index}.json"
        input_path.write_text("{}", encoding="utf-8")
        pool.run(
            script_path=script,
            input_path=input_path,
            output_path=output_path,
            log_path=tmp_path / f"worker-{index}.log",
        )
        return json.loads(output_path.read_text(encoding="utf-8"))

    try:
        pool.start()
        pids = {worker.process.pid for worker in pool._workers}
        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(execute, range(2)))
        elapsed = time.monotonic() - started
        assert len(pids) == 2
        assert results == [{"ok": True}, {"ok": True}]
        assert elapsed < 1.0
    finally:
        pool.close()


def test_future_parallel_analysis_and_htmt_are_worker_count_invariant(tmp_path) -> None:
    settings = get_settings()
    script = tmp_path / "parallel-invariance.R"
    result_path = tmp_path / "parallel-invariance.json"
    parallel_path = (settings.project_root / "engine/R/lib/parallel.R").as_posix()
    budget_path = (settings.project_root / "engine/R/lib/resource_budget.R").as_posix()
    seed_utils_path = (settings.project_root / "engine/R/lib/seed_utils.R").as_posix()
    efa_path = (settings.project_root / "engine/R/lib/efa.R").as_posix()
    validity_path = (settings.project_root / "engine/R/lib/validity.R").as_posix()
    script.write_text(
        f"""
        suppressPackageStartupMessages(library(jsonlite))
        source({json.dumps(parallel_path)})
        source({json.dumps(budget_path)})
        source({json.dumps(seed_utils_path)})
        source({json.dumps(efa_path)})
        source({json.dumps(validity_path)})
        Sys.setenv(RESEARCHPATH_PARALLEL_MIN_WORK_UNITS = "0")
        set.seed(99)
        data <- as.data.frame(matrix(rnorm(2400), nrow = 200, ncol = 12))
        names(data) <- paste0("item", seq_len(12))
        constructs <- lapply(seq_len(3), function(index) list(
          itemIds = as.list(names(data)[((index - 1) * 4 + 1):(index * 4)])
        ))
        Sys.setenv(RESEARCHPATH_PARALLEL_WORKERS = "1")
        pa_one <- run_parallel_analysis(data, iterations = 80, seed = 271828)
        htmt_one <- htmt_bootstrap(data, constructs, reps = 80, seed = 314159)
        Sys.setenv(RESEARCHPATH_PARALLEL_WORKERS = "4")
        pa_four <- run_parallel_analysis(data, iterations = 80, seed = 271828)
        htmt_four <- htmt_bootstrap(data, constructs, reps = 80, seed = 314159)
        stopifnot(identical(pa_one$simulatedEigenvalues, pa_four$simulatedEigenvalues))
        stopifnot(isTRUE(all.equal(htmt_one$lower, htmt_four$lower, tolerance = 0)))
        stopifnot(isTRUE(all.equal(htmt_one$upper, htmt_four$upper, tolerance = 0)))
        stopifnot(identical(pa_four$parallelBackend, "future_multisession"))
        stopifnot(identical(htmt_four$parallelBackend, "future_multisession"))
        write_json(list(ok = TRUE), {json.dumps(result_path.as_posix())}, auto_unbox = TRUE)
        future::plan(future::sequential)
        """,
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment.update(
        {
            "R_LIBS_USER": str(settings.r_library_path),
            "LC_ALL": "English_United States.utf8",
        }
    )
    completed = subprocess.run(
        [str(settings.rscript_path), "--vanilla", str(script)],
        cwd=settings.project_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert json.loads(result_path.read_text(encoding="utf-8")) == {"ok": True}


def test_rscript_fallback_cannot_restart_an_expired_resident_deadline(
    tmp_path, monkeypatch
) -> None:
    data_path = tmp_path / "data.csv"
    data_path.write_text("x,y\n1,2\n", encoding="utf-8")

    class ExpiredPool:
        def run(self, **_kwargs):
            raise RWorkerUnavailable("resident timed out")

    clock = iter([0.0, 0.0, 181.0])
    monkeypatch.setattr(r_engine.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(
        r_engine.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("expired work must not fall back"),
    )

    with pytest.raises(EngineExecutionError, match="总执行期限"):
        r_engine._execute_analysis(
            {"modelId": "model_a"},
            data_path,
            get_settings(),
            "model_a_v1",
            worker_pool=ExpiredPool(),  # type: ignore[arg-type]
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows resource counters")
def test_resident_worker_soak_stays_within_handle_memory_and_temp_budgets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = replace(get_settings(), r_worker_count=1, r_parallel_workers=1)
    model = json.loads(settings.demo_model_path.read_text(encoding="utf-8"))
    model["estimation"]["bootstrap"]["replicates"] = 25
    temporary_root = tmp_path / "engine-temporary"
    temporary_root.mkdir()
    # The full suite runs in xdist workers. Scope this ownership assertion to
    # r_engine's temporary root, so another test cannot look like a resource
    # leak merely by creating an unrelated system-temporary directory.
    monkeypatch.setattr(r_engine.tempfile, "tempdir", str(temporary_root))
    pool = RWorkerPool(settings)

    try:
        pool.start()
        run_mediation(model, settings.demo_data_path, settings, worker_pool=pool)
        pid = pool._workers[0].process.pid
        before_metrics = _windows_process_metrics(pid)
        before_temporary = {path.name for path in temporary_root.glob("researchpath-*")}

        for _ in range(20):
            result = run_mediation(
                model,
                settings.demo_data_path,
                settings,
                worker_pool=pool,
            )
            assert result["run"]["status"] == "succeeded"
            assert pool._workers[0].process.pid == pid

        after_metrics = _windows_process_metrics(pid)
        after_temporary = {path.name for path in temporary_root.glob("researchpath-*")}
        assert after_metrics["handles"] - before_metrics["handles"] <= 24
        assert after_metrics["workingSet"] - before_metrics["workingSet"] <= 96 * 1024 * 1024
        assert after_temporary <= before_temporary
    finally:
        pool.close()
