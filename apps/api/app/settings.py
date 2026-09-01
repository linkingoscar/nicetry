from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("researchpath")


@dataclass(frozen=True)
class Settings:
    project_root: Path
    state_root: Path
    model_schema_path: Path
    dataset_schema_path: Path
    measurement_schema_path: Path
    result_schema_path: Path
    demo_model_path: Path
    demo_data_path: Path
    rscript_path: Path
    r_library_path: Path
    r_engine_path: Path
    r_worker_count: int = 1
    r_parallel_workers: int = 8
    analysis_queue_capacity: int = 8
    runtime_tmp_max_age_hours: int = 24
    runtime_runs_max_age_days: int = 30
    serve_web_app: bool = False
    cors_origins: list[str] = field(
        default_factory=lambda: ["http://localhost:5173"],
    )
    session_token: str = field(
        default_factory=lambda: secrets.token_urlsafe(32),
        repr=False,
    )
    session_bootstrap_token: str = field(
        default_factory=lambda: secrets.token_urlsafe(32),
        repr=False,
    )

    @property
    def r_worker_path(self) -> Path:
        return self.project_root / "engine" / "R" / "worker.R"

    @property
    def advanced_result_schema_path(self) -> Path:
        return self.project_root / "specs" / "advanced-result-bundle.schema.json"

    @property
    def empirical_result_schema_path(self) -> Path:
        return self.project_root / "specs" / "empirical-result-bundle.schema.json"

    @property
    def advanced_spec_schema_path(self) -> Path:
        return self.project_root / "specs" / "advanced-analysis-spec.schema.json"


def _bounded_environment_integer(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("环境变量 %s=%r 不是整数，已回退默认值 %d", name, raw, default)
        value = default
    if value < minimum or value > maximum:
        logger.warning("环境变量 %s=%r 超出范围 [%d, %d]，已钳制", name, raw, minimum, maximum)
    return min(max(value, minimum), maximum)


def _environment_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _environment_token(name: str) -> str:
    """Read an auth token and fail closed on empty or trivially short values.

    An empty environment variable must never silently disable the session
    guard (compare_digest("", "") would authorize every tokenless request).
    """
    raw = os.environ.get(name)
    if raw is None:
        return secrets.token_urlsafe(32)
    value = raw.strip()
    if len(value) < 16:
        raise ValueError(
            f"{name} 为空或长度不足 16 个字符；为避免静默关闭会话鉴权，服务拒绝启动"
        )
    return value


def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[3]
    logical_processors = os.cpu_count() or 4
    worker_count = _bounded_environment_integer(
        "RESEARCHPATH_R_WORKERS",
        1,
        1,
        2,
    )
    parallel_workers = _bounded_environment_integer(
        "RESEARCHPATH_R_PARALLEL_WORKERS",
        min(8, max(1, logical_processors // worker_count)),
        1,
        max(1, logical_processors // worker_count),
    )
    queue_capacity = _bounded_environment_integer(
        "RESEARCHPATH_ANALYSIS_QUEUE_CAPACITY",
        8,
        0,
        100,
    )
    tmp_max_age_hours = _bounded_environment_integer(
        "RESEARCHPATH_RUNTIME_TMP_MAX_AGE_HOURS",
        24,
        1,
        24 * 30,
    )
    runs_max_age_days = _bounded_environment_integer(
        "RESEARCHPATH_RUNTIME_RUNS_MAX_AGE_DAYS",
        30,
        1,
        365,
    )
    return Settings(
        project_root=project_root,
        state_root=project_root / ".researchpath" / "workspace",
        model_schema_path=project_root / "specs" / "model-spec.schema.json",
        dataset_schema_path=project_root / "specs" / "dataset-version.schema.json",
        measurement_schema_path=project_root / "specs" / "measurement-version.schema.json",
        result_schema_path=project_root / "specs" / "result-bundle.schema.json",
        demo_model_path=project_root / "examples" / "model-4.example.json",
        demo_data_path=project_root / "samples" / "data" / "mediation-demo.csv",
        rscript_path=project_root / ".runtime" / "R" / "bin" / "Rscript.exe",
        r_library_path=project_root / ".runtime" / "R-library",
        r_engine_path=project_root / "engine" / "R" / "run_analysis.R",
        r_worker_count=worker_count,
        r_parallel_workers=parallel_workers,
        analysis_queue_capacity=queue_capacity,
        runtime_tmp_max_age_hours=tmp_max_age_hours,
        runtime_runs_max_age_days=runs_max_age_days,
        serve_web_app=_environment_flag("RESEARCHPATH_SERVE_WEB"),
        cors_origins=[
            origin.strip()
            for origin in os.environ.get("RESEARCHPATH_CORS_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ],
        session_bootstrap_token=_environment_token("RESEARCHPATH_BOOTSTRAP_TOKEN"),
        session_token=_environment_token("RESEARCHPATH_SESSION_TOKEN"),
    )
