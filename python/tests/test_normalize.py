from wire.capture.normalize import (
    classify_content_type,
    normalize_headers,
    normalize_method,
    normalize_domain,
    parse_url,
    try_parse_json,
)
from wire.models import ContentType


class TestClassifyContentType:
    def test_json(self):
        assert classify_content_type("application/json", b"{}") == ContentType.JSON

    def test_json_charset(self):
        assert classify_content_type("application/json; charset=utf-8", b"{}") == ContentType.JSON

    def test_json_variant(self):
        assert classify_content_type("application/vnd.api+json", b"{}") == ContentType.JSON

    def test_text_plain(self):
        assert classify_content_type("text/plain", b"hello") == ContentType.TEXT

    def test_text_html(self):
        assert classify_content_type("text/html", b"<html>") == ContentType.TEXT

    def test_binary(self):
        assert classify_content_type("application/octet-stream", b"\x00") == ContentType.BINARY

    def test_image(self):
        assert classify_content_type("image/png", b"\x89PNG") == ContentType.BINARY

    def test_empty_body(self):
        assert classify_content_type("application/json", b"") == ContentType.EMPTY

    def test_no_content_type(self):
        assert classify_content_type("", b"data") == ContentType.BINARY


class TestNormalizeHeaders:
    def test_lowercase_keys(self):
        result = normalize_headers({"Content-Type": "application/json", "X-Custom": "val"})
        assert "content-type" in result
        assert "x-custom" in result

    def test_empty(self):
        assert normalize_headers({}) == {}


class TestNormalizeMethods:
    def test_uppercase(self):
        assert normalize_method("get") == "GET"
        assert normalize_method("Post") == "POST"

    def test_already_upper(self):
        assert normalize_method("DELETE") == "DELETE"


class TestNormalizeDomain:
    def test_lowercase(self):
        assert normalize_domain("API.Example.COM") == "api.example.com"


class TestParseUrl:
    def test_basic(self):
        domain, endpoint, params = parse_url("https://api.example.com/users/123")
        assert domain == "api.example.com"
        assert endpoint == "/users/123"
        assert params == {}

    def test_trailing_slash(self):
        _, endpoint, _ = parse_url("https://example.com/users/")
        assert endpoint == "/users"

    def test_query_params(self):
        _, endpoint, params = parse_url("https://example.com/search?q=test&page=1")
        assert endpoint == "/search"
        assert params == {"q": "test", "page": "1"}

    def test_root_path(self):
        _, endpoint, _ = parse_url("https://example.com/")
        assert endpoint == "/"

    def test_root_no_slash(self):
        _, endpoint, _ = parse_url("https://example.com")
        assert endpoint == "/"


class TestTryParseJson:
    def test_valid_json(self):
        result = try_parse_json(b'{"key": "value"}')
        assert result == {"key": "value"}

    def test_invalid_json(self):
        assert try_parse_json(b"not json") is None

    def test_empty(self):
        assert try_parse_json(b"") is None

    def test_array(self):
        result = try_parse_json(b'[1, 2, 3]')
        assert result == [1, 2, 3]
