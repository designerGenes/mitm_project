from __future__ import annotations

import asyncio
import logging

import uvicorn
from mitmproxy import options as mitmproxy_options
from mitmproxy.tools.dump import DumpMaster

from watcher.config import WatcherConfig
from watcher.store.data_store import DataStore
from watcher.store.span_manager import SpanManager
from watcher.capture.addon import WatcherAddon
from watcher.persistence.writer import DiskWriter
from watcher.api.app import create_app

logger = logging.getLogger(__name__)


async def run_server(config: WatcherConfig) -> None:
    data_store = DataStore()
    span_manager = SpanManager()
    shutdown_event = asyncio.Event()

    disk_writer = DiskWriter(config.output_dir)
    app = create_app(config, data_store, span_manager, shutdown_event, disk_writer)

    # --- uvicorn (HTTP API) ---
    uv_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=config.api_port,
        log_level="info" if config.verbose else "warning",
    )
    uv_server = uvicorn.Server(uv_config)

    # --- mitmproxy (traffic capture) ---
    opts = mitmproxy_options.Options(
        listen_host="127.0.0.1",
        listen_port=config.proxy_port,
    )
    master = DumpMaster(opts, with_termlog=config.verbose, with_dumper=False)
    addon = WatcherAddon(data_store, span_manager, config.api_port, disk_writer)
    master.addons.add(addon)

    # Stash master on app state so /admin/shutdown can stop the proxy too
    app.state.mitmproxy_master = master

    async def run_uvicorn():
        await uv_server.serve()

    async def run_mitmproxy():
        await master.run()

    async def wait_shutdown():
        await shutdown_event.wait()
        # Gracefully stop both servers
        uv_server.should_exit = True
        master.should_exit.set()

    logger.info(
        "Watcher starting — API on :%d, proxy on :%d",
        config.api_port, config.proxy_port,
    )

    await asyncio.gather(
        run_uvicorn(),
        run_mitmproxy(),
        wait_shutdown(),
    )


def start(config: WatcherConfig | None = None) -> None:
    if config is None:
        config = WatcherConfig()
    asyncio.run(run_server(config))
