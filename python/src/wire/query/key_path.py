"""Dot/bracket key path parser and resolver.

Supports:
  - Dot notation: user.name
  - Bracket notation: users[0].name
  - Root-level arrays: [0].name or [2]
  - Nested arrays: data.teams[0].members[1].role
"""

from __future__ import annotations

import re
from typing import Any

from wire.models import AnswerErrorReason

# Matches either a dotted key or a bracket index: "key", "[0]", "key[0]"
_SEGMENT_RE = re.compile(r'([^.\[\]]+)|\[(\d+)\]')


def parse_key_path(path: str) -> list[str | int]:
    """Parse a key path string into a list of keys (str) and indices (int)."""
    segments: list[str | int] = []
    for match in _SEGMENT_RE.finditer(path):
        key, index = match.groups()
        if key is not None:
            segments.append(key)
        elif index is not None:
            segments.append(int(index))
    return segments


def resolve_key_path(data: Any, path: str) -> tuple[bool, Any, str | None]:
    """Resolve a key path against a data structure.

    Returns (found, value, error_reason).
    """
    segments = parse_key_path(path)
    if not segments:
        return True, data, None

    current = data
    for segment in segments:
        if isinstance(segment, int):
            if not isinstance(current, list):
                return False, None, AnswerErrorReason.KEY_NOT_FOUND
            if segment < 0 or segment >= len(current):
                return False, None, AnswerErrorReason.INDEX_OUT_OF_BOUNDS
            current = current[segment]
        else:
            if not isinstance(current, dict):
                return False, None, AnswerErrorReason.KEY_NOT_FOUND
            if segment not in current:
                return False, None, AnswerErrorReason.KEY_NOT_FOUND
            current = current[segment]

    return True, current, None
