"""Span-level query orchestrator for POST /span/query."""

from __future__ import annotations

from watcher.models import SpanQueryRequest, SpanQueryResponse, AnswerResult
from watcher.store.data_store import DataStore
from watcher.store.span_manager import SpanManager
from watcher.query.scope import resolve_scope
from watcher.query.span_questions import evaluate_span_question


def execute_span_query(
    store: DataStore,
    span_manager: SpanManager,
    request: SpanQueryRequest,
) -> SpanQueryResponse:
    """Execute a span-level query."""

    # Check if the span exists (for named spans)
    scope = request.scope
    if scope not in ("all", "unspanned") and not span_manager.has_span(scope):
        # Also check if any exchanges are tagged with this span
        exchanges = resolve_scope(store, scope)
        if not exchanges:
            return SpanQueryResponse(found=False, reason="span_not_found")

    # Resolve scope
    exchanges = resolve_scope(store, scope)

    # Apply optional filter
    f = request.filter
    if f.domain is not None:
        domain_lower = f.domain.lower()
        exchanges = [e for e in exchanges if e.domain == domain_lower]
    if f.endpoint is not None:
        ep = f.endpoint.rstrip("/") or "/"
        exchanges = [e for e in exchanges if e.endpoint == ep]
    if f.method is not None:
        method_upper = f.method.upper()
        exchanges = [e for e in exchanges if e.method == method_upper]

    # Evaluate questions
    answers = [
        evaluate_span_question(question, exchanges)
        for question in request.questions
    ]

    return SpanQueryResponse(found=True, answers=answers)
