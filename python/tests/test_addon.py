"""Tests for the mitmproxy capture addon."""

from __future__ import annotations

import time

import pytest
from mitmproxy import http
from mitmproxy.test import tflow

from watcher.capture.addon import WatcherAddon, _headers_to_dict
from watcher.store.data_store import DataStore
from watcher.store.span_manager import SpanManager


@pytest.fixture
def store():
    return DataStore()


@pytest.fixture
def spans():
    return SpanManager()


@pytest.fixture
def addon(store, spans):
    return WatcherAddon(store, spans, api_port=9090)


def _make_flow(
    *,
    method: str = "GET",
    url: str = "https://api.example.com/users/123",
    status_code: int = 200,
    req_content: bytes = b"",
    resp_content: bytes = b'{"id": 123, "name": "Alice"}',
    req_headers: list[tuple[bytes, bytes]] | None = None,
    resp_headers: list[tuple[bytes, bytes]] | None = None,
) -> http.HTTPFlow:
    """Build a realistic HTTPFlow for testing."""
    flow = tflow.tflow(resp=True)

    flow.request.url = url
    flow.request.method = method
    flow.request.content = req_content
    if req_headers:
        flow.request.headers = http.Headers(req_headers)
    flow.request.timestamp_start = time.time() - 0.1
    flow.request.timestamp_end = time.time() - 0.05

    flow.response.status_code = status_code
    flow.response.content = resp_content
    if resp_headers:
        flow.response.headers = http.Headers(resp_headers)
    else:
        flow.response.headers = http.Headers([(b"Content-Type", b"application/json")])
    flow.response.timestamp_start = time.time() - 0.04
    flow.response.timestamp_end = time.time()

    return flow


class TestHeadersToDict:
    def test_single_values(self):
        h = http.Headers([(b"Content-Type", b"application/json"), (b"Host", b"example.com")])
        result = _headers_to_dict(h)
        assert result["content-type"] == "application/json"
        assert result["host"] == "example.com"

    def test_multi_values(self):
        h = http.Headers([
            (b"Set-Cookie", b"a=1"),
            (b"Set-Cookie", b"b=2"),
        ])
        result = _headers_to_dict(h)
        assert result["set-cookie"] == ["a=1", "b=2"]

    def test_empty(self):
        h = http.Headers()
        assert _headers_to_dict(h) == {}

    def test_case_insensitive_grouping(self):
        h = http.Headers([
            (b"X-Custom", b"val1"),
            (b"x-custom", b"val2"),
        ])
        result = _headers_to_dict(h)
        assert result["x-custom"] == ["val1", "val2"]


class TestWatcherAddon:
    def test_captures_basic_exchange(self, addon, store):
        flow = _make_flow()
        addon.response(flow)

        assert store.count() == 1
        ex = store.exchanges[0]
        assert ex.domain == "api.example.com"
        assert ex.endpoint == "/users/123"
        assert ex.method == "GET"
        assert ex.response_status == 200

    def test_captures_json_body(self, addon, store):
        flow = _make_flow(resp_content=b'{"key": "value"}')
        addon.response(flow)

        ex = store.exchanges[0]
        assert ex.response_content_type == "json"
        assert ex.response_body_parsed == {"key": "value"}

    def test_captures_non_json_body(self, addon, store):
        flow = _make_flow(
            resp_content=b"<html>hello</html>",
            resp_headers=[(b"Content-Type", b"text/html")],
        )
        addon.response(flow)

        ex = store.exchanges[0]
        assert ex.response_content_type == "text"
        assert ex.response_body_parsed is None

    def test_captures_request_body(self, addon, store):
        flow = _make_flow(
            method="POST",
            req_content=b'{"name": "Bob"}',
            req_headers=[(b"Content-Type", b"application/json")],
        )
        addon.response(flow)

        ex = store.exchanges[0]
        assert ex.request_body_parsed == {"name": "Bob"}
        assert ex.request_content_type == "json"
        assert ex.method == "POST"

    def test_filters_control_traffic(self, addon, store):
        flow = _make_flow(url="http://localhost:9090/health")
        addon.response(flow)
        assert store.count() == 0

    def test_filters_control_traffic_127(self, addon, store):
        flow = _make_flow(url="http://127.0.0.1:9090/span/start")
        addon.response(flow)
        assert store.count() == 0

    def test_allows_different_port(self, addon, store):
        flow = _make_flow(url="http://localhost:3000/api/data")
        addon.response(flow)
        assert store.count() == 1

    def test_skips_no_response(self, addon, store):
        flow = _make_flow()
        flow.response = None
        addon.response(flow)
        assert store.count() == 0

    def test_tags_with_active_span(self, addon, store, spans):
        spans.start("my_span")
        flow = _make_flow()
        addon.response(flow)

        ex = store.exchanges[0]
        assert ex.span == "my_span"

    def test_no_span_when_inactive(self, addon, store, spans):
        flow = _make_flow()
        addon.response(flow)

        ex = store.exchanges[0]
        assert ex.span is None

    def test_query_params_extracted(self, addon, store):
        flow = _make_flow(url="https://api.example.com/search?q=test&page=2")
        addon.response(flow)

        ex = store.exchanges[0]
        assert ex.endpoint == "/search"
        assert ex.query_params == {"q": "test", "page": "2"}

    def test_trailing_slash_stripped(self, addon, store):
        flow = _make_flow(url="https://api.example.com/users/")
        addon.response(flow)

        ex = store.exchanges[0]
        assert ex.endpoint == "/users"

    def test_domain_normalized_lowercase(self, addon, store):
        flow = _make_flow(url="https://API.Example.COM/test")
        addon.response(flow)

        ex = store.exchanges[0]
        assert ex.domain == "api.example.com"

    def test_method_normalized_uppercase(self, addon, store):
        flow = _make_flow(method="post")
        addon.response(flow)

        ex = store.exchanges[0]
        assert ex.method == "POST"

    def test_timing_fields(self, addon, store):
        flow = _make_flow()
        addon.response(flow)

        ex = store.exchanges[0]
        assert ex.timestamp_start is not None
        assert ex.timestamp_end is not None
        assert ex.duration_ms >= 0

    def test_empty_body_classified_as_empty(self, addon, store):
        flow = _make_flow(resp_content=b"", resp_headers=[(b"Content-Type", b"application/json")])
        addon.response(flow)

        ex = store.exchanges[0]
        assert ex.response_content_type == "empty"
        assert ex.response_body_parsed is None

    def test_multiple_captures(self, addon, store):
        for i in range(5):
            flow = _make_flow(url=f"https://api.example.com/item/{i}")
            addon.response(flow)

        assert store.count() == 5
        endpoints = [ex.endpoint for ex in store.exchanges]
        assert "/item/0" in endpoints
        assert "/item/4" in endpoints
