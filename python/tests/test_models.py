from datetime import datetime, timezone

from watcher.models import (
    Exchange,
    ContentType,
    QueryTarget,
    QueryRequest,
    SpanStartRequest,
    AnswerResult,
    QueryResponse,
)


class TestExchange:
    def test_create_minimal(self):
        now = datetime.now(timezone.utc)
        ex = Exchange(
            timestamp_start=now,
            timestamp_end=now,
            duration_ms=0,
            domain="example.com",
            endpoint="/test",
            method="GET",
        )
        assert ex.domain == "example.com"
        assert ex.span is None
        assert ex.request_content_type == ContentType.EMPTY

    def test_content_type_enum(self):
        assert ContentType.JSON == "json"
        assert ContentType.TEXT == "text"
        assert ContentType.BINARY == "binary"
        assert ContentType.EMPTY == "empty"


class TestQueryModels:
    def test_query_target_defaults(self):
        t = QueryTarget()
        assert t.domain is None
        assert t.occurrence == 0

    def test_query_request_parse(self):
        req = QueryRequest(
            scope="span1",
            target=QueryTarget(domain="api.example.com", method="GET"),
            questions=[],
        )
        assert req.scope == "span1"
        assert req.target.domain == "api.example.com"

    def test_span_start_request(self):
        r = SpanStartRequest(name="test_span")
        assert r.name == "test_span"


class TestResponseModels:
    def test_answer_result(self):
        a = AnswerResult(found=True, value=200)
        assert a.found is True
        assert a.value == 200

    def test_query_response(self):
        r = QueryResponse(
            found=True,
            matched_count=1,
            occurrence_used=0,
            answers=[AnswerResult(found=True, value="ok")],
        )
        assert r.matched_count == 1
