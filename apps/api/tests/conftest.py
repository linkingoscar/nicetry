from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

import app.settings


# Detect xdist worker ID if running with pytest-xdist
def _get_worker_id(request: pytest.FixtureRequest) -> str:
    if hasattr(request, "config") and hasattr(request.config, "workerinput"):
        return str(request.config.workerinput.get("workerid", "master"))
    return "master"


# Create a temporary directory for the pytest session state root.
_test_dir = tempfile.TemporaryDirectory(prefix="pytest_state_root_")
_test_state_root = Path(_test_dir.name)

_original_get_settings = app.settings.get_settings


def _test_get_settings() -> app.settings.Settings:
    default = _original_get_settings()
    return app.settings.Settings(
        project_root=default.project_root,
        state_root=_test_state_root,
        model_schema_path=default.model_schema_path,
        dataset_schema_path=default.dataset_schema_path,
        measurement_schema_path=default.measurement_schema_path,
        result_schema_path=default.result_schema_path,
        demo_model_path=default.demo_model_path,
        demo_data_path=default.demo_data_path,
        rscript_path=default.rscript_path,
        r_library_path=default.r_library_path,
        r_engine_path=default.r_engine_path,
        r_worker_count=default.r_worker_count,
        # pytest already distributes the statistical suite across isolated
        # processes. Keep each process sequential so the default four-worker
        # harness does not multiply into 4 * os.cpu_count() R processes.
        # Dedicated parallel-runtime tests opt into their own worker counts.
        r_parallel_workers=1,
        analysis_queue_capacity=default.analysis_queue_capacity,
    )


app.settings.get_settings = _test_get_settings

# Import app.main after patching get_settings
import app.main  # noqa: E402

# Overwrite the global app instance in app.main using test_settings
app.main.app = app.main.create_app(_test_get_settings())


@pytest.fixture(scope="session")
def worker_id(request: pytest.FixtureRequest) -> str:
    return _get_worker_id(request)


@pytest.fixture(scope="session")
def worker_storage_root(
    tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest
) -> Path:
    wid = _get_worker_id(request)
    return tmp_path_factory.mktemp(f"storage-{wid}")


@pytest.fixture(scope="session")
def worker_db_path(worker_storage_root: Path, request: pytest.FixtureRequest) -> Path:
    wid = _get_worker_id(request)
    return worker_storage_root / f"test-{wid}.sqlite"


@pytest.fixture(scope="session", autouse=True)
def clean_test_state():
    yield
    try:
        _test_dir.cleanup()
    except Exception:
        pass
