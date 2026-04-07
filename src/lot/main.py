from __future__ import annotations

from fastapi import FastAPI

from lot.api.error_mapper import install_api_error_handlers
from lot.api.routes import build_api_router
from lot.bootstrap import build_container


def create_app() -> FastAPI:
    """Create the FastAPI app around the architecture scaffold."""

    container = build_container()

    app = FastAPI(
        title="LOT MVP",
        version="0.1.0",
        summary="Agent-oriented embedded virtual debugging platform scaffold.",
    )
    app.state.container = container
    install_api_error_handlers(app)
    app.include_router(build_api_router(container.api_facade))
    return app


app = create_app()
