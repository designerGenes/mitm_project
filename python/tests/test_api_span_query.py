"""Tests for POST /span/query HTTP endpoint."""

from __future__ import annotations

import json

import pytest

from tests.conftest import make_exchange
from watcher.models import ContentType


@pytest.mark.asyncio
class TestSpanQueryEndpoint:
    async def _seed(self, data_store, span_manager):
        span_manager.start("test_span")
        data_store.add(make_exchange(
            span="test_span",
            domain="api.example.com",
            endpoint="/users",
            method="GET",
            status=200,
            duration_ms=100.0,
        ))
        data_store.add(make_exchange(
            span="test_span",
            domain="api.example.com",
            endpoint="/users",
            method="POST",
            status=201,
            duration_ms=200.0,
        ))
        span_manager.stop()

    async def test_total_request_count(self, client, data_store, span_manager):
        await self._seed(data_store, span_manager)
        resp = await client.post("/span/query", json={
            "scope": "test_span",
            "questions": [{"type": "total_request_count"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["answers"][0]["value"] == 2

    async def test_domains_contacted(self, client, data_store, span_manager):
        await self._seed(data_store, span_manager)
        resp = await client.post("/span/query", json={
            "scope": "test_span",
            "questions": [{"type": "domains_contacted"}],
        })
        data = resp.json()
        assert data["answers"][0]["value"] == ["api.example.com"]

    async def test_span_not_found(self, client, data_store, span_manager):
        resp = await client.post("/span/query", json={
            "scope": "nonexistent",
            "questions": [{"type": "total_request_count"}],
        })
        data = resp.json()
        assert data["found"] is False

    async def test_with_filter(self, client, data_store, span_manager):
        await self._seed(data_store, span_manager)
        resp = await client.post("/span/query", json={
            "scope": "test_span",
            "filter": {"method": "POST"},
            "questions": [{"type": "total_request_count"}],
        })
        data = resp.json()
        assert data["answers"][0]["value"] == 1

    async def test_status_code_summary(self, client, data_store, span_manager):
        await self._seed(data_store, span_manager)
        resp = await client.post("/span/query", json={
            "scope": "test_span",
            "questions": [{"type": "status_code_summary"}],
        })
        data = resp.json()
        summary = data["answers"][0]["value"]
        assert summary["200"] == 1
        assert summary["201"] == 1

    async def test_multiple_questions(self, client, data_store, span_manager):
        await self._seed(data_store, span_manager)
        resp = await client.post("/span/query", json={
            "scope": "test_span",
            "questions": [
                {"type": "total_request_count"},
                {"type": "methods_used"},
                {"type": "error_count"},
            ],
        })
        data = resp.json()
        assert len(data["answers"]) == 3
        assert data["answers"][0]["value"] == 2
        assert data["answers"][1]["value"] == ["GET", "POST"]
        assert data["answers"][2]["value"] == 0
