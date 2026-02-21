import pytest

from tests.conftest import make_exchange


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
class TestStatusEndpoint:
    async def test_status_empty(self, client):
        resp = await client.get("/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_span"] is None
        assert data["exchange_count"] == 0
        assert "config" in data

    async def test_status_with_span(self, client, span_manager):
        span_manager.start("test_span")
        resp = await client.get("/status")
        data = resp.json()
        assert data["current_span"] == "test_span"

    async def test_status_with_exchanges(self, client, data_store):
        data_store.add(make_exchange())
        data_store.add(make_exchange())
        resp = await client.get("/status")
        data = resp.json()
        assert data["exchange_count"] == 2


@pytest.mark.asyncio
class TestResetEndpoint:
    async def test_reset(self, client, data_store, span_manager):
        data_store.add(make_exchange())
        span_manager.start("span1")

        resp = await client.post("/reset")
        assert resp.status_code == 200
        assert resp.json() == {"status": "reset"}
        assert data_store.count() == 0
        assert span_manager.current_span is None


@pytest.mark.asyncio
class TestShutdownEndpoint:
    async def test_shutdown(self, client):
        resp = await client.post("/admin/shutdown")
        assert resp.status_code == 200
        assert resp.json() == {"status": "shutting_down"}
