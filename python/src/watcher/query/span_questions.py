"""Span-level question evaluators (13 types)."""

from __future__ import annotations

from collections import Counter

from watcher.models import Exchange, Question, AnswerResult, AnswerErrorReason


def evaluate_span_question(
    question: Question,
    exchanges: list[Exchange],
) -> AnswerResult:
    """Evaluate a single span-level question against filtered exchanges."""
    qtype = question.type

    # --- Inventory ---
    if qtype == "total_request_count":
        return AnswerResult(found=True, value=len(exchanges))

    if qtype == "domains_contacted":
        domains = sorted(set(e.domain for e in exchanges))
        return AnswerResult(found=True, value=domains)

    if qtype == "endpoints_contacted":
        endpoints = sorted(set(e.endpoint for e in exchanges))
        return AnswerResult(found=True, value=endpoints)

    if qtype == "methods_used":
        methods = sorted(set(e.method for e in exchanges))
        return AnswerResult(found=True, value=methods)

    if qtype == "unique_exchanges":
        counter: Counter[tuple[str, str, str]] = Counter()
        for e in exchanges:
            counter[(e.domain, e.endpoint, e.method)] += 1
        result = [
            {"domain": d, "endpoint": ep, "method": m, "count": c}
            for (d, ep, m), c in sorted(counter.items())
        ]
        return AnswerResult(found=True, value=result)

    # --- Timing ---
    if qtype == "total_duration_ms":
        if not exchanges:
            return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
        first_start = min(e.timestamp_start for e in exchanges)
        last_end = max(e.timestamp_end for e in exchanges)
        ms = (last_end - first_start).total_seconds() * 1000
        return AnswerResult(found=True, value=ms)

    if qtype == "span_start_time":
        if not exchanges:
            return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
        earliest = min(e.timestamp_start for e in exchanges)
        return AnswerResult(found=True, value=earliest.isoformat())

    if qtype == "span_end_time":
        if not exchanges:
            return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
        latest = max(e.timestamp_end for e in exchanges)
        return AnswerResult(found=True, value=latest.isoformat())

    # --- Aggregates ---
    if qtype == "avg_response_time_ms":
        if not exchanges:
            return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
        avg = sum(e.duration_ms for e in exchanges) / len(exchanges)
        return AnswerResult(found=True, value=avg)

    if qtype == "slowest_request":
        if not exchanges:
            return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
        # Find the slowest, tracking its occurrence index among same domain/endpoint/method
        slowest = max(exchanges, key=lambda e: e.duration_ms)
        # Count occurrence: how many exchanges with the same signature appear before it
        occurrence = 0
        for e in sorted(exchanges, key=lambda e: e.timestamp_start):
            if e is slowest:
                break
            if e.domain == slowest.domain and e.endpoint == slowest.endpoint and e.method == slowest.method:
                occurrence += 1
        return AnswerResult(found=True, value={
            "domain": slowest.domain,
            "endpoint": slowest.endpoint,
            "method": slowest.method,
            "occurrence": occurrence,
        })

    if qtype == "error_count":
        count = sum(1 for e in exchanges if e.response_status >= 400)
        return AnswerResult(found=True, value=count)

    if qtype == "error_rate":
        if not exchanges:
            return AnswerResult(found=True, value=0.0)
        errors = sum(1 for e in exchanges if e.response_status >= 400)
        return AnswerResult(found=True, value=(errors / len(exchanges)) * 100)

    if qtype == "status_code_summary":
        counter: Counter[int] = Counter()
        for e in exchanges:
            counter[e.response_status] += 1
        summary = {str(code): count for code, count in sorted(counter.items())}
        return AnswerResult(found=True, value=summary)

    return AnswerResult(found=False, reason=AnswerErrorReason.NOT_APPLICABLE)
