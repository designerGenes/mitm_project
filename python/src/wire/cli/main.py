"""CLI for the WIRE daemon: start|stop|reset|status."""

from __future__ import annotations

import json
import sys
import time

import click
import httpx

from wire.cli import launchd


def _api_url(port: int, path: str) -> str:
    return f"http://localhost:{port}{path}"


def _daemon_port() -> int:
    """Read the API port from the running plist, or default to 9090."""
    import plistlib
    try:
        with open(launchd.PLIST_PATH, "rb") as f:
            plist = plistlib.load(f)
        return int(plist.get("EnvironmentVariables", {}).get("WIRE_API_PORT", "9090"))
    except Exception:
        return 9090


@click.group()
def cli():
    """WIRE — HTTP traffic capture and query daemon."""
    pass


@cli.command()
@click.option("--port", default=9090, help="HTTP API server port")
@click.option("--proxy-port", default=8080, help="mitmproxy listening port")
@click.option("--output", default=None, help="Output directory for traffic data")
@click.option("--verbose", is_flag=True, help="Log captured traffic to stdout")
@click.option("--unsafe", is_flag=True, help="Skip upstream TLS verification (for Zscaler/corporate proxies)")
@click.option("--foreground", is_flag=True, help="Run in foreground instead of launchd")
def start(port: int, proxy_port: int, output: str | None, verbose: bool, unsafe: bool, foreground: bool):
    """Start the WIRE daemon."""
    if foreground:
        from pathlib import Path
        from wire.config import WireConfig
        from wire.daemon import start as daemon_start

        config = WireConfig(
            api_port=port,
            proxy_port=proxy_port,
            verbose=verbose,
            unsafe=unsafe,
        )
        if output:
            config.output_dir = Path(output)
        daemon_start(config)
        return

    # Check if already running
    if launchd.is_loaded():
        click.echo(f"WIRE is already running. Use 'wire stop' first.")
        sys.exit(1)

    # Write plist and load via launchd
    plist_path = launchd.write_plist(
        port=port,
        proxy_port=proxy_port,
        output_dir=output,
        verbose=verbose,
        unsafe=unsafe,
    )
    click.echo(f"Wrote plist to {plist_path}")

    result = launchd.load()
    if result.returncode != 0:
        click.echo(f"Failed to load launchd job: {result.stderr.strip()}", err=True)
        sys.exit(1)

    # Wait briefly for the daemon to start, then verify
    click.echo(f"Starting WIRE (API :{port}, proxy :{proxy_port})...")
    time.sleep(1)

    try:
        resp = httpx.get(_api_url(port, "/health"), timeout=3)
        if resp.status_code == 200:
            click.echo("WIRE is running.")
        else:
            click.echo("WIRE started but health check returned unexpected status.", err=True)
    except httpx.ConnectError:
        click.echo("WIRE loaded but not yet responding. Check logs at:")
        click.echo(f"  {launchd.LOG_DIR / 'wired.stderr.log'}")


@cli.command()
@click.option("--port", default=None, type=int, help="API port (auto-detected from plist)")
def stop(port: int | None):
    """Stop the WIRE daemon."""
    api_port = port or _daemon_port()

    # Send shutdown to the daemon
    try:
        resp = httpx.post(_api_url(api_port, "/admin/shutdown"), timeout=5)
        if resp.status_code == 200:
            click.echo("Shutdown signal sent.")
    except httpx.ConnectError:
        click.echo("Daemon not responding (may already be stopped).")

    # Unload from launchd
    if launchd.is_loaded():
        result = launchd.unload()
        if result.returncode == 0:
            click.echo("Unloaded launchd job.")
        else:
            click.echo(f"Failed to unload: {result.stderr.strip()}", err=True)
    else:
        click.echo("No launchd job loaded.")


@cli.command()
@click.option("--port", default=None, type=int, help="API port (auto-detected from plist)")
def reset(port: int | None):
    """Reset all captured data."""
    api_port = port or _daemon_port()

    try:
        resp = httpx.post(_api_url(api_port, "/reset"), timeout=5)
        if resp.status_code == 200:
            click.echo("All data reset.")
        else:
            click.echo(f"Unexpected response: {resp.status_code}", err=True)
    except httpx.ConnectError:
        click.echo("Cannot connect to daemon. Is it running?", err=True)
        sys.exit(1)


@cli.command()
@click.option("--port", default=None, type=int, help="API port (auto-detected from plist)")
@click.option("--json-output", "as_json", is_flag=True, help="Output raw JSON")
def status(port: int | None, as_json: bool):
    """Show daemon status."""
    api_port = port or _daemon_port()

    try:
        resp = httpx.get(_api_url(api_port, "/status"), timeout=5)
    except httpx.ConnectError:
        click.echo("WIRE is not running.")
        sys.exit(1)

    data = resp.json()

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    # Pretty-print
    config = data.get("config", {})
    click.echo(f"WIRE is running")
    click.echo(f"  API port:       {config.get('api_port')}")
    click.echo(f"  Proxy port:     {config.get('proxy_port')}")
    click.echo(f"  Output dir:     {config.get('output_dir')}")
    click.echo(f"  Verbose:        {config.get('verbose')}")
    click.echo(f"  Current span:   {data.get('current_span') or '(none)'}")
    click.echo(f"  Exchange count: {data.get('exchange_count', 0)}")

    spans = data.get("spans", {})
    if spans:
        click.echo(f"  Spans ({len(spans)}):")
        for name, info in spans.items():
            state = "active" if info.get("stopped_at") is None else "stopped"
            click.echo(f"    - {name} ({state})")
