from __future__ import annotations

import asyncio
import logging

import uvicorn
from mitmproxy import options as mitmproxy_options
from mitmproxy.tools.dump import DumpMaster

from wire.config import WireConfig
from wire.store.data_store import DataStore
from wire.store.span_manager import SpanManager
from wire.capture.addon import WireAddon
from wire.persistence.writer import DiskWriter
from wire.api.app import create_app

logger = logging.getLogger(__name__)


async def run_server(config: WireConfig) -> None:
    data_store = DataStore()
    span_manager = SpanManager()
    shutdown_event = asyncio.Event()

    disk_writer = DiskWriter(config.output_dir)
    app = create_app(config, data_store, span_manager, shutdown_event, disk_writer)

    # --- uvicorn (HTTP API) ---
    # Bind to localhost only — we only serve the iOS simulator and local CLI,
    # not the wider network. This also avoids needing sudo on enterprise Macs.
    uv_config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=config.api_port,
        log_level="info" if config.verbose else "warning",
    )
    uv_server = uvicorn.Server(uv_config)

    # --- mitmproxy (traffic capture) ---
    opts = mitmproxy_options.Options(
        listen_host="127.0.0.1",
        listen_port=config.proxy_port,
    )
    # In unsafe mode, skip upstream TLS certificate verification.
    # This is required on enterprise networks where Zscaler or similar
    # TLS-inspection proxies re-sign traffic with their own CA, causing
    # "self-signed certificate in certificate chain" errors.
    if config.unsafe:
        opts.update(ssl_insecure=True)
    master = DumpMaster(opts, with_termlog=config.verbose, with_dumper=False)
    addon = WireAddon(data_store, span_manager, config.api_port, disk_writer)
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
        "WIREd starting — API on :%d, proxy on :%d",
        config.api_port, config.proxy_port,
    )

    await asyncio.gather(
        run_uvicorn(),
        run_mitmproxy(),
        wait_shutdown(),
    )


def start(config: WireConfig | None = None) -> None:
    if config is None:
        config = WireConfig()
    asyncio.run(run_server(config))
