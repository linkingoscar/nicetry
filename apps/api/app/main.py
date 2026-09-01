from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import ApiServices
from app.api.routes import ROUTERS
from app.api.session_middleware import session_guard
from app.error_handlers import register_error_handlers
from app.services.advanced_jobs import AdvancedJobManager
from app.services.analysis_context import AnalysisContextService
from app.services.analysis_jobs import AnalysisJobManager
from app.services.capability_applicability import applicable_capability_registry
from app.services.dataset_repository import DatasetRepository
from app.services.r_workers import RWorkerPool, RWorkerUnavailable
from app.services.runtime_cleanup import startup_cleanup
from app.services.session_bootstrap import SessionBootstrap
from app.services.workflow_services import WorkflowServices
from app.settings import Settings, get_settings
from app.web_static import mount_web_app

logger = logging.getLogger("researchpath")
def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    repository = DatasetRepository(resolved_settings)
    r_worker_pool = RWorkerPool(resolved_settings)
    context_service = AnalysisContextService(repository)
    services = ApiServices(settings=resolved_settings, dataset_repository=repository, analysis_context_service=context_service, workflow_services=WorkflowServices.build(repository, context_service, applicable_capability_registry), capability_applicability_service=applicable_capability_registry, analysis_job_manager=AnalysisJobManager(repository, resolved_settings, r_worker_pool, context_service), advanced_job_manager=AdvancedJobManager(repository, resolved_settings, context_service, applicable_capability_registry), r_worker_pool=r_worker_pool)
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        startup_cleanup(resolved_settings)
        try:
            r_worker_pool.start()
            logger.info("R Worker Pool 启动成功 (%d workers)", resolved_settings.r_worker_count)
        except RWorkerUnavailable as error:
            logger.warning(
                "R Worker Pool 启动失败，已降级至 Rscript 子进程模式: %s | Rscript 路径: %s | 是否存在: %s",
                error,
                resolved_settings.rscript_path,
                resolved_settings.rscript_path.exists(),
            )
        try:
            yield
        finally:
            services.analysis_job_manager.close()
            services.advanced_job_manager.close()
            r_worker_pool.close()
    application = FastAPI(
        title="ResearchPath Local API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    application.state.services = services
    application.state.session_bootstrap = SessionBootstrap(resolved_settings.session_bootstrap_token, resolved_settings.session_token)
    register_error_handlers(application)
    @application.middleware("http")
    async def require_session_token(request: Request, call_next):
        guard = session_guard(request, resolved_settings)
        if guard is not None:
            return guard
        return await call_next(request)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-ResearchPath-Token"],
    )
    for router in ROUTERS:
        application.include_router(router, prefix="/api/v1")
    if resolved_settings.serve_web_app:
        mount_web_app(application, resolved_settings.project_root / "apps" / "web" / "dist")
    return application

app = create_app()
