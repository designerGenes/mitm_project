from __future__ import annotations

from watcher.models import Exchange


class DataStore:
    """In-memory store for captured HTTP exchanges."""

    def __init__(self) -> None:
        self._exchanges: list[Exchange] = []

    @property
    def exchanges(self) -> list[Exchange]:
        return self._exchanges

    def add(self, exchange: Exchange) -> None:
        self._exchanges.append(exchange)

    def reset(self) -> None:
        self._exchanges.clear()

    def count(self) -> int:
        return len(self._exchanges)

    def filter(
        self,
        *,
        span: str | None = ...,  # sentinel: ... means "don't filter"
        domain: str | None = None,
        endpoint: str | None = None,
        method: str | None = None,
    ) -> list[Exchange]:
        """Filter exchanges by optional criteria.

        For span filtering:
          - span=... (default/Ellipsis): no span filter applied
          - span=None: only unspanned exchanges
          - span="name": only that span
        """
        result = self._exchanges

        if span is not ...:
            result = [e for e in result if e.span == span]

        if domain is not None:
            domain_lower = domain.lower()
            result = [e for e in result if e.domain == domain_lower]

        if endpoint is not None:
            ep = endpoint.rstrip("/") or "/"
            result = [e for e in result if e.endpoint == ep]

        if method is not None:
            method_upper = method.upper()
            result = [e for e in result if e.method == method_upper]

        return sorted(result, key=lambda e: e.timestamp_start)
