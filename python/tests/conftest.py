from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from watcher.config import WatcherConfig
from watcher.models import Exchange, ContentType
from watcher.store.data_store import DataStore
from watcher.store.span_manager import SpanManager
from watcher.api.app import create_app


@pytest.fixture
def config():
    return WatcherConfig()


@pytest.fixture
def data_store():
    return DataStore()


@pytest.fixture
def span_manager():
    return SpanManager()


@pytest.fixture
def app(config, data_store, span_manager):
    return create_app(config, data_store, span_manager)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def make_exchange(
    *,
    span: str | None = None,
    domain: str = "api.example.com",
    endpoint: str = "/users",
    method: str = "GET",
    status: int = 200,
    request_body: bytes = b"",
    response_body: bytes = b"",
    request_content_type: ContentType = ContentType.EMPTY,
    response_content_type: ContentType = ContentType.JSON,
    request_headers: dict | None = None,
    response_headers: dict | None = None,
    query_params: dict | None = None,
    duration_ms: float = 50.0,
    timestamp_start: datetime | None = None,
) -> Exchange:
    """Helper to build Exchange objects for tests."""
    import json as _json

    start = timestamp_start or datetime.now(timezone.utc)
    end = start + timedelta(milliseconds=duration_ms)

    # Auto-parse JSON bodies
    resp_parsed = None
    if response_content_type == ContentType.JSON and response_body:
        try:
            resp_parsed = _json.loads(response_body)
        except (ValueError, UnicodeDecodeError):
            pass

    req_parsed = None
    if request_content_type == ContentType.JSON and request_body:
        try:
            req_parsed = _json.loads(request_body)
        except (ValueError, UnicodeDecodeError):
            pass

    return Exchange(
        timestamp_start=start,
        timestamp_end=end,
        duration_ms=duration_ms,
        span=span,
        domain=domain,
        endpoint=endpoint,
        query_params=query_params or {},
        method=method,
        request_headers=request_headers or {},
        request_body_raw=request_body,
        request_body_parsed=req_parsed,
        request_content_type=request_content_type,
        request_content_type_raw="application/json" if request_content_type == ContentType.JSON else "",
        response_status=status,
        response_headers=response_headers or {"content-type": "application/json"},
        response_body_raw=response_body,
        response_body_parsed=resp_parsed,
        response_content_type=response_content_type,
        response_content_type_raw="application/json" if response_content_type == ContentType.JSON else "",
    )
