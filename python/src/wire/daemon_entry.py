"""Daemon entry point for launchd. Reads config from environment variables."""

import os
from pathlib import Path

from wire.config import WireConfig
from wire.daemon import start


def main() -> None:
    config = WireConfig(
        api_port=int(os.environ.get("WIRE_API_PORT", "18081")),
        proxy_port=int(os.environ.get("WIRE_PROXY_PORT", "8080")),
        verbose=os.environ.get("WIRE_VERBOSE", "0") == "1",
        unsafe=os.environ.get("WIRE_UNSAFE", "0") == "1",
    )
    output = os.environ.get("WIRE_OUTPUT_DIR")
    if output:
        config.output_dir = Path(output)

    start(config)


if __name__ == "__main__":
    main()
