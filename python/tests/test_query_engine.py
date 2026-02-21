"""Tests for the full exchange-level query engine."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import pytest

from tests.conftest import make_exchange
from wire.models import (
    ContentType,
    QueryRequest,
    QueryTarget,
    Question,
)
from wire.store.data_store import DataStore
from wire.query.engine import execute_query


@pytest.fixture
def store_with_data():
    """DataStore pre-loaded with test exchanges."""
    store = DataStore()
    t1 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = t1 + timedelta(seconds=10)
    t3 = t1 + timedelta(seconds=20)

    store.add(make_exchange(
        span="login",
        domain="api.example.com",
        endpoint="/auth",
        method="POST",
        status=200,
        response_body=json.dumps({"token": "abc123", "user": {"name": "Alice", "id": 1}}).encode(),
        response_content_type=ContentType.JSON,
        request_body=json.dumps({"username": "alice", "password": "secret"}).encode(),
        request_content_type=ContentType.JSON,
        request_headers={"content-type": "application/json", "x-request-id": "req-001"},
        response_headers={"content-type": "application/json", "x-ratelimit": "100"},
        query_params={"redirect": "/home"},
        duration_ms=50.0,
        timestamp_start=t1,
    ))

    store.add(make_exchange(
        span="login",
        domain="api.example.com",
        endpoint="/users",
        method="GET",
        status=200,
        response_body=json.dumps([{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]).encode(),
        response_content_type=ContentType.JSON,
        response_headers={"content-type": "application/json"},
        duration_ms=30.0,
        timestamp_start=t2,
    ))

    store.add(make_exchange(
        span="login",
        domain="cdn.example.com",
        endpoint="/assets/logo.png",
        method="GET",
        status=200,
        response_body=b"\x89PNG...",
        response_content_type=ContentType.BINARY,
        response_headers={"content-type": "image/png"},
        duration_ms=10.0,
        timestamp_start=t3,
    ))

    # An unspanned exchange
    store.add(make_exchange(
        span=None,
        domain="api.example.com",
        endpoint="/health",
        method="GET",
        status=200,
        response_body=b'{"status":"ok"}',
        response_content_type=ContentType.JSON,
        response_headers={"content-type": "application/json"},
        duration_ms=5.0,
        timestamp_start=t1 + timedelta(seconds=30),
    ))

    return store


class TestScopeResolution:
    def test_scope_span(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            questions=[Question(type="request_count")],
        ))
        assert result.found is True
        assert result.answers[0].value == 3

    def test_scope_unspanned(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="unspanned",
            questions=[Question(type="request_count")],
        ))
        assert result.answers[0].value == 1

    def test_scope_all(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="all",
            questions=[Question(type="request_count")],
        ))
        assert result.answers[0].value == 4

    def test_scope_nonexistent_span(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="nonexistent",
            questions=[Question(type="response_status")],
        ))
        assert result.found is False
        assert result.reason == "no_matching_exchange"


class TestTargetResolution:
    def test_filter_by_domain(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(domain="cdn.example.com"),
            questions=[Question(type="request_count")],
        ))
        assert result.answers[0].value == 1

    def test_filter_by_endpoint(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="request_count")],
        ))
        assert result.answers[0].value == 1

    def test_filter_by_method(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(method="POST"),
            questions=[Question(type="request_count")],
        ))
        assert result.answers[0].value == 1

    def test_filter_combined(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(domain="api.example.com", method="GET"),
            questions=[Question(type="request_count")],
        ))
        assert result.answers[0].value == 1


class TestOccurrence:
    def test_first_occurrence(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(domain="api.example.com", occurrence=0),
            questions=[Question(type="response_status")],
        ))
        assert result.found is True
        assert result.occurrence_used == 0
        assert result.answers[0].value == 200

    def test_second_occurrence(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(domain="api.example.com", occurrence=1),
            questions=[Question(type="response_status")],
        ))
        assert result.found is True
        assert result.occurrence_used == 1

    def test_last_occurrence(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(domain="api.example.com", occurrence=-1),
            questions=[Question(type="response_status")],
        ))
        assert result.found is True
        assert result.occurrence_used == -1

    def test_occurrence_out_of_range(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(domain="api.example.com", occurrence=99),
            questions=[Question(type="response_status")],
        ))
        assert result.found is False
        assert result.reason == "occurrence_out_of_range"
        assert result.matched_count == 2


class TestExistenceAndCounting:
    def test_request_exists_true(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="request_exists")],
        ))
        assert result.answers[0].value is True

    def test_request_exists_false(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/nonexistent"),
            questions=[Question(type="request_exists")],
        ))
        assert result.answers[0].value is False

    def test_request_count(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            questions=[Question(type="request_count")],
        ))
        assert result.answers[0].value == 3


class TestStatusQuestion:
    def test_response_status(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth", method="POST"),
            questions=[Question(type="response_status")],
        ))
        assert result.answers[0].found is True
        assert result.answers[0].value == 200


class TestHeaderQuestions:
    def test_response_header_value(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_header_value", name="x-ratelimit")],
        ))
        assert result.answers[0].found is True
        assert result.answers[0].value == "100"

    def test_request_header_value(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="request_header_value", name="x-request-id")],
        ))
        assert result.answers[0].value == "req-001"

    def test_header_not_found(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_header_value", name="x-nonexistent")],
        ))
        assert result.answers[0].found is False
        assert result.answers[0].reason == "header_not_found"

    def test_response_header_exists_true(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_header_exists", name="content-type")],
        ))
        assert result.answers[0].value is True

    def test_response_header_exists_false(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_header_exists", name="x-nonexistent")],
        ))
        assert result.answers[0].value is False

    def test_request_header_exists(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="request_header_exists", name="content-type")],
        ))
        assert result.answers[0].value is True

    def test_header_case_insensitive(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_header_value", name="Content-Type")],
        ))
        assert result.answers[0].found is True


class TestResponseBodyQuestions:
    def test_body_key_path(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_body_key_path", path="user.name")],
        ))
        assert result.answers[0].found is True
        assert result.answers[0].value == "Alice"

    def test_body_key_path_nested(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_body_key_path", path="token")],
        ))
        assert result.answers[0].value == "abc123"

    def test_body_key_path_not_found(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_body_key_path", path="nonexistent.path")],
        ))
        assert result.answers[0].found is False
        assert result.answers[0].reason == "key_not_found"

    def test_body_key_path_array(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/users"),
            questions=[Question(type="response_body_key_path", path="[0].name")],
        ))
        assert result.answers[0].value == "Alice"

    def test_count_at_key_path(self, store_with_data):
        # /users response is a root-level array with 2 items
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/users"),
            questions=[Question(type="count_at_key_path", path="")],
        ))
        assert result.answers[0].found is True
        assert result.answers[0].value == 2

    def test_body_contains_true(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_body_contains", substring="abc123")],
        ))
        assert result.answers[0].value is True

    def test_body_contains_false(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_body_contains", substring="zzz_not_here")],
        ))
        assert result.answers[0].value is False

    def test_body_raw_json(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_body_raw")],
        ))
        assert result.answers[0].found is True
        assert isinstance(result.answers[0].value, dict)
        assert result.answers[0].value["token"] == "abc123"

    def test_response_content_type(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_content_type")],
        ))
        assert result.answers[0].value == "json"

    def test_body_not_json(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/assets/logo.png"),
            questions=[Question(type="response_body_key_path", path="key")],
        ))
        assert result.answers[0].found is False
        assert result.answers[0].reason == "body_not_json"


class TestRequestBodyQuestions:
    def test_request_body_key_path(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="request_body_key_path", path="username")],
        ))
        assert result.answers[0].value == "alice"

    def test_request_body_raw(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="request_body_raw")],
        ))
        assert result.answers[0].found is True
        assert result.answers[0].value["username"] == "alice"

    def test_request_content_type(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="request_content_type")],
        ))
        assert result.answers[0].value == "json"


class TestQueryParamQuestions:
    def test_query_param_value(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="query_param_value", name="redirect")],
        ))
        assert result.answers[0].value == "/home"

    def test_query_param_exists_true(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="query_param_exists", name="redirect")],
        ))
        assert result.answers[0].value is True

    def test_query_param_exists_false(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="query_param_exists", name="nonexistent")],
        ))
        assert result.answers[0].value is False

    def test_query_param_not_found(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="query_param_value", name="nonexistent")],
        ))
        assert result.answers[0].found is False
        assert result.answers[0].reason == "key_not_found"


class TestMetricQuestions:
    def test_response_time_ms(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_time_ms")],
        ))
        assert result.answers[0].value == 50.0

    def test_response_body_size_bytes(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_body_size_bytes")],
        ))
        assert result.answers[0].found is True
        assert result.answers[0].value > 0

    def test_request_body_size_bytes(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="request_body_size_bytes")],
        ))
        assert result.answers[0].found is True
        assert result.answers[0].value > 0


class TestAggregateMetrics:
    def test_avg_response_time(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            questions=[Question(type="response_time_ms", aggregate="avg")],
        ))
        assert result.answers[0].found is True
        # (50 + 30 + 10) / 3 = 30.0
        assert result.answers[0].value == pytest.approx(30.0)

    def test_max_response_time(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            questions=[Question(type="response_time_ms", aggregate="max")],
        ))
        assert result.answers[0].value == 50.0

    def test_min_response_time(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            questions=[Question(type="response_time_ms", aggregate="min")],
        ))
        assert result.answers[0].value == 10.0

    def test_sum_response_time(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            questions=[Question(type="response_time_ms", aggregate="sum")],
        ))
        assert result.answers[0].value == 90.0

    def test_aggregate_with_target_filter(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(domain="api.example.com"),
            questions=[Question(type="response_time_ms", aggregate="avg")],
        ))
        # (50 + 30) / 2 = 40.0
        assert result.answers[0].value == pytest.approx(40.0)


class TestMultipleQuestions:
    def test_multiple_questions_single_request(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[
                Question(type="response_status"),
                Question(type="response_body_key_path", path="token"),
                Question(type="response_header_value", name="content-type"),
                Question(type="response_time_ms"),
            ],
        ))
        assert result.found is True
        assert len(result.answers) == 4
        assert result.answers[0].value == 200
        assert result.answers[1].value == "abc123"
        assert result.answers[2].value == "application/json"
        assert result.answers[3].value == 50.0

    def test_mixed_list_and_exchange_questions(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[
                Question(type="request_count"),
                Question(type="response_status"),
            ],
        ))
        assert result.answers[0].value == 1  # count for /auth
        assert result.answers[1].value == 200


class TestResponseEnvelope:
    def test_found_envelope(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="login",
            target=QueryTarget(endpoint="/auth"),
            questions=[Question(type="response_status")],
        ))
        assert result.found is True
        assert result.matched_count == 1
        assert result.occurrence_used == 0

    def test_not_found_envelope(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="nonexistent",
            questions=[Question(type="response_status")],
        ))
        assert result.found is False
        assert result.reason == "no_matching_exchange"

    def test_list_only_query_found_even_when_empty(self, store_with_data):
        result = execute_query(store_with_data, QueryRequest(
            scope="nonexistent",
            questions=[Question(type="request_count")],
        ))
        # List questions still return found=True with value 0
        assert result.found is True
        assert result.answers[0].value == 0
