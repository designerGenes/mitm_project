"""Daemon entry point for launchd. Reads config from environment variables."""

import os
from pathlib import Path

from watcher.config import WatcherConfig
from watcher.daemon import start


def main() -> None:
    config = WatcherConfig(
        api_port=int(os.environ.get("WATCHER_API_PORT", "9090")),
        proxy_port=int(os.environ.get("WATCHER_PROXY_PORT", "8080")),
        verbose=os.environ.get("WATCHER_VERBOSE", "0") == "1",
    )
    output = os.environ.get("WATCHER_OUTPUT_DIR")
    if output:
        config.output_dir = Path(output)

    start(config)


if __name__ == "__main__":
    main()
