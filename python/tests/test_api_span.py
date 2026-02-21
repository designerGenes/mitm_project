import pytest


@pytest.mark.asyncio
class TestSpanStart:
    async def test_start_span(self, client):
        resp = await client.post("/span/start", json={"name": "test_span"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "started"
        assert data["name"] == "test_span"

    async def test_start_span_auto_closes(self, client):
        await client.post("/span/start", json={"name": "span1"})
        resp = await client.post("/span/start", json={"name": "span2"})
        data = resp.json()
        assert data["status"] == "started"
        assert data["name"] == "span2"
        assert data["auto_closed"] == "span1"

    async def test_start_span_missing_name(self, client):
        resp = await client.post("/span/start", json={})
        assert resp.status_code == 422  # Validation error


@pytest.mark.asyncio
class TestSpanStop:
    async def test_stop_active_span(self, client):
        await client.post("/span/start", json={"name": "span1"})
        resp = await client.post("/span/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "stopped"
        assert data["name"] == "span1"

    async def test_stop_no_active_span(self, client):
        resp = await client.post("/span/stop")
        data = resp.json()
        assert data["status"] == "no_active_span"


@pytest.mark.asyncio
class TestSpanIntegration:
    async def test_start_stop_start(self, client):
        await client.post("/span/start", json={"name": "span1"})
        await client.post("/span/stop")

        resp = await client.get("/status")
        assert resp.json()["current_span"] is None

        await client.post("/span/start", json={"name": "span2"})
        resp = await client.get("/status")
        assert resp.json()["current_span"] == "span2"

    async def test_reset_clears_spans(self, client):
        await client.post("/span/start", json={"name": "span1"})
        await client.post("/reset")
        resp = await client.get("/status")
        data = resp.json()
        assert data["current_span"] is None
        assert data["spans"] == {}
