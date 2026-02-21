"""Stage 1: Scope resolution — filter exchanges by span."""

from __future__ import annotations

from wire.models import Exchange
from wire.store.data_store import DataStore


def resolve_scope(store: DataStore, scope: str) -> list[Exchange]:
    """Filter exchanges by scope.

    - "all": all exchanges
    - "unspanned": only exchanges with no span (span=None)
    - any other string: only exchanges with that span name
    """
    if scope == "all":
        return store.filter()
    if scope == "unspanned":
        return store.filter(span=None)
    return store.filter(span=scope)
