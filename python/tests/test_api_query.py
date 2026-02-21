"""Tests for POST /query HTTP endpoint."""

from __future__ import annotations

import json

import pytest

from tests.conftest import make_exchange
from watcher.models import ContentType


@pytest.mark.asyncio
class TestQueryEndpoint:
    async def _seed(self, data_store, span_manager):
        """Seed test data."""
        span_manager.start("test_span")
        data_store.add(make_exchange(
            span="test_span",
            domain="api.example.com",
            endpoint="/users",
            method="GET",
            status=200,
            response_body=json.dumps({"users": [{"name": "Alice"}]}).encode(),
            response_content_type=ContentType.JSON,
            response_headers={"content-type": "application/json"},
        ))

    async def test_query_response_status(self, client, data_store, span_manager):
        await self._seed(data_store, span_manager)
        resp = await client.post("/query", json={
            "scope": "test_span",
            "target": {"endpoint": "/users"},
            "questions": [{"type": "response_status"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["answers"][0]["value"] == 200

    async def test_query_key_path(self, client, data_store, span_manager):
        await self._seed(data_store, span_manager)
        resp = await client.post("/query", json={
            "scope": "test_span",
            "target": {"endpoint": "/users"},
            "questions": [{"type": "response_body_key_path", "path": "users[0].name"}],
        })
        data = resp.json()
        assert data["answers"][0]["value"] == "Alice"

    async def test_query_not_found(self, client, data_store, span_manager):
        await self._seed(data_store, span_manager)
        resp = await client.post("/query", json={
            "scope": "nonexistent",
            "questions": [{"type": "response_status"}],
        })
        data = resp.json()
        assert data["found"] is False
        assert data["reason"] == "no_matching_exchange"

    async def test_query_request_count(self, client, data_store, span_manager):
        await self._seed(data_store, span_manager)
        resp = await client.post("/query", json={
            "scope": "test_span",
            "questions": [{"type": "request_count"}],
        })
        data = resp.json()
        assert data["found"] is True
        assert data["answers"][0]["value"] == 1

    async def test_query_multiple_questions(self, client, data_store, span_manager):
        await self._seed(data_store, span_manager)
        resp = await client.post("/query", json={
            "scope": "test_span",
            "target": {"endpoint": "/users"},
            "questions": [
                {"type": "response_status"},
                {"type": "request_count"},
                {"type": "response_content_type"},
            ],
        })
        data = resp.json()
        assert len(data["answers"]) == 3
        assert data["answers"][0]["value"] == 200
        assert data["answers"][1]["value"] == 1
        assert data["answers"][2]["value"] == "json"

    async def test_query_validation_error(self, client):
        resp = await client.post("/query", json={})
        assert resp.status_code == 422
