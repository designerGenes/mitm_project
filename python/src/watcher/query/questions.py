"""Stage 4: Exchange-level question evaluators (~20 types)."""

from __future__ import annotations

from watcher.models import (
    Exchange,
    Question,
    AnswerResult,
    AnswerErrorReason,
    ContentType,
)
from watcher.query.key_path import resolve_key_path
from watcher.query.aggregates import compute_aggregate


# Questions that skip occurrence and operate on the full filtered list
LIST_QUESTIONS = {"request_exists", "request_count"}

# Questions that support the aggregate modifier
METRIC_QUESTIONS = {"response_time_ms", "response_body_size_bytes", "request_body_size_bytes"}


def evaluate_question(
    question: Question,
    exchange: Exchange | None,
    matched: list[Exchange],
) -> AnswerResult:
    """Evaluate a single question.

    For list questions (request_exists, request_count), `exchange` may be None
    and `matched` is the full filtered list.

    For aggregate metrics, `exchange` is ignored and `matched` is used.
    """
    qtype = question.type

    # --- List questions (skip occurrence) ---
    if qtype == "request_exists":
        return AnswerResult(found=True, value=len(matched) > 0)

    if qtype == "request_count":
        return AnswerResult(found=True, value=len(matched))

    # --- Aggregate metrics ---
    if qtype in METRIC_QUESTIONS and question.aggregate:
        return _evaluate_aggregate_metric(question, matched)

    # --- All remaining questions require a selected exchange ---
    if exchange is None:
        return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)

    # --- Status ---
    if qtype == "response_status":
        return AnswerResult(found=True, value=exchange.response_status)

    # --- Headers ---
    if qtype == "response_header_value":
        return _header_value(exchange.response_headers, question.name)

    if qtype == "request_header_value":
        return _header_value(exchange.request_headers, question.name)

    if qtype == "response_header_exists":
        return _header_exists(exchange.response_headers, question.name)

    if qtype == "request_header_exists":
        return _header_exists(exchange.request_headers, question.name)

    # --- Body: Response ---
    if qtype == "response_body_key_path":
        return _body_key_path(exchange.response_body_parsed, exchange.response_content_type, question.path)

    if qtype == "count_at_key_path":
        return _count_at_key_path(exchange.response_body_parsed, exchange.response_content_type, question.path)

    if qtype == "response_body_contains":
        return _body_contains(exchange.response_body_raw, question.substring)

    if qtype == "response_body_raw":
        return _body_raw(exchange.response_body_raw, exchange.response_body_parsed, exchange.response_content_type)

    if qtype == "response_content_type":
        return AnswerResult(found=True, value=str(exchange.response_content_type))

    # --- Body: Request ---
    if qtype == "request_body_key_path":
        return _body_key_path(exchange.request_body_parsed, exchange.request_content_type, question.path)

    if qtype == "request_body_raw":
        return _body_raw(exchange.request_body_raw, exchange.request_body_parsed, exchange.request_content_type)

    if qtype == "request_content_type":
        return AnswerResult(found=True, value=str(exchange.request_content_type))

    # --- Query Params ---
    if qtype == "query_param_value":
        return _query_param_value(exchange, question.name)

    if qtype == "query_param_exists":
        return _query_param_exists(exchange, question.name)

    # --- Metrics ---
    if qtype == "response_time_ms":
        return AnswerResult(found=True, value=exchange.duration_ms)

    if qtype == "response_body_size_bytes":
        return AnswerResult(found=True, value=len(exchange.response_body_raw))

    if qtype == "request_body_size_bytes":
        return AnswerResult(found=True, value=len(exchange.request_body_raw))

    return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)


# --- Helper functions ---

def _header_value(
    headers: dict[str, str | list[str]], name: str | None
) -> AnswerResult:
    if name is None:
        return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
    key = name.lower()
    if key in headers:
        return AnswerResult(found=True, value=headers[key])
    return AnswerResult(found=False, reason=AnswerErrorReason.HEADER_NOT_FOUND)


def _header_exists(
    headers: dict[str, str | list[str]], name: str | None
) -> AnswerResult:
    if name is None:
        return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
    key = name.lower()
    return AnswerResult(found=True, value=key in headers)


def _body_key_path(
    parsed: object | None, content_type: ContentType, path: str | None
) -> AnswerResult:
    if path is None:
        return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
    if content_type == ContentType.EMPTY:
        return AnswerResult(found=False, reason=AnswerErrorReason.BODY_EMPTY)
    if parsed is None:
        return AnswerResult(found=False, reason=AnswerErrorReason.BODY_NOT_JSON)
    found, value, reason = resolve_key_path(parsed, path)
    if found:
        return AnswerResult(found=True, value=value)
    return AnswerResult(found=False, reason=reason)


def _count_at_key_path(
    parsed: object | None, content_type: ContentType, path: str | None
) -> AnswerResult:
    if path is None:
        return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
    if content_type == ContentType.EMPTY:
        return AnswerResult(found=False, reason=AnswerErrorReason.BODY_EMPTY)
    if parsed is None:
        return AnswerResult(found=False, reason=AnswerErrorReason.BODY_NOT_JSON)
    found, value, reason = resolve_key_path(parsed, path)
    if not found:
        return AnswerResult(found=False, reason=reason)
    if not isinstance(value, list):
        return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
    return AnswerResult(found=True, value=len(value))


def _body_contains(body_raw: bytes, substring: str | None) -> AnswerResult:
    if substring is None:
        return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
    if not body_raw:
        return AnswerResult(found=True, value=False)
    try:
        text = body_raw.decode("utf-8", errors="replace")
    except Exception:
        text = ""
    return AnswerResult(found=True, value=substring in text)


def _body_raw(
    body_raw: bytes, body_parsed: object | None, content_type: ContentType
) -> AnswerResult:
    if content_type == ContentType.EMPTY:
        return AnswerResult(found=True, value=None)
    if body_parsed is not None:
        return AnswerResult(found=True, value=body_parsed)
    try:
        return AnswerResult(found=True, value=body_raw.decode("utf-8", errors="replace"))
    except Exception:
        return AnswerResult(found=True, value=None)


def _query_param_value(exchange: Exchange, name: str | None) -> AnswerResult:
    if name is None:
        return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
    if name in exchange.query_params:
        return AnswerResult(found=True, value=exchange.query_params[name])
    return AnswerResult(found=False, reason=AnswerErrorReason.KEY_NOT_FOUND)


def _query_param_exists(exchange: Exchange, name: str | None) -> AnswerResult:
    if name is None:
        return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
    return AnswerResult(found=True, value=name in exchange.query_params)


def _evaluate_aggregate_metric(
    question: Question, matched: list[Exchange]
) -> AnswerResult:
    """Evaluate a metrics question with an aggregate across all matched exchanges."""
    qtype = question.type
    values: list[float | int] = []
    for ex in matched:
        if qtype == "response_time_ms":
            values.append(ex.duration_ms)
        elif qtype == "response_body_size_bytes":
            values.append(len(ex.response_body_raw))
        elif qtype == "request_body_size_bytes":
            values.append(len(ex.request_body_raw))

    if not values:
        return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)

    result = compute_aggregate(values, question.aggregate)
    if result is None:
        return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
    return AnswerResult(found=True, value=result)
