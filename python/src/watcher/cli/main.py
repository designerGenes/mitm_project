"""CLI stub for `watcher` command. Full implementation in Phase 6."""

import click


@click.group()
def cli():
    """Watcher — HTTP traffic capture and query daemon."""
    pass


@cli.command()
@click.option("--port", default=9090, help="HTTP API server port")
@click.option("--proxy-port", default=8080, help="mitmproxy listening port")
@click.option("--output", default=None, help="Output directory for traffic data")
@click.option("--verbose", is_flag=True, help="Log captured traffic to stdout")
def start(port, proxy_port, output, verbose):
    """Start the Watcher daemon."""
    from pathlib import Path
    from watcher.config import WatcherConfig
    from watcher.daemon import start as daemon_start

    config = WatcherConfig(
        api_port=port,
        proxy_port=proxy_port,
        verbose=verbose,
    )
    if output:
        config.output_dir = Path(output)

    daemon_start(config)


@cli.command()
def stop():
    """Stop the Watcher daemon."""
    click.echo("Stop not yet implemented (Phase 6)")


@cli.command()
def reset():
    """Reset all captured data."""
    click.echo("Reset not yet implemented (Phase 6)")


@cli.command()
def status():
    """Show daemon status."""
    click.echo("Status not yet implemented (Phase 6)")
