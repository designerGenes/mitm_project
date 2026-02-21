from __future__ import annotations

import logging
from datetime import datetime, timezone

from mitmproxy import http

from wire.models import Exchange
from wire.capture.normalize import (
    classify_content_type,
    normalize_method,
    parse_url,
    try_parse_json,
)
from wire.store.data_store import DataStore
from wire.store.span_manager import SpanManager
from wire.persistence.writer import DiskWriter

logger = logging.getLogger(__name__)


def _headers_to_dict(headers: http.Headers) -> dict[str, str | list[str]]:
    """Convert mitmproxy Headers to a dict with lowercased keys.

    Single-value headers become strings; multi-value headers become lists.
    """
    result: dict[str, list[str]] = {}
    for key, value in headers.items(multi=True):
        k = key.lower()
        result.setdefault(k, []).append(value)
    return {k: v[0] if len(v) == 1 else v for k, v in result.items()}


class WireAddon:
    """mitmproxy addon that captures HTTP exchanges into the DataStore."""

    def __init__(
        self,
        data_store: DataStore,
        span_manager: SpanManager,
        api_port: int,
        disk_writer: DiskWriter | None = None,
    ) -> None:
        self._store = data_store
        self._span_manager = span_manager
        self._api_port = api_port
        self._writer = disk_writer

    def _is_control_traffic(self, flow: http.HTTPFlow) -> bool:
        """Return True if this flow is a request to WIRE's own HTTP API."""
        host = flow.request.host.lower()
        port = flow.request.port
        if host in ("localhost", "127.0.0.1", "::1") and port == self._api_port:
            return True
        return False

    def response(self, flow: http.HTTPFlow) -> None:
        """Called when a full HTTP response has been received."""
        if flow.response is None:
            return
        if self._is_control_traffic(flow):
            return

        req = flow.request
        resp = flow.response

        # Parse URL
        domain, endpoint, query_params = parse_url(req.pretty_url)
        method = normalize_method(req.method)

        # Extract bodies
        req_body = req.get_content(strict=False) or b""
        resp_body = resp.get_content(strict=False) or b""

        # Headers
        req_headers = _headers_to_dict(req.headers)
        resp_headers = _headers_to_dict(resp.headers)

        # Content-Type classification
        req_ct_raw = req.headers.get("content-type", "")
        resp_ct_raw = resp.headers.get("content-type", "")
        req_ct = classify_content_type(req_ct_raw, req_body)
        resp_ct = classify_content_type(resp_ct_raw, resp_body)

        # JSON parsing (only when classified as JSON)
        req_parsed = try_parse_json(req_body) if req_ct == "json" else None
        resp_parsed = try_parse_json(resp_body) if resp_ct == "json" else None

        # Timestamps
        ts_start = datetime.fromtimestamp(req.timestamp_start, tz=timezone.utc)
        ts_end = datetime.fromtimestamp(
            resp.timestamp_end if resp.timestamp_end else req.timestamp_start,
            tz=timezone.utc,
        )
        duration_ms = (ts_end - ts_start).total_seconds() * 1000

        exchange = Exchange(
            timestamp_start=ts_start,
            timestamp_end=ts_end,
            duration_ms=duration_ms,
            span=self._span_manager.current_span,
            domain=domain,
            endpoint=endpoint,
            query_params=query_params,
            method=method,
            request_headers=req_headers,
            request_body_raw=req_body,
            request_body_parsed=req_parsed,
            request_content_type=req_ct,
            request_content_type_raw=req_ct_raw,
            response_status=resp.status_code,
            response_headers=resp_headers,
            response_body_raw=resp_body,
            response_body_parsed=resp_parsed,
            response_content_type=resp_ct,
            response_content_type_raw=resp_ct_raw,
        )

        self._store.add(exchange)

        # Write-behind to disk
        if self._writer:
            try:
                self._writer.write(exchange)
            except Exception:
                logger.exception("Failed to write exchange to disk")

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Captured: %s %s%s -> %d (span=%s)",
                method, domain, endpoint, resp.status_code,
                self._span_manager.current_span,
            )
