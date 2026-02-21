"""Stage 2: Target resolution — filter by domain/endpoint/method."""

from __future__ import annotations

from wire.models import Exchange, QueryTarget


def resolve_target(exchanges: list[Exchange], target: QueryTarget) -> list[Exchange]:
    """Further filter exchanges by target fields. All fields are optional."""
    result = exchanges

    if target.domain is not None:
        domain_lower = target.domain.lower()
        result = [e for e in result if e.domain == domain_lower]

    if target.endpoint is not None:
        ep = target.endpoint.rstrip("/") or "/"
        result = [e for e in result if e.endpoint == ep]

    if target.method is not None:
        method_upper = target.method.upper()
        result = [e for e in result if e.method == method_upper]

    return result
