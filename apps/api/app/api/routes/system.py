from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse

from app.api.dependencies import ApiServices, get_services
from app.api.responses import (
    DemoProjectRequest,
    DemoProjectResponse,
    DemoResponse,
    HealthResponse,
    SessionBootstrapRequest,
    SessionResponse,
)
from app.contracts import load_json
from app.services.dataset_import import DatasetImportError
from app.services.dataset_repository import DictionaryUpdateError
from app.services.demo_project import DemoProjectError, load_demo_project
from app.services.measurement import MeasurementError

router = APIRouter(tags=["system"])

_r_probe_cache: tuple[float, bool] | None = None
_R_PROBE_TTL_SECONDS = 60


def _r_executable_ready(rscript: Path) -> bool:
    """Probe Rscript once per TTL; failures never raise so health stays available."""
    global _r_probe_cache
    now = time.monotonic()
    if _r_probe_cache is not None and now - _r_probe_cache[0] < _R_PROBE_TTL_SECONDS:
        return _r_probe_cache[1]
    try:
        result = subprocess.run(
            [str(rscript), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        ready = result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ready = False
    _r_probe_cache = (now, ready)
    return ready


@router.post("/session/bootstrap", response_model=SessionResponse)
def bootstrap_session(
    body: SessionBootstrapRequest,
    request: Request,
    response: Response,
) -> dict[str, str]:
    response.headers["Cache-Control"] = "no-store"
    token = request.app.state.session_bootstrap.exchange(body.bootstrapToken)
    if token is None:
        raise HTTPException(status_code=403, detail="会话启动凭据无效或已使用")
    return {
        "token": token,
        "headerName": "X-ResearchPath-Token",
    }


@router.get("/health", response_model=HealthResponse)
def health(request: Request, services: ApiServices = Depends(get_services)) -> dict[str, Any]:
    rscript = services.settings.rscript_path
    r_available = rscript.exists()
    disk = shutil.disk_usage(services.settings.state_root)
    return {
        "status": "ok",
        "apiVersion": request.app.version,
        "rAvailable": r_available,
        "rExecutable": r_available and _r_executable_ready(rscript),
        "diskFreeBytes": disk.free,
        "diskFreePercent": round(disk.free / disk.total * 100, 1),
    }


@router.get("/demo", response_model=DemoResponse)
def demo(services: ApiServices = Depends(get_services)) -> dict[str, Any]:
    return {
        "datasetId": "mediation-demo",
        "datasetLabel": "合成问卷单一中介示例",
        "modelSpec": load_json(services.settings.demo_model_path),
    }


@router.post(
    "/demo/load",
    status_code=status.HTTP_201_CREATED,
    response_model=DemoProjectResponse,
)
def create_demo_project(
    body: DemoProjectRequest | None = None,
    services: ApiServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        return load_demo_project(
            services.dataset_repository,
            services.settings,
            (body or DemoProjectRequest()).timeStructure,
        )
    except DemoProjectError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (DatasetImportError, DictionaryUpdateError, MeasurementError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/demo/data/{kind}", response_class=FileResponse)
def download_method_demo_data(
    kind: Literal["longitudinal", "diary", "esm"],
    services: ApiServices = Depends(get_services),
) -> FileResponse:
    filename = {
        "longitudinal": "longitudinal-panel-demo.csv",
        "diary": "daily-diary-demo.csv",
        "esm": "intensive-esm-demo.csv",
    }[kind]
    path = services.settings.project_root / "samples" / "data" / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="示例数据不存在")
    return FileResponse(path, media_type="text/csv", filename=filename)
