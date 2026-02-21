"""launchd plist generation and management for the Watcher daemon."""

from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path

LABEL = "com.watcher.daemon"
PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = PLIST_DIR / f"{LABEL}.plist"
LOG_DIR = Path.home() / "Library" / "Logs" / "Watcher"


def generate_plist(
    *,
    port: int = 9090,
    proxy_port: int = 8080,
    output_dir: str | None = None,
    verbose: bool = False,
) -> dict:
    """Generate the launchd plist dictionary."""
    # Build the command to run the daemon
    python = sys.executable
    args = [python, "-m", "watcher.daemon_entry"]

    # Pass config via environment variables
    env = {
        "WATCHER_API_PORT": str(port),
        "WATCHER_PROXY_PORT": str(proxy_port),
        "WATCHER_VERBOSE": "1" if verbose else "0",
    }
    if output_dir:
        env["WATCHER_OUTPUT_DIR"] = output_dir

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    plist = {
        "Label": LABEL,
        "ProgramArguments": args,
        "EnvironmentVariables": env,
        "KeepAlive": True,
        "RunAtLoad": False,
        "StandardOutPath": str(LOG_DIR / "watcher.stdout.log"),
        "StandardErrorPath": str(LOG_DIR / "watcher.stderr.log"),
    }
    return plist


def write_plist(
    *,
    port: int = 9090,
    proxy_port: int = 8080,
    output_dir: str | None = None,
    verbose: bool = False,
) -> Path:
    """Write the plist file to ~/Library/LaunchAgents/."""
    PLIST_DIR.mkdir(parents=True, exist_ok=True)
    plist = generate_plist(
        port=port,
        proxy_port=proxy_port,
        output_dir=output_dir,
        verbose=verbose,
    )
    with open(PLIST_PATH, "wb") as f:
        plistlib.dump(plist, f)
    return PLIST_PATH


def load() -> subprocess.CompletedProcess:
    """Load the launchd job (starts the daemon)."""
    return subprocess.run(
        ["launchctl", "load", str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )


def unload() -> subprocess.CompletedProcess:
    """Unload the launchd job (stops the daemon)."""
    return subprocess.run(
        ["launchctl", "unload", str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )


def is_loaded() -> bool:
    """Check if the launchd job is currently loaded."""
    result = subprocess.run(
        ["launchctl", "list"],
        capture_output=True,
        text=True,
    )
    return LABEL in result.stdout


def remove_plist() -> None:
    """Remove the plist file."""
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
