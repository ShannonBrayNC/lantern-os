from __future__ import annotations

import os
from pathlib import Path
from typing import Awaitable, Callable

from starlette.responses import FileResponse, PlainTextResponse
from starlette.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send

from app.main import app as backend_app

ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class ProductionApplication:
    """Serve the compiled React client while preserving backend routes and rollback."""

    _backend_prefixes = (
        "/api",
        "/auth",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/legacy",
    )

    def __init__(self, backend: ASGIApp, frontend_dist: Path) -> None:
        self.backend = backend
        self.frontend_dist = frontend_dist
        self.assets = StaticFiles(directory=frontend_dist, check_dir=False)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.backend(scope, receive, send)
            return

        path = scope.get("path", "/")
        if path == "/legacy" or path.startswith("/legacy/"):
            legacy_scope = dict(scope)
            legacy_scope["path"] = path.removeprefix("/legacy") or "/"
            legacy_scope["raw_path"] = legacy_scope["path"].encode("utf-8")
            await self.backend(legacy_scope, receive, send)
            return

        if path.startswith(self._backend_prefixes):
            await self.backend(scope, receive, send)
            return

        if path.startswith("/assets/"):
            await self.assets(scope, receive, send)
            return

        index = self.frontend_dist / "index.html"
        if index.is_file():
            await FileResponse(index)(scope, receive, send)
            return

        response = PlainTextResponse(
            "Lantern OS frontend is not built. Run `npm install && npm run build` in frontend/.",
            status_code=503,
        )
        await response(scope, receive, send)


frontend_dist = Path(
    os.getenv(
        "LANTERN_FRONTEND_DIST",
        Path(__file__).resolve().parent / "static",
    )
)
app = ProductionApplication(backend_app, frontend_dist)
