from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


_DEFAULT_OUTPUT = Path.home() / "Library" / "Application Support" / "Watcher" / "traffic"


@dataclass
class WatcherConfig:
    api_port: int = 9090
    proxy_port: int = 8080
    output_dir: Path = field(default_factory=lambda: _DEFAULT_OUTPUT)
    verbose: bool = False
    unsafe: bool = False

    def to_dict(self) -> dict:
        return {
            "api_port": self.api_port,
            "proxy_port": self.proxy_port,
            "output_dir": str(self.output_dir),
            "verbose": self.verbose,
            "unsafe": self.unsafe,
        }
