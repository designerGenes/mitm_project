"""Write-behind folder structure for captured HTTP exchanges.

Folder hierarchy:
  output/
  ├── spans/<span_name>/<domain>/<endpoint>/<method>/<datetime>/
  │   ├── request/headers.json, body.json
  │   └── response/headers.json, body.json, status.json
  └── unspanned/<domain>/<endpoint>/<method>/<datetime>/
      ├── request/...
      └── response/...
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from wire.models import Exchange, ContentType

logger = logging.getLogger(__name__)


class DiskWriter:
    """Writes Exchange data to the folder hierarchy on disk."""

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    def write(self, exchange: Exchange) -> Path:
        """Write an exchange to disk. Returns the exchange directory path."""
        exchange_dir = self._build_path(exchange)
        exchange_dir.mkdir(parents=True, exist_ok=True)

        req_dir = exchange_dir / "request"
        resp_dir = exchange_dir / "response"
        req_dir.mkdir(exist_ok=True)
        resp_dir.mkdir(exist_ok=True)

        # Request
        self._write_json(req_dir / "headers.json", exchange.request_headers)
        self._write_body(req_dir / "body.json", exchange.request_body_raw, exchange.request_body_parsed, exchange.request_content_type)

        # Response
        self._write_json(resp_dir / "headers.json", exchange.response_headers)
        self._write_body(resp_dir / "body.json", exchange.response_body_raw, exchange.response_body_parsed, exchange.response_content_type)
        self._write_json(resp_dir / "status.json", {"status_code": exchange.response_status})

        logger.debug("Wrote exchange to %s", exchange_dir)
        return exchange_dir

    def reset(self) -> None:
        """Remove the entire output directory."""
        if self._output_dir.exists():
            shutil.rmtree(self._output_dir)
            logger.debug("Cleared output directory: %s", self._output_dir)

    def _build_path(self, exchange: Exchange) -> Path:
        """Build the folder path for an exchange."""
        # Span layer
        if exchange.span:
            span_dir = "spans" / Path(exchange.span)
        else:
            span_dir = Path("unspanned")

        # Endpoint: strip leading slash, use path segments as directories
        endpoint_path = exchange.endpoint.lstrip("/")
        if not endpoint_path:
            endpoint_path = "_root"

        # Datetime layer (filesystem-safe ISO format)
        dt_str = exchange.timestamp_start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        return self._output_dir / span_dir / exchange.domain / endpoint_path / exchange.method / dt_str

    def _write_json(self, path: Path, data: object) -> None:
        """Write data as formatted JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _write_body(
        self,
        path: Path,
        raw: bytes,
        parsed: object | None,
        content_type: ContentType,
    ) -> None:
        """Write body: parsed JSON if available, raw text otherwise, skip if empty."""
        if content_type == ContentType.EMPTY or not raw:
            # Write an explicit null for empty bodies
            self._write_json(path, None)
            return
        if parsed is not None:
            self._write_json(path, parsed)
            return
        # For text bodies, write as string; for binary, write raw bytes
        if content_type == ContentType.TEXT:
            try:
                text = raw.decode("utf-8", errors="replace")
                self._write_json(path, text)
            except Exception:
                path.write_bytes(raw)
        else:
            # Binary — write raw bytes
            path.write_bytes(raw)
