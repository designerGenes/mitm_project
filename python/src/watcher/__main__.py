"""Entry point for `python -m watcher`."""

from watcher.config import WatcherConfig
from watcher.daemon import start

if __name__ == "__main__":
    start(WatcherConfig())
