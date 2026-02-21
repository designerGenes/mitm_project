"""5-stage query pipeline orchestrator for exchange-level queries."""

from __future__ import annotations

from wire.models import QueryRequest, QueryResponse, QueryErrorReason
from wire.store.data_store import DataStore
from wire.query.scope import resolve_scope
from wire.query.target import resolve_target
from wire.query.occurrence import select_occurrence
from wire.query.questions import evaluate_question, LIST_QUESTIONS, METRIC_QUESTIONS
from wire.query.response import format_not_found, format_response


def execute_query(store: DataStore, request: QueryRequest) -> QueryResponse:
    """Execute a full exchange-level query through the 5-stage pipeline."""

    # Stage 1: Scope resolution
    scoped = resolve_scope(store, request.scope)

    # Stage 2: Target resolution
    matched = resolve_target(scoped, request.target)
    matched_count = len(matched)

    # Check if any questions are list-only (skip occurrence)
    has_only_list_questions = all(
        q.type in LIST_QUESTIONS or (q.type in METRIC_QUESTIONS and q.aggregate)
        for q in request.questions
    )

    # If no matches and not all questions are list questions, return not found
    if matched_count == 0 and not has_only_list_questions:
        return format_not_found(QueryErrorReason.NO_MATCHING_EXCHANGE)

    # Stage 3: Occurrence selection (for questions that need a specific exchange)
    exchange = None
    occurrence_used = None
    needs_occurrence = any(
        q.type not in LIST_QUESTIONS and not (q.type in METRIC_QUESTIONS and q.aggregate)
        for q in request.questions
    )

    if needs_occurrence and matched_count > 0:
        exchange = select_occurrence(matched, request.target.occurrence)
        if exchange is None:
            return format_not_found(
                QueryErrorReason.OCCURRENCE_OUT_OF_RANGE,
                matched_count=matched_count,
            )
        occurrence_used = request.target.occurrence

    # Stage 4: Question evaluation
    answers = [
        evaluate_question(question, exchange, matched)
        for question in request.questions
    ]

    # Stage 5: Response formatting
    return format_response(answers, matched_count, occurrence_used)
