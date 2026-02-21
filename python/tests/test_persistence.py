"""Tests for the write-behind disk persistence layer."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from tests.conftest import make_exchange
from wire.models import ContentType
from wire.persistence.writer import DiskWriter


@pytest.fixture
def output_dir(tmp_path):
    return tmp_path / "traffic"


@pytest.fixture
def writer(output_dir):
    return DiskWriter(output_dir)


class TestDiskWriter:
    def test_write_creates_directory_structure(self, writer, output_dir):
        ex = make_exchange(
            span="test_span",
            domain="api.example.com",
            endpoint="/users",
            method="GET",
            status=200,
        )
        path = writer.write(ex)

        assert path.exists()
        assert (path / "request").is_dir()
        assert (path / "response").is_dir()
        assert (path / "request" / "headers.json").exists()
        assert (path / "request" / "body.json").exists()
        assert (path / "response" / "headers.json").exists()
        assert (path / "response" / "body.json").exists()
        assert (path / "response" / "status.json").exists()

    def test_folder_hierarchy_spanned(self, writer, output_dir):
        ex = make_exchange(
            span="login",
            domain="api.example.com",
            endpoint="/auth",
            method="POST",
        )
        path = writer.write(ex)

        # Verify path structure: output/spans/login/api.example.com/auth/POST/<datetime>/
        rel = path.relative_to(output_dir)
        parts = rel.parts
        assert parts[0] == "spans"
        assert parts[1] == "login"
        assert parts[2] == "api.example.com"
        assert parts[3] == "auth"
        assert parts[4] == "POST"
        # parts[5] is the datetime

    def test_folder_hierarchy_unspanned(self, writer, output_dir):
        ex = make_exchange(
            span=None,
            domain="api.example.com",
            endpoint="/health",
            method="GET",
        )
        path = writer.write(ex)

        rel = path.relative_to(output_dir)
        assert rel.parts[0] == "unspanned"
        assert rel.parts[1] == "api.example.com"

    def test_nested_endpoint_path(self, writer, output_dir):
        ex = make_exchange(
            span="test",
            domain="api.example.com",
            endpoint="/api/v1/users",
            method="GET",
        )
        path = writer.write(ex)

        rel = path.relative_to(output_dir)
        # spans/test/api.example.com/api/v1/users/GET/<datetime>
        assert "api" in rel.parts
        assert "v1" in rel.parts
        assert "users" in rel.parts

    def test_response_status_json(self, writer):
        ex = make_exchange(status=201)
        path = writer.write(ex)

        status_file = path / "response" / "status.json"
        data = json.loads(status_file.read_text())
        assert data["status_code"] == 201

    def test_response_headers_json(self, writer):
        ex = make_exchange(
            response_headers={"content-type": "application/json", "x-custom": "val"},
        )
        path = writer.write(ex)

        headers_file = path / "response" / "headers.json"
        data = json.loads(headers_file.read_text())
        assert data["content-type"] == "application/json"
        assert data["x-custom"] == "val"

    def test_request_headers_json(self, writer):
        ex = make_exchange(
            request_headers={"authorization": "Bearer token123"},
        )
        path = writer.write(ex)

        headers_file = path / "request" / "headers.json"
        data = json.loads(headers_file.read_text())
        assert data["authorization"] == "Bearer token123"

    def test_json_body_written(self, writer):
        body_data = {"name": "Alice", "id": 1}
        ex = make_exchange(
            response_body=json.dumps(body_data).encode(),
            response_content_type=ContentType.JSON,
        )
        path = writer.write(ex)

        body_file = path / "response" / "body.json"
        data = json.loads(body_file.read_text())
        assert data == body_data

    def test_text_body_written(self, writer):
        ex = make_exchange(
            response_body=b"Hello, world!",
            response_content_type=ContentType.TEXT,
        )
        path = writer.write(ex)

        body_file = path / "response" / "body.json"
        data = json.loads(body_file.read_text())
        assert data == "Hello, world!"

    def test_empty_body_written_as_null(self, writer):
        ex = make_exchange(
            response_body=b"",
            response_content_type=ContentType.EMPTY,
        )
        path = writer.write(ex)

        body_file = path / "response" / "body.json"
        data = json.loads(body_file.read_text())
        assert data is None

    def test_binary_body_written_raw(self, writer):
        binary = b"\x89PNG\r\n\x1a\n"
        ex = make_exchange(
            response_body=binary,
            response_content_type=ContentType.BINARY,
        )
        path = writer.write(ex)

        body_file = path / "response" / "body.json"
        assert body_file.read_bytes() == binary

    def test_request_json_body(self, writer):
        body_data = {"username": "alice"}
        ex = make_exchange(
            request_body=json.dumps(body_data).encode(),
            request_content_type=ContentType.JSON,
        )
        path = writer.write(ex)

        body_file = path / "request" / "body.json"
        data = json.loads(body_file.read_text())
        assert data == body_data

    def test_multiple_exchanges_different_dirs(self, writer):
        t1 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = t1 + timedelta(seconds=5)

        ex1 = make_exchange(span="s1", endpoint="/a", timestamp_start=t1)
        ex2 = make_exchange(span="s1", endpoint="/a", timestamp_start=t2)

        path1 = writer.write(ex1)
        path2 = writer.write(ex2)

        # Different datetime layer → different directories
        assert path1 != path2
        assert path1.exists()
        assert path2.exists()


class TestDiskWriterReset:
    def test_reset_removes_directory(self, writer, output_dir):
        ex = make_exchange(span="test")
        writer.write(ex)
        assert output_dir.exists()

        writer.reset()
        assert not output_dir.exists()

    def test_reset_when_no_directory(self, writer, output_dir):
        # Should not raise
        writer.reset()
        assert not output_dir.exists()


class TestRootEndpoint:
    def test_root_endpoint_uses_placeholder(self, writer, output_dir):
        ex = make_exchange(endpoint="/")
        path = writer.write(ex)

        rel = path.relative_to(output_dir)
        assert "_root" in rel.parts
