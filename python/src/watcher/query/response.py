"""Stage 5: Response formatting — wrap answers in the standard envelope."""

from __future__ import annotations

from watcher.models import AnswerResult, QueryResponse, QueryErrorReason


def format_not_found(reason: QueryErrorReason, matched_count: int = 0) -> QueryResponse:
    return QueryResponse(
        found=False,
        matched_count=matched_count,
        reason=str(reason),
    )


def format_response(
    answers: list[AnswerResult],
    matched_count: int,
    occurrence_used: int | None,
) -> QueryResponse:
    return QueryResponse(
        found=True,
        matched_count=matched_count,
        occurrence_used=occurrence_used,
        answers=answers,
    )
