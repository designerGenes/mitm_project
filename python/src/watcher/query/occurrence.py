"""Stage 3: Occurrence selection — pick a specific exchange by index."""

from __future__ import annotations

from watcher.models import Exchange


def select_occurrence(exchanges: list[Exchange], occurrence: int) -> Exchange | None:
    """Select an exchange by occurrence index.

    0 = first recorded, 1 = second, -1 = most recent.
    Returns None if index is out of range.
    """
    if not exchanges:
        return None
    try:
        return exchanges[occurrence]
    except IndexError:
        return None
