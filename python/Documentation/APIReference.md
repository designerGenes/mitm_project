# Watcher HTTP API Reference

Human-readable reference for the Watcher daemon's HTTP API. For the machine-readable OpenAPI spec, see [`openapi.yaml`](openapi.yaml).

## Server

Default: `http://localhost:9090`

Configurable via `watcher start --port <port>`.

---

## Endpoints

### GET /health

Health check. Returns OK if the daemon is alive.

```bash
curl http://localhost:9090/health
```

```json
{"status": "ok"}
```

### GET /status

Current daemon state.

```bash
curl http://localhost:9090/status
```

```json
{
  "config": {
    "api_port": 9090,
    "proxy_port": 8080,
    "output_dir": "~/Library/Application Support/Watcher/traffic",
    "verbose": false,
    "unsafe": false
  },
  "current_span": "login",
  "exchange_count": 42,
  "spans": {
    "login": {"started_at": "2025-01-15T10:30:00Z", "stopped_at": null},
    "setup": {"started_at": "2025-01-15T10:29:00Z", "stopped_at": "2025-01-15T10:29:55Z"}
  }
}
```

### POST /reset

Clear all captured exchanges, spans, and disk data.

```bash
curl -X POST http://localhost:9090/reset
```

```json
{"status": "reset"}
```

### POST /admin/shutdown

Initiate graceful shutdown. Used by the CLI (`watcher stop`).

```bash
curl -X POST http://localhost:9090/admin/shutdown
```

```json
{"status": "shutting_down"}
```

### POST /span/start

Start a named span. All subsequent captured traffic is tagged with this name.

If another span is already active, it is auto-closed first.

```bash
curl -X POST http://localhost:9090/span/start \
  -H "Content-Type: application/json" \
  -d '{"name": "login"}'
```

```json
{"status": "started", "name": "login"}
```

With auto-close:

```json
{"status": "started", "name": "checkout", "auto_closed": "login"}
```

### POST /span/stop

Stop the current span. Subsequent traffic becomes unspanned.

```bash
curl -X POST http://localhost:9090/span/stop
```

```json
{"status": "stopped", "name": "login"}
```

If no span is active:

```json
{"status": "no_active_span"}
```

### POST /query

Exchange-level query. Ask questions about a specific captured HTTP exchange.

```bash
curl -X POST http://localhost:9090/query \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "login",
    "target": {
      "domain": "api.example.com",
      "endpoint": "/auth",
      "method": "POST"
    },
    "questions": [
      {"type": "response_status"},
      {"type": "response_body_key_path", "path": "user.name"}
    ]
  }'
```

```json
{
  "found": true,
  "matched_count": 1,
  "occurrence_used": 0,
  "answers": [
    {"found": true, "value": 200},
    {"found": true, "value": "Alice"}
  ]
}
```

### POST /span/query

Span-level query. Ask meta questions about an entire span of traffic.

```bash
curl -X POST http://localhost:9090/span/query \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "login",
    "questions": [
      {"type": "total_request_count"},
      {"type": "domains_contacted"},
      {"type": "error_count"}
    ]
  }'
```

```json
{
  "found": true,
  "answers": [
    {"found": true, "value": 5},
    {"found": true, "value": ["api.example.com", "cdn.example.com"]},
    {"found": true, "value": 0}
  ]
}
```

---

## Query Pipeline

Exchange-level queries (`POST /query`) follow a 5-stage pipeline:

### 1. Scope Resolution

Filter exchanges by span name.

| Scope Value | Behavior |
|-------------|----------|
| `"login"` (any string) | Only exchanges tagged to that span |
| `"unspanned"` | Only exchanges with no span |
| `"all"` | All exchanges regardless of span |

### 2. Target Resolution

Further filter by `domain`, `endpoint`, `method`. All fields are optional — omitted fields are not filtered on.

| Field | Matching |
|-------|----------|
| `domain` | Exact match, case-insensitive (domains are lowercased on capture) |
| `endpoint` | Exact match. Trailing slashes stripped. No query params (stored separately). |
| `method` | Exact match, case-insensitive (methods are uppercased on capture) |

**Endpoint matching is exact.** `/users`, `/users/123`, and `/users/456` are three distinct endpoints. No prefix matching, no wildcards.

### 3. Occurrence Selection

When multiple exchanges match, `occurrence` selects which one:

| Value | Selects |
|-------|---------|
| `0` (default) | First recorded |
| `1` | Second recorded |
| `-1` | Most recent |
| `-2` | Second most recent |

Some question types skip this step:
- `request_exists` and `request_count` operate on the full filtered list
- Metric questions with `aggregate` operate across all matches

### 4. Question Evaluation

Each question is evaluated against the selected exchange (or the full list for skip-occurrence questions).

### 5. Response Formatting

Results are wrapped in the standard envelope with two-level `found`:
- Top-level `found: false` — no exchange matched scope + target
- Per-answer `found: false` — the exchange was found but the question couldn't be answered

---

## Exchange-Level Question Types (23)

### Existence & Counting

These skip occurrence selection and operate on the full filtered list.

| Type | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `request_exists` | — | `bool` | Whether any exchange matches the target |
| `request_count` | — | `int` | Number of matching exchanges |

### Status

| Type | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `response_status` | — | `int` | HTTP response status code |

### Headers

| Type | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `response_header_value` | `name` | `string` or `list` | Response header value |
| `request_header_value` | `name` | `string` or `list` | Request header value |
| `response_header_exists` | `name` | `bool` | Whether the response header exists |
| `request_header_exists` | `name` | `bool` | Whether the request header exists |

Header matching is case-insensitive (all keys normalized to lowercase on capture).

### Response Body

| Type | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `response_body_key_path` | `path` | any | Extract value from JSON response body |
| `count_at_key_path` | `path` | `int` | Length of the array at the key path |
| `response_body_contains` | `substring` | `bool` | Substring search on raw body |
| `response_body_raw` | — | any | Full response body (parsed JSON or raw string) |
| `response_content_type` | — | `string` | Classification: `json`, `text`, `binary`, or `empty` |

**Key path syntax:**
- Dot notation: `user.name`, `data.items`
- Array indices: `users[0].name`, `[0].id`
- Nested: `data.teams[0].members[1].role`

### Request Body

| Type | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `request_body_key_path` | `path` | any | Extract value from JSON request body |
| `request_body_raw` | — | any | Full request body |
| `request_content_type` | — | `string` | Classification: `json`, `text`, `binary`, or `empty` |

### Query Parameters

| Type | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `query_param_value` | `name` | `string` | Value of a URL query parameter |
| `query_param_exists` | `name` | `bool` | Whether a query parameter exists |

### Metrics

| Type | Parameters | Returns | Description |
|------|-----------|---------|-------------|
| `response_time_ms` | `aggregate`? | `number` | Response time in milliseconds |
| `response_body_size_bytes` | `aggregate`? | `int` | Response body size in bytes |
| `request_body_size_bytes` | `aggregate`? | `int` | Request body size in bytes |

**Aggregate modifier** (optional): `avg`, `min`, `max`, `sum`. When present, occurrence is ignored and the metric is computed across all matched exchanges.

```json
{"type": "response_time_ms", "aggregate": "avg"}
```

---

## Span-Level Question Types (13)

### Inventory

| Type | Returns | Description |
|------|---------|-------------|
| `total_request_count` | `int` | Total exchanges in the span |
| `domains_contacted` | `list[string]` | Sorted unique domains |
| `endpoints_contacted` | `list[string]` | Sorted unique endpoints |
| `methods_used` | `list[string]` | Sorted unique HTTP methods |
| `unique_exchanges` | `list[object]` | `{domain, endpoint, method, count}` combos |

### Timing

| Type | Returns | Description |
|------|---------|-------------|
| `total_duration_ms` | `number` | First request start to last response end |
| `span_start_time` | `string` (ISO 8601) | Timestamp of first exchange |
| `span_end_time` | `string` (ISO 8601) | Timestamp of last exchange |

### Aggregates

| Type | Returns | Description |
|------|---------|-------------|
| `avg_response_time_ms` | `number` | Average response time |
| `slowest_request` | `object` | `{domain, endpoint, method, occurrence}` of the slowest exchange |
| `error_count` | `int` | Exchanges with status >= 400 |
| `error_rate` | `number` | Percentage of error responses (0-100) |
| `status_code_summary` | `object` | `{"200": 10, "404": 2}` map of status codes to counts |

---

## Error Reasons

### Per-Answer Reasons

When `answer.found` is `false`:

| Reason | Meaning |
|--------|---------|
| `key_not_found` | Key path doesn't exist in the JSON body |
| `index_out_of_bounds` | Array index exceeds array length |
| `body_not_json` | Body couldn't be parsed as JSON |
| `body_empty` | No body present |
| `header_not_found` | Header name doesn't exist in the exchange |
| `not_applicable` | Question type doesn't apply to this exchange |

### Top-Level Reasons (Exchange Query)

When `response.found` is `false`:

| Reason | Meaning |
|--------|---------|
| `no_matching_exchange` | Nothing matched scope + target filters |
| `occurrence_out_of_range` | Exchanges matched but the occurrence index was out of bounds |

### Top-Level Reasons (Span Query)

| Reason | Meaning |
|--------|---------|
| `span_not_found` | The named span doesn't exist and has no tagged exchanges |

---

## Configuration (CLI)

The daemon is started via the CLI:

```bash
watcher start [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `9090` | HTTP API server port |
| `--proxy-port` | `8080` | mitmproxy listening port |
| `--output` | `~/Library/Application Support/Watcher/traffic/` | Output directory for disk data |
| `--verbose` | `false` | Log captured traffic to stdout |
| `--unsafe` | `false` | Skip upstream TLS verification (for corporate proxies) |
| `--foreground` | `false` | Run in foreground instead of as a launchd service |

Other CLI commands:

```bash
watcher stop [--port PORT]     # Stop the daemon
watcher reset [--port PORT]    # Clear all captured data
watcher status [--port PORT]   # Show daemon status
watcher status --json-output   # Output raw JSON
```
