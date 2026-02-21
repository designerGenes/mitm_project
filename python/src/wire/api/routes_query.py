from __future__ import annotations

from fastapi import APIRouter, Request

from wire.models import QueryRequest
from wire.query.engine import execute_query

router = APIRouter()


@router.post("/query")
async def query(body: QueryRequest, request: Request):
    data_store = request.app.state.data_store
    result = execute_query(data_store, body)
    return result
