from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "font-src 'self' data:; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


def mount_web_app(application: FastAPI, dist_directory: Path) -> None:
    """Mount the production Vite bundle after API routes."""
    index_path = dist_directory / "index.html"
    if not index_path.is_file():
        raise RuntimeError(
            f"Production web bundle is missing: {index_path}. "
            "Run npm run build:web before starting desktop mode."
        )

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Content-Security-Policy", _CSP)
        return response

    application.mount("/", StaticFiles(directory=dist_directory, html=True), name="web")
