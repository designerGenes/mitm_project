from __future__ import annotations

from datetime import datetime, timezone


class SpanManager:
    """Manages the lifecycle of traffic capture spans.

    Only one span can be active at a time.
    Starting a new span auto-closes the current one.
    """

    def __init__(self) -> None:
        self._current_span: str | None = None
        self._spans: dict[str, dict] = {}  # name -> {started_at, stopped_at}

    @property
    def current_span(self) -> str | None:
        return self._current_span

    @property
    def spans(self) -> dict[str, dict]:
        return dict(self._spans)

    def start(self, name: str) -> str | None:
        """Start a new span. Returns the name of any auto-closed span, or None."""
        auto_closed = None
        if self._current_span is not None:
            auto_closed = self._current_span
            self._close_current()
        self._current_span = name
        self._spans[name] = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "stopped_at": None,
        }
        return auto_closed

    def stop(self) -> str | None:
        """Stop the current span. Returns the stopped span name, or None if no span was active."""
        if self._current_span is None:
            return None
        stopped = self._current_span
        self._close_current()
        return stopped

    def _close_current(self) -> None:
        if self._current_span and self._current_span in self._spans:
            self._spans[self._current_span]["stopped_at"] = datetime.now(timezone.utc).isoformat()
        self._current_span = None

    def has_span(self, name: str) -> bool:
        return name in self._spans

    def reset(self) -> None:
        self._current_span = None
        self._spans.clear()
