from __future__ import annotations

from urllib.parse import urlparse, parse_qs

from watcher.models import ContentType


def classify_content_type(raw_ct: str, body: bytes) -> ContentType:
    """Classify a Content-Type header into one of: json, text, binary, empty."""
    if not body:
        return ContentType.EMPTY
    if not raw_ct:
        return ContentType.BINARY
    lower = raw_ct.lower().split(";")[0].strip()
    if lower == "application/json" or lower.endswith("+json"):
        return ContentType.JSON
    if lower.startswith("text/"):
        return ContentType.TEXT
    return ContentType.BINARY


def normalize_headers(headers: dict[str, str | list[str]]) -> dict[str, str | list[str]]:
    """Lowercase all header keys."""
    return {k.lower(): v for k, v in headers.items()}


def normalize_method(method: str) -> str:
    return method.upper()


def normalize_domain(domain: str) -> str:
    return domain.lower()


def parse_url(url: str) -> tuple[str, str, dict[str, str]]:
    """Parse a URL into (domain, endpoint, query_params).

    - Domain is lowercased
    - Endpoint has trailing slash stripped and query params removed
    - Query params are extracted separately
    """
    parsed = urlparse(url)
    domain = normalize_domain(parsed.hostname or "")
    endpoint = parsed.path.rstrip("/") or "/"
    raw_params = parse_qs(parsed.query, keep_blank_values=True)
    # Flatten single-value lists
    query_params = {k: v[0] if len(v) == 1 else v for k, v in raw_params.items()}
    return domain, endpoint, query_params


def try_parse_json(body: bytes) -> object | None:
    """Attempt to parse bytes as JSON. Returns None on failure."""
    import json
    try:
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
