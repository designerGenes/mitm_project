from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/status")
async def status(request: Request):
    config = request.app.state.config
    data_store = request.app.state.data_store
    span_manager = request.app.state.span_manager

    return {
        "config": config.to_dict(),
        "current_span": span_manager.current_span,
        "spans": span_manager.spans,
        "exchange_count": data_store.count(),
    }


@router.post("/reset")
async def reset(request: Request):
    data_store = request.app.state.data_store
    span_manager = request.app.state.span_manager
    disk_writer = request.app.state.disk_writer
    data_store.reset()
    span_manager.reset()
    if disk_writer is not None:
        disk_writer.reset()
    return {"status": "reset"}


@router.post("/admin/shutdown")
async def shutdown(request: Request):
    shutdown_event = request.app.state.shutdown_event
    if shutdown_event is not None:
        shutdown_event.set()
    return {"status": "shutting_down"}
