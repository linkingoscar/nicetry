from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.web_static import mount_web_app


def test_mount_web_app_serves_production_assets_after_api_routes(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>ResearchPath</h1>", encoding="utf-8")
    (dist / "asset.js").write_text("window.ready = true;", encoding="utf-8")
    application = FastAPI()

    @application.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    mount_web_app(application, dist)

    with TestClient(application) as client:
        assert client.get("/").text == "<h1>ResearchPath</h1>"
        assert client.get("/asset.js").text == "window.ready = true;"
        assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_mount_web_app_sets_security_response_headers(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>ResearchPath</h1>", encoding="utf-8")
    application = FastAPI()

    @application.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    mount_web_app(application, dist)

    with TestClient(application) as client:
        html = client.get("/")
        assert html.headers["x-content-type-options"] == "nosniff"
        assert html.headers["x-frame-options"] == "DENY"
        assert "default-src 'self'" in html.headers["content-security-policy"]
        assert "script-src 'self'" in html.headers["content-security-policy"]
        api = client.get("/api/v1/health")
        assert api.headers.get("x-content-type-options") == "nosniff"


def test_mount_web_app_requires_a_built_index(tmp_path: Path) -> None:
    application = FastAPI()

    try:
        mount_web_app(application, tmp_path / "missing")
    except RuntimeError as error:
        assert "npm run build:web" in str(error)
    else:
        raise AssertionError("mount_web_app should reject a missing production bundle")
