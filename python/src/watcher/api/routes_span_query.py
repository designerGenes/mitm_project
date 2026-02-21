from __future__ import annotations

from fastapi import APIRouter, Request

from watcher.models import SpanQueryRequest
from watcher.query.span_engine import execute_span_query

router = APIRouter()


@router.post("/span/query")
async def span_query(body: SpanQueryRequest, request: Request):
    data_store = request.app.state.data_store
    span_manager = request.app.state.span_manager
    result = execute_span_query(data_store, span_manager, body)
    return result
