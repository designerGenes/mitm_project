"""Tests for the CLI and launchd modules."""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from watcher.cli.main import cli
from watcher.cli import launchd


@pytest.fixture
def runner():
    return CliRunner()


class TestLaunchdPlist:
    def test_generate_plist_defaults(self):
        plist = launchd.generate_plist()
        assert plist["Label"] == "com.watcher.daemon"
        assert plist["KeepAlive"] is True
        assert plist["RunAtLoad"] is False
        env = plist["EnvironmentVariables"]
        assert env["WATCHER_API_PORT"] == "9090"
        assert env["WATCHER_PROXY_PORT"] == "8080"
        assert env["WATCHER_VERBOSE"] == "0"
        assert env["WATCHER_UNSAFE"] == "0"

    def test_generate_plist_custom(self):
        plist = launchd.generate_plist(
            port=8888,
            proxy_port=9999,
            output_dir="/tmp/traffic",
            verbose=True,
            unsafe=True,
        )
        env = plist["EnvironmentVariables"]
        assert env["WATCHER_API_PORT"] == "8888"
        assert env["WATCHER_PROXY_PORT"] == "9999"
        assert env["WATCHER_OUTPUT_DIR"] == "/tmp/traffic"
        assert env["WATCHER_VERBOSE"] == "1"
        assert env["WATCHER_UNSAFE"] == "1"

    def test_generate_plist_has_log_paths(self):
        plist = launchd.generate_plist()
        assert "StandardOutPath" in plist
        assert "StandardErrorPath" in plist
        assert "watcher.stdout.log" in plist["StandardOutPath"]

    def test_generate_plist_program_arguments(self):
        plist = launchd.generate_plist()
        args = plist["ProgramArguments"]
        assert args[0] == sys.executable
        assert args[1] == "-m"
        assert args[2] == "watcher.daemon_entry"

    def test_write_plist(self, tmp_path):
        with patch.object(launchd, "PLIST_DIR", tmp_path), \
             patch.object(launchd, "PLIST_PATH", tmp_path / "com.watcher.daemon.plist"), \
             patch.object(launchd, "LOG_DIR", tmp_path / "logs"):
            path = launchd.write_plist(port=7777)
            assert path.exists()
            with open(path, "rb") as f:
                data = plistlib.load(f)
            assert data["EnvironmentVariables"]["WATCHER_API_PORT"] == "7777"

    def test_remove_plist(self, tmp_path):
        plist_file = tmp_path / "com.watcher.daemon.plist"
        plist_file.write_text("dummy")
        with patch.object(launchd, "PLIST_PATH", plist_file):
            launchd.remove_plist()
            assert not plist_file.exists()

    def test_remove_plist_missing(self, tmp_path):
        plist_file = tmp_path / "nonexistent.plist"
        with patch.object(launchd, "PLIST_PATH", plist_file):
            launchd.remove_plist()  # should not raise


class TestCliStatus:
    def test_status_not_running(self, runner):
        with patch("watcher.cli.main.httpx") as mock_httpx:
            mock_httpx.get.side_effect = __import__("httpx").ConnectError("refused")
            mock_httpx.ConnectError = __import__("httpx").ConnectError
            result = runner.invoke(cli, ["status"])
            assert "not running" in result.output

    def test_status_running(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "config": {
                "api_port": 9090,
                "proxy_port": 8080,
                "output_dir": "/tmp/traffic",
                "verbose": False,
            },
            "current_span": "test_span",
            "exchange_count": 5,
            "spans": {
                "test_span": {"started_at": "2025-01-01T00:00:00", "stopped_at": None},
            },
        }
        with patch("watcher.cli.main.httpx") as mock_httpx:
            mock_httpx.get.return_value = mock_resp
            mock_httpx.ConnectError = __import__("httpx").ConnectError
            result = runner.invoke(cli, ["status"])
            assert "running" in result.output
            assert "9090" in result.output
            assert "test_span" in result.output
            assert "5" in result.output

    def test_status_json_output(self, runner):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"config": {}, "current_span": None, "exchange_count": 0, "spans": {}}
        with patch("watcher.cli.main.httpx") as mock_httpx:
            mock_httpx.get.return_value = mock_resp
            mock_httpx.ConnectError = __import__("httpx").ConnectError
            result = runner.invoke(cli, ["status", "--json-output"])
            assert '"exchange_count"' in result.output


class TestCliReset:
    def test_reset_success(self, runner):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("watcher.cli.main.httpx") as mock_httpx:
            mock_httpx.post.return_value = mock_resp
            mock_httpx.ConnectError = __import__("httpx").ConnectError
            result = runner.invoke(cli, ["reset"])
            assert "reset" in result.output.lower()

    def test_reset_not_running(self, runner):
        with patch("watcher.cli.main.httpx") as mock_httpx:
            mock_httpx.post.side_effect = __import__("httpx").ConnectError("refused")
            mock_httpx.ConnectError = __import__("httpx").ConnectError
            result = runner.invoke(cli, ["reset"])
            assert result.exit_code != 0


class TestCliStop:
    def test_stop_sends_shutdown(self, runner):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("watcher.cli.main.httpx") as mock_httpx, \
             patch("watcher.cli.main.launchd") as mock_launchd:
            mock_httpx.post.return_value = mock_resp
            mock_httpx.ConnectError = __import__("httpx").ConnectError
            mock_launchd.is_loaded.return_value = True
            mock_launchd.unload.return_value = MagicMock(returncode=0)
            result = runner.invoke(cli, ["stop"])
            assert "shutdown" in result.output.lower()
            mock_launchd.unload.assert_called_once()

    def test_stop_daemon_not_responding(self, runner):
        with patch("watcher.cli.main.httpx") as mock_httpx, \
             patch("watcher.cli.main.launchd") as mock_launchd:
            mock_httpx.post.side_effect = __import__("httpx").ConnectError("refused")
            mock_httpx.ConnectError = __import__("httpx").ConnectError
            mock_launchd.is_loaded.return_value = False
            result = runner.invoke(cli, ["stop"])
            assert "not responding" in result.output.lower() or "no launchd" in result.output.lower()


class TestCliStart:
    def test_start_foreground_option_exists(self, runner):
        # Just check the option is recognized (don't actually start)
        result = runner.invoke(cli, ["start", "--help"])
        assert "--foreground" in result.output
        assert "--port" in result.output
        assert "--proxy-port" in result.output
        assert "--verbose" in result.output
        assert "--unsafe" in result.output

    def test_start_already_running(self, runner):
        with patch("watcher.cli.main.launchd") as mock_launchd:
            mock_launchd.is_loaded.return_value = True
            result = runner.invoke(cli, ["start"])
            assert result.exit_code != 0
            assert "already running" in result.output.lower()

    def test_start_unsafe_passed_to_launchd(self, runner):
        with patch("watcher.cli.main.launchd") as mock_launchd, \
             patch("watcher.cli.main.httpx") as mock_httpx:
            mock_launchd.is_loaded.return_value = False
            mock_launchd.write_plist.return_value = Path("/tmp/fake.plist")
            mock_launchd.load.return_value = MagicMock(returncode=0)
            mock_httpx.get.return_value = MagicMock(status_code=200)
            mock_httpx.ConnectError = __import__("httpx").ConnectError

            runner.invoke(cli, ["start", "--unsafe"])

            _, kwargs = mock_launchd.write_plist.call_args
            assert kwargs["unsafe"] is True

    def test_start_unsafe_default_false(self, runner):
        with patch("watcher.cli.main.launchd") as mock_launchd, \
             patch("watcher.cli.main.httpx") as mock_httpx:
            mock_launchd.is_loaded.return_value = False
            mock_launchd.write_plist.return_value = Path("/tmp/fake.plist")
            mock_launchd.load.return_value = MagicMock(returncode=0)
            mock_httpx.get.return_value = MagicMock(status_code=200)
            mock_httpx.ConnectError = __import__("httpx").ConnectError

            runner.invoke(cli, ["start"])

            _, kwargs = mock_launchd.write_plist.call_args
            assert kwargs["unsafe"] is False


class TestUnsafeConfig:
    def test_config_unsafe_default_false(self):
        from watcher.config import WatcherConfig
        config = WatcherConfig()
        assert config.unsafe is False

    def test_config_unsafe_in_dict(self):
        from watcher.config import WatcherConfig
        config = WatcherConfig(unsafe=True)
        d = config.to_dict()
        assert d["unsafe"] is True

    def test_generate_plist_unsafe_flag(self):
        plist = launchd.generate_plist(unsafe=True)
        assert plist["EnvironmentVariables"]["WATCHER_UNSAFE"] == "1"

    def test_generate_plist_unsafe_default(self):
        plist = launchd.generate_plist()
        assert plist["EnvironmentVariables"]["WATCHER_UNSAFE"] == "0"

    def test_daemon_entry_reads_unsafe_env(self):
        import os
        from watcher.daemon_entry import main
        with patch.dict(os.environ, {"WATCHER_UNSAFE": "1"}), \
             patch("watcher.daemon_entry.start") as mock_start:
            main()
            config = mock_start.call_args[0][0]
            assert config.unsafe is True

    def test_daemon_entry_unsafe_default(self):
        import os
        from watcher.daemon_entry import main
        env = {k: v for k, v in os.environ.items() if k != "WATCHER_UNSAFE"}
        with patch.dict(os.environ, env, clear=True), \
             patch("watcher.daemon_entry.start") as mock_start:
            main()
            config = mock_start.call_args[0][0]
            assert config.unsafe is False
