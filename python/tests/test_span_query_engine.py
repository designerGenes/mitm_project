"""Tests for span-level query engine."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import pytest

from tests.conftest import make_exchange
from watcher.models import (
    ContentType,
    SpanQueryRequest,
    SpanFilter,
    Question,
)
from watcher.store.data_store import DataStore
from watcher.store.span_manager import SpanManager
from watcher.query.span_engine import execute_span_query


@pytest.fixture
def span_manager():
    sm = SpanManager()
    sm.start("api_test")
    sm.stop()
    sm.start("login_test")
    sm.stop()
    return sm


@pytest.fixture
def store_with_data():
    store = DataStore()
    t1 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    # api_test span: 3 exchanges
    store.add(make_exchange(
        span="api_test",
        domain="api.example.com",
        endpoint="/users",
        method="GET",
        status=200,
        response_body=json.dumps([{"id": 1}]).encode(),
        response_content_type=ContentType.JSON,
        duration_ms=100.0,
        timestamp_start=t1,
    ))
    store.add(make_exchange(
        span="api_test",
        domain="api.example.com",
        endpoint="/users",
        method="POST",
        status=201,
        duration_ms=200.0,
        timestamp_start=t1 + timedelta(seconds=1),
    ))
    store.add(make_exchange(
        span="api_test",
        domain="cdn.example.com",
        endpoint="/assets/logo.png",
        method="GET",
        status=404,
        duration_ms=50.0,
        timestamp_start=t1 + timedelta(seconds=2),
    ))

    # login_test span: 2 exchanges
    store.add(make_exchange(
        span="login_test",
        domain="api.example.com",
        endpoint="/auth",
        method="POST",
        status=200,
        duration_ms=150.0,
        timestamp_start=t1 + timedelta(seconds=10),
    ))
    store.add(make_exchange(
        span="login_test",
        domain="api.example.com",
        endpoint="/auth",
        method="POST",
        status=500,
        duration_ms=300.0,
        timestamp_start=t1 + timedelta(seconds=11),
    ))

    # Unspanned exchange
    store.add(make_exchange(
        span=None,
        domain="api.example.com",
        endpoint="/health",
        method="GET",
        status=200,
        duration_ms=5.0,
        timestamp_start=t1 + timedelta(seconds=20),
    ))

    return store


class TestSpanFound:
    def test_existing_span(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="total_request_count")],
        ))
        assert result.found is True

    def test_nonexistent_span(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="nonexistent",
            questions=[Question(type="total_request_count")],
        ))
        assert result.found is False
        assert result.reason == "span_not_found"

    def test_scope_all(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="all",
            questions=[Question(type="total_request_count")],
        ))
        assert result.found is True
        assert result.answers[0].value == 6

    def test_scope_unspanned(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="unspanned",
            questions=[Question(type="total_request_count")],
        ))
        assert result.found is True
        assert result.answers[0].value == 1


class TestInventoryQuestions:
    def test_total_request_count(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="total_request_count")],
        ))
        assert result.answers[0].value == 3

    def test_domains_contacted(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="domains_contacted")],
        ))
        assert result.answers[0].value == ["api.example.com", "cdn.example.com"]

    def test_endpoints_contacted(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="endpoints_contacted")],
        ))
        assert "/users" in result.answers[0].value
        assert "/assets/logo.png" in result.answers[0].value

    def test_methods_used(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="methods_used")],
        ))
        assert result.answers[0].value == ["GET", "POST"]

    def test_unique_exchanges(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="unique_exchanges")],
        ))
        items = result.answers[0].value
        assert len(items) == 3
        # Find the GET /users entry
        users_get = next(i for i in items if i["endpoint"] == "/users" and i["method"] == "GET")
        assert users_get["count"] == 1
        assert users_get["domain"] == "api.example.com"


class TestTimingQuestions:
    def test_total_duration_ms(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="total_duration_ms")],
        ))
        assert result.answers[0].found is True
        # First exchange at t1, last ends at t1+2s+50ms
        assert result.answers[0].value > 0

    def test_span_start_time(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="span_start_time")],
        ))
        assert result.answers[0].found is True
        assert "2025-01-01T10:00:00" in result.answers[0].value

    def test_span_end_time(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="span_end_time")],
        ))
        assert result.answers[0].found is True
        assert "2025-01-01" in result.answers[0].value

    def test_timing_empty_span(self, store_with_data, span_manager):
        # Create a span with no exchanges
        span_manager.start("empty_span")
        span_manager.stop()
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="empty_span",
            questions=[Question(type="total_duration_ms")],
        ))
        assert result.answers[0].found is False


class TestAggregateQuestions:
    def test_avg_response_time(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="avg_response_time_ms")],
        ))
        # (100 + 200 + 50) / 3 ≈ 116.67
        assert result.answers[0].found is True
        assert result.answers[0].value == pytest.approx(116.667, rel=0.01)

    def test_slowest_request(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="slowest_request")],
        ))
        slowest = result.answers[0].value
        assert slowest["domain"] == "api.example.com"
        assert slowest["endpoint"] == "/users"
        assert slowest["method"] == "POST"

    def test_error_count(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="error_count")],
        ))
        assert result.answers[0].value == 1  # 404

    def test_error_count_login(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="login_test",
            questions=[Question(type="error_count")],
        ))
        assert result.answers[0].value == 1  # 500

    def test_error_rate(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="error_rate")],
        ))
        # 1 error out of 3 = 33.33%
        assert result.answers[0].value == pytest.approx(33.333, rel=0.01)

    def test_error_rate_no_errors(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="unspanned",
            questions=[Question(type="error_rate")],
        ))
        assert result.answers[0].value == 0.0

    def test_status_code_summary(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[Question(type="status_code_summary")],
        ))
        summary = result.answers[0].value
        assert summary["200"] == 1
        assert summary["201"] == 1
        assert summary["404"] == 1

    def test_status_code_summary_login(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="login_test",
            questions=[Question(type="status_code_summary")],
        ))
        summary = result.answers[0].value
        assert summary["200"] == 1
        assert summary["500"] == 1


class TestFilter:
    def test_filter_by_domain(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            filter=SpanFilter(domain="api.example.com"),
            questions=[Question(type="total_request_count")],
        ))
        assert result.answers[0].value == 2

    def test_filter_by_endpoint(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            filter=SpanFilter(endpoint="/users"),
            questions=[Question(type="total_request_count")],
        ))
        assert result.answers[0].value == 2

    def test_filter_by_method(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            filter=SpanFilter(method="GET"),
            questions=[Question(type="total_request_count")],
        ))
        assert result.answers[0].value == 2

    def test_filter_combined(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            filter=SpanFilter(domain="api.example.com", method="POST"),
            questions=[Question(type="total_request_count")],
        ))
        assert result.answers[0].value == 1


class TestMultipleQuestions:
    def test_multiple_span_questions(self, store_with_data, span_manager):
        result = execute_span_query(store_with_data, span_manager, SpanQueryRequest(
            scope="api_test",
            questions=[
                Question(type="total_request_count"),
                Question(type="domains_contacted"),
                Question(type="error_count"),
                Question(type="avg_response_time_ms"),
            ],
        ))
        assert result.found is True
        assert len(result.answers) == 4
        assert result.answers[0].value == 3
        assert len(result.answers[1].value) == 2
        assert result.answers[2].value == 1
        assert result.answers[3].found is True
