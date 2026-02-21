from __future__ import annotations

from fastapi import APIRouter, Request

from watcher.models import SpanStartRequest

router = APIRouter(prefix="/span")


@router.post("/start")
async def span_start(body: SpanStartRequest, request: Request):
    span_manager = request.app.state.span_manager
    auto_closed = span_manager.start(body.name)
    result = {"status": "started", "name": body.name}
    if auto_closed:
        result["auto_closed"] = auto_closed
    return result


@router.post("/stop")
async def span_stop(request: Request):
    span_manager = request.app.state.span_manager
    stopped = span_manager.stop()
    if stopped is None:
        return {"status": "no_active_span"}
    return {"status": "stopped", "name": stopped}
