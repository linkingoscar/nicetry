from app.api.routes.advanced import router as advanced_router
from app.api.routes.analyses import router as analyses_router
from app.api.routes.datasets import router as datasets_router
from app.api.routes.models import router as models_router
from app.api.routes.studies import router as studies_router
from app.api.routes.system import router as system_router
from app.api.routes.workflows import router as workflows_router

ROUTERS = (
    system_router,
    datasets_router,
    models_router,
    analyses_router,
    advanced_router,
    studies_router,
    workflows_router,
)

__all__ = ["ROUTERS"]
