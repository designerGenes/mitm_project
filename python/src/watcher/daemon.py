from __future__ import annotations

import asyncio

import uvicorn

from watcher.config import WatcherConfig
from watcher.store.data_store import DataStore
from watcher.store.span_manager import SpanManager
from watcher.api.app import create_app


async def run_server(config: WatcherConfig) -> None:
    data_store = DataStore()
    span_manager = SpanManager()
    shutdown_event = asyncio.Event()

    app = create_app(config, data_store, span_manager, shutdown_event)

    uv_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=config.api_port,
        log_level="info" if config.verbose else "warning",
    )
    server = uvicorn.Server(uv_config)

    # Run server until shutdown is requested
    serve_task = asyncio.create_task(server.serve())
    shutdown_task = asyncio.create_task(shutdown_event.wait())

    done, pending = await asyncio.wait(
        [serve_task, shutdown_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    if shutdown_task in done:
        server.should_exit = True
        await serve_task

    for task in pending:
        task.cancel()


def start(config: WatcherConfig | None = None) -> None:
    if config is None:
        config = WatcherConfig()
    asyncio.run(run_server(config))
