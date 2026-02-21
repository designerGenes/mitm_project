from __future__ import annotations

from fastapi import FastAPI

from wire.config import WireConfig
from wire.store.data_store import DataStore
from wire.store.span_manager import SpanManager
from wire.api.routes_admin import router as admin_router
from wire.api.routes_span import router as span_router
from wire.api.routes_query import router as query_router
from wire.api.routes_span_query import router as span_query_router


def create_app(
    config: WireConfig,
    data_store: DataStore,
    span_manager: SpanManager,
    shutdown_event: object | None = None,
    disk_writer: object | None = None,
) -> FastAPI:
    app = FastAPI(title="WIRE", version="0.1.0")

    # Stash shared state on app for dependency injection
    app.state.config = config
    app.state.data_store = data_store
    app.state.span_manager = span_manager
    app.state.shutdown_event = shutdown_event
    app.state.disk_writer = disk_writer

    app.include_router(admin_router)
    app.include_router(span_router)
    app.include_router(query_router)
    app.include_router(span_query_router)

    return app
