from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# --- Content Type Classification ---

class ContentType(StrEnum):
    JSON = "json"
    TEXT = "text"
    BINARY = "binary"
    EMPTY = "empty"


# --- Exchange ---

class Exchange(BaseModel):
    timestamp_start: datetime
    timestamp_end: datetime
    duration_ms: float
    span: str | None = None
    domain: str
    endpoint: str
    query_params: dict[str, str] = Field(default_factory=dict)
    method: str
    request_headers: dict[str, str | list[str]] = Field(default_factory=dict)
    request_body_raw: bytes = b""
    request_body_parsed: Any | None = None
    request_content_type: ContentType = ContentType.EMPTY
    request_content_type_raw: str = ""
    response_status: int = 0
    response_headers: dict[str, str | list[str]] = Field(default_factory=dict)
    response_body_raw: bytes = b""
    response_body_parsed: Any | None = None
    response_content_type: ContentType = ContentType.EMPTY
    response_content_type_raw: str = ""

    model_config = {"arbitrary_types_allowed": True}


# --- Error Reasons ---

class AnswerErrorReason(StrEnum):
    KEY_NOT_FOUND = "key_not_found"
    INDEX_OUT_OF_BOUNDS = "index_out_of_bounds"
    BODY_NOT_JSON = "body_not_json"
    BODY_EMPTY = "body_empty"
    HEADER_NOT_FOUND = "header_not_found"
    NOT_APPLICABLE = "not_applicable"


class QueryErrorReason(StrEnum):
    NO_MATCHING_EXCHANGE = "no_matching_exchange"
    OCCURRENCE_OUT_OF_RANGE = "occurrence_out_of_range"


# --- Query Request Models ---

class QueryTarget(BaseModel):
    domain: str | None = None
    endpoint: str | None = None
    method: str | None = None
    occurrence: int = 0


class Question(BaseModel):
    type: str
    name: str | None = None
    path: str | None = None
    substring: str | None = None
    aggregate: str | None = None


class QueryRequest(BaseModel):
    scope: str
    target: QueryTarget = Field(default_factory=QueryTarget)
    questions: list[Question] = Field(default_factory=list)


class SpanFilter(BaseModel):
    domain: str | None = None
    endpoint: str | None = None
    method: str | None = None


class SpanQueryRequest(BaseModel):
    scope: str
    filter: SpanFilter = Field(default_factory=SpanFilter)
    questions: list[Question] = Field(default_factory=list)


# --- Query Response Models ---

class AnswerResult(BaseModel):
    found: bool
    value: Any | None = None
    reason: str | None = None


class QueryResponse(BaseModel):
    found: bool
    matched_count: int = 0
    occurrence_used: int | None = None
    answers: list[AnswerResult] = Field(default_factory=list)
    reason: str | None = None


class SpanQueryResponse(BaseModel):
    found: bool
    answers: list[AnswerResult] = Field(default_factory=list)
    reason: str | None = None


# --- Span Request ---

class SpanStartRequest(BaseModel):
    name: str
