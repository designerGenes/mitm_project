"""Aggregate functions for metrics questions."""

from __future__ import annotations


def compute_aggregate(values: list[float | int], aggregate: str) -> float | int | None:
    """Compute an aggregate over a list of numeric values."""
    if not values:
        return None
    match aggregate:
        case "avg":
            return sum(values) / len(values)
        case "min":
            return min(values)
        case "max":
            return max(values)
        case "sum":
            return sum(values)
        case _:
            return None
