from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.production import ProductionApplication


def build_client(tmp_path: Path) -> TestClient:
    frontend = tmp_path / "dist"
    assets = frontend / "assets"
    assets.mkdir(parents=True)
    (frontend / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (assets / "app.js").write_text("console.log('lantern')", encoding="utf-8")

    async def backend(request):
        if request.url.path == "/":
            return PlainTextResponse("Mission Control legacy")
        return JSONResponse({"path": request.url.path})

    backend_app = Starlette(
        routes=[
            Route("/", backend),
            Route("/api/health", backend),
            Route("/docs", backend),
        ]
    )
    return TestClient(ProductionApplication(backend_app, frontend))


def test_serves_react_root_and_spa_fallback(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    assert '<div id="root"></div>' in client.get("/").text
    assert '<div id="root"></div>' in client.get("/customers/acme").text
    assert "console.log" in client.get("/assets/app.js").text


def test_delegates_backend_and_rewrites_legacy(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    assert client.get("/api/health").json() == {"path": "/api/health"}
    assert client.get("/docs").json() == {"path": "/docs"}
    assert client.get("/legacy").text == "Mission Control legacy"


def test_returns_service_unavailable_without_frontend_build(tmp_path: Path) -> None:
    backend_app = Starlette()
    client = TestClient(ProductionApplication(backend_app, tmp_path / "missing"))

    response = client.get("/")

    assert response.status_code == 503
    assert "frontend is not built" in response.text
