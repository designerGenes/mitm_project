"""Entry point for `python -m watcher`."""

from wire.config import WireConfig
from wire.daemon import start

if __name__ == "__main__":
    start(WireConfig())
