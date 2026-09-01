from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = PROJECT_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.r_engine import run_mediation  # noqa: E402
from app.services.r_workers import RWorkerPool  # noqa: E402
from app.settings import get_settings  # noqa: E402


def elapsed_seconds(action: Callable[[], Any]) -> tuple[float, Any]:
    started = time.perf_counter()
    result = action()
    return time.perf_counter() - started, result


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def duration_summary(seconds: list[float]) -> dict[str, Any]:
    return {
        "runs": len(seconds),
        "valuesMs": [round(value * 1000, 3) for value in seconds],
        "medianMs": round(statistics.median(seconds) * 1000, 3),
        "p95Ms": round(percentile(seconds, 0.95) * 1000, 3),
    }


def measure_rscript_startup(settings: Any, runs: int) -> list[float]:
    environment = os.environ.copy()
    environment.update(
        {
            "R_LIBS_USER": str(settings.r_library_path),
            "LC_ALL": "English_United States.utf8",
        }
    )
    command = [
        str(settings.rscript_path),
        "--vanilla",
        "-e",
        "suppressPackageStartupMessages(library(lavaan));"
        "suppressPackageStartupMessages(library(jsonlite))",
    ]
    durations: list[float] = []
    for _ in range(runs):
        started = time.perf_counter()
        subprocess.run(
            command,
            cwd=settings.project_root,
            env=environment,
            capture_output=True,
            check=True,
            timeout=30,
        )
        durations.append(time.perf_counter() - started)
    return durations


def make_large_dataset(source: Path, destination: Path, rows: int) -> None:
    with source.open("r", encoding="utf-8", newline="") as source_file:
        records = list(csv.DictReader(source_file))
        fieldnames = list(records[0])
    with destination.open("w", encoding="utf-8", newline="") as destination_file:
        writer = csv.DictWriter(destination_file, fieldnames=fieldnames)
        writer.writeheader()
        for index in range(rows):
            writer.writerow(records[index % len(records)])


def model_with_replicates(model: dict[str, Any], replicates: int) -> dict[str, Any]:
    copied = json.loads(json.dumps(model))
    copied["estimation"]["bootstrap"]["replicates"] = replicates
    return copied


def numeric_signature(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "effects": result.get("effects"),
        "modelSummary": result.get("modelSummary"),
        "regressions": result.get("regressions"),
        "sampleFlow": result.get("sampleFlow"),
    }


def run_pool_analysis(
    settings: Any,
    model: dict[str, Any],
    data_path: Path,
) -> tuple[float, dict[str, Any], float, list[int], bool]:
    pool = RWorkerPool(settings)
    workers = []
    try:
        startup_seconds, _ = elapsed_seconds(pool.start)
        workers = list(pool._workers)
        warmup = model_with_replicates(model, 100)
        run_mediation(warmup, data_path, settings, pool)
        duration, result = elapsed_seconds(lambda: run_mediation(model, data_path, settings, pool))
        pids = [worker.process.pid for worker in workers]
    finally:
        pool.close()
    all_stopped = all(worker.process.poll() is not None for worker in workers)
    return duration, result, startup_seconds, pids, all_stopped


def collect_r_version(settings: Any) -> str:
    environment = os.environ.copy()
    environment["R_LIBS_USER"] = str(settings.r_library_path)
    completed = subprocess.run(
        [str(settings.rscript_path), "--vanilla", "-e", "cat(R.version.string)"],
        cwd=settings.project_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        timeout=30,
    )
    return completed.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark ResearchPath R runtime")
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--replicates", type=int, default=5000)
    parser.add_argument("--latency-runs", type=int, default=5)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output/performance/r-runtime-baseline.json",
    )
    args = parser.parse_args()
    if args.rows < 100 or args.replicates < 100 or args.latency_runs < 1:
        parser.error("rows and replicates must be >=100; latency-runs must be >=1")

    settings = get_settings()
    parallel_workers = max(2, min(8, os.cpu_count() or 2))
    model = json.loads(settings.demo_model_path.read_text(encoding="utf-8"))
    latency_model = model_with_replicates(model, 100)
    cold_start = measure_rscript_startup(settings, args.latency_runs)

    direct_durations: list[float] = []
    direct_result: dict[str, Any] | None = None
    for _ in range(args.latency_runs):
        duration, direct_result = elapsed_seconds(
            lambda: run_mediation(
                latency_model, settings.demo_data_path, settings, worker_pool=None
            )
        )
        direct_durations.append(duration)

    resident_settings = replace(settings, r_worker_count=1, r_parallel_workers=1)
    resident_pool = RWorkerPool(resident_settings)
    resident_durations: list[float] = []
    resident_result: dict[str, Any] | None = None
    resident_workers = []
    try:
        resident_startup, _ = elapsed_seconds(resident_pool.start)
        resident_workers = list(resident_pool._workers)
        run_mediation(
            latency_model,
            resident_settings.demo_data_path,
            resident_settings,
            resident_pool,
        )
        for _ in range(args.latency_runs):
            duration, resident_result = elapsed_seconds(
                lambda: run_mediation(
                    latency_model,
                    resident_settings.demo_data_path,
                    resident_settings,
                    resident_pool,
                )
            )
            resident_durations.append(duration)
    finally:
        resident_pool.close()
    resident_stopped = all(worker.process.poll() is not None for worker in resident_workers)

    with tempfile.TemporaryDirectory(prefix="researchpath-r-benchmark-") as temp_dir:
        large_data_path = Path(temp_dir) / "large-mediation.csv"
        make_large_dataset(settings.demo_data_path, large_data_path, args.rows)
        heavy_model = model_with_replicates(model, args.replicates)
        sequential = run_pool_analysis(
            replace(settings, r_worker_count=1, r_parallel_workers=1),
            heavy_model,
            large_data_path,
        )
        parallel = run_pool_analysis(
            replace(
                settings,
                r_worker_count=1,
                r_parallel_workers=parallel_workers,
            ),
            heavy_model,
            large_data_path,
        )

    sequential_seconds, sequential_result, sequential_startup, sequential_pids, seq_stop = (
        sequential
    )
    parallel_seconds, parallel_result, parallel_startup, parallel_pids, parallel_stop = parallel
    speedup = sequential_seconds / parallel_seconds
    numeric_equal = numeric_signature(sequential_result) == numeric_signature(parallel_result)
    latency_equal = (
        direct_result is not None
        and resident_result is not None
        and numeric_signature(direct_result) == numeric_signature(resident_result)
    )

    report = {
        "schemaVersion": "1.0.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "logicalCpuCount": os.cpu_count(),
            "pythonVersion": platform.python_version(),
            "rVersion": collect_r_version(settings),
        },
        "configuration": {
            "sampleRows": args.rows,
            "bootstrapReplicates": args.replicates,
            "parallelWorkers": parallel_workers,
            "latencyRuns": args.latency_runs,
            "randomSeed": model["estimation"]["bootstrap"]["seed"],
        },
        "coldStart": {
            "operation": "new Rscript loading lavaan and jsonlite",
            **duration_summary(cold_start),
        },
        "interactiveLatency": {
            "operation": "Model 4 with 100 bootstrap replicates",
            "rscript": duration_summary(direct_durations),
            "residentWorker": duration_summary(resident_durations),
            "residentPoolStartupMs": round(resident_startup * 1000, 3),
            "medianTimeSavedMs": round(
                (statistics.median(direct_durations) - statistics.median(resident_durations))
                * 1000,
                3,
            ),
            "numericEquivalent": latency_equal,
            "workersStoppedAfterClose": resident_stopped,
        },
        "heavyBootstrap": {
            "sequential": {
                "durationMs": round(sequential_seconds * 1000, 3),
                "poolStartupMs": round(sequential_startup * 1000, 3),
                "workerPids": sequential_pids,
            },
            "parallel": {
                "durationMs": round(parallel_seconds * 1000, 3),
                "poolStartupMs": round(parallel_startup * 1000, 3),
                "workerPids": parallel_pids,
            },
            "speedup": round(speedup, 3),
            "targetSpeedup": 3.0,
            "targetMet": speedup >= 3.0,
            "numericEquivalent": numeric_equal,
            "workersStoppedAfterClose": seq_stop and parallel_stop,
        },
        "passed": all(
            [
                latency_equal,
                resident_stopped,
                numeric_equal,
                seq_stop,
                parallel_stop,
                speedup >= 3.0,
            ]
        ),
    }
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Benchmark report: {output_path}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
