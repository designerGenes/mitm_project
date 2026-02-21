# WireKit API Reference

Complete reference for all public types in the WireKit Swift library.

## Wire (Static Facade)

The primary API for iOS UI tests. All methods are `static` and delegate to an internal `WireKit` instance.

```swift
public enum Wire
```

### Configuration

```swift
static func configure(
    port: Int = 9090,
    host: String = "localhost",
    session: URLSession = .shared,
    timeout: TimeInterval = 10
)
```

Reconfigures the underlying client. Call in your test `setUp` if not using the default port.

```swift
static var client: WireKit { get }
```

The underlying client instance, if you need direct access.

### Span Control

```swift
static func startSpan(named name: String) throws
```

Start a named span. All subsequent captured traffic is tagged with this name. If another span is already active, it is auto-closed first.

```swift
static func stopSpan() throws
```

Stop the current span. Subsequent traffic becomes unspanned.

### Exchange-Level Queries

```swift
static func query(
    scope: Scope,
    target: QueryTarget = .init(),
    questions: [Question]
) throws -> QueryResponse
```

Send multiple questions about a single exchange. Returns the full response including `matchedCount` and `occurrenceUsed`.

```swift
static func query(
    scope: Scope,
    target: QueryTarget = .init(),
    question: Question
) throws -> Answer
```

Convenience: send a single question, get back just the `Answer`.

### Span-Level Queries

```swift
static func spanQuery(
    scope: Scope,
    filter: SpanFilter? = nil,
    questions: [SpanQuestion]
) throws -> SpanQueryResponse
```

Ask meta questions about an entire span of traffic.

```swift
static func spanQuery(
    scope: Scope,
    filter: SpanFilter? = nil,
    question: SpanQuestion
) throws -> Answer
```

Convenience: single span question, returns just the `Answer`.

### Admin

```swift
static func reset() throws
```

Clear all captured data and spans.

```swift
static func status() throws -> StatusResponse
```

Get the daemon's current state.

```swift
static func health() throws -> Bool
```

Returns `true` if the daemon is alive and responding.

---

## WireKit (Instance-Based)

For advanced usage when you need multiple client instances or custom configuration per-instance.

```swift
public final class WireKit: @unchecked Sendable
```

### Initializer

```swift
init(
    port: Int = 9090,
    host: String = "localhost",
    session: URLSession = .shared,
    timeout: TimeInterval = 10
)
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `baseURL` | `URL` | The base URL constructed from host and port |
| `session` | `URLSession` | The URL session used for requests |
| `timeout` | `TimeInterval` | Request timeout in seconds |

### Methods

All methods mirror the static `Wire` facade — see above for signatures and descriptions:

- `startSpan(named:)`, `stopSpan()`
- `query(scope:target:questions:)`, `query(scope:target:question:)`
- `spanQuery(scope:filter:questions:)`, `spanQuery(scope:filter:question:)`
- `reset()`, `status()`, `health()`

All methods are **synchronous** (blocking), designed for use in XCTest where you interact with the UI, then assert.

---

## Scope

Selects which exchanges to query.

```swift
public enum Scope: Encodable, Equatable
```

| Case | Description |
|------|-------------|
| `.span(String)` | Only exchanges tagged to the named span |
| `.unspanned` | Only exchanges with no span |
| `.all` | All exchanges regardless of span |

---

## QueryTarget

Filters exchanges by domain, endpoint, method, and selects by occurrence.

```swift
public struct QueryTarget: Encodable, Equatable
```

### Initializer

```swift
init(
    domain: String? = nil,
    endpoint: String? = nil,
    method: HTTPMethod? = nil,
    occurrence: Int? = nil
)
```

### Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `domain` | `String?` | `nil` | Exact match on normalized hostname |
| `endpoint` | `String?` | `nil` | Exact match on normalized path (trailing slash stripped, no query params) |
| `method` | `HTTPMethod?` | `nil` | Filter by HTTP method |
| `occurrence` | `Int?` | `nil` | Index into matched results. `0` = first, `1` = second, `-1` = most recent. Default server behavior is `0` when omitted. |

All fields are optional. Omitted fields are not filtered on.

---

## SpanFilter

Optional filter for span-level queries. Narrows which exchanges within the span are considered.

```swift
public struct SpanFilter: Encodable, Equatable
```

### Initializer

```swift
init(
    domain: String? = nil,
    endpoint: String? = nil,
    method: HTTPMethod? = nil
)
```

### Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `domain` | `String?` | `nil` | Filter exchanges by domain |
| `endpoint` | `String?` | `nil` | Filter exchanges by endpoint |
| `method` | `HTTPMethod?` | `nil` | Filter exchanges by HTTP method |

---

## Question (Exchange-Level)

A question to ask about a single captured HTTP exchange. 23 cases organized by category.

```swift
public enum Question: Encodable
```

### Existence & Counting

These skip occurrence selection and operate on the full filtered list.

| Case | Parameters | Return Type | Description |
|------|-----------|-------------|-------------|
| `.requestExists` | — | `Bool` | Whether any exchange matches the target |
| `.requestCount` | — | `Int` | Number of exchanges matching the target |

### Status

| Case | Parameters | Return Type | Description |
|------|-----------|-------------|-------------|
| `.responseStatus` | — | `Int` | HTTP response status code |

### Headers

| Case | Parameters | Return Type | Description |
|------|-----------|-------------|-------------|
| `.responseHeaderValue(name:)` | `name: String` | `String` or `[String]` | Response header value (array if multi-value) |
| `.requestHeaderValue(name:)` | `name: String` | `String` or `[String]` | Request header value |
| `.responseHeaderExists(name:)` | `name: String` | `Bool` | Whether the response header exists |
| `.requestHeaderExists(name:)` | `name: String` | `Bool` | Whether the request header exists |

Header matching is case-insensitive (all keys are normalized to lowercase on capture).

### Response Body

| Case | Parameters | Return Type | Description |
|------|-----------|-------------|-------------|
| `.responseBodyKeyPath(path:)` | `path: String` | Any JSON value | Extract a value from the JSON response body |
| `.countAtKeyPath(path:)` | `path: String` | `Int` | Length of the array at the given key path |
| `.responseBodyContains(substring:)` | `substring: String` | `Bool` | Whether the raw response body contains the substring |
| `.responseBodyRaw` | — | Any | Full response body (parsed JSON if JSON, raw string otherwise) |
| `.responseContentType` | — | `String` | Content type classification (`json`, `text`, `binary`, `empty`) |

**Key path syntax:** Dot notation for objects (`user.name`), bracket notation for arrays (`users[0].name`), nested (`data.teams[0].members[1].role`).

### Request Body

| Case | Parameters | Return Type | Description |
|------|-----------|-------------|-------------|
| `.requestBodyKeyPath(path:)` | `path: String` | Any JSON value | Extract a value from the JSON request body |
| `.requestBodyRaw` | — | Any | Full request body |
| `.requestContentType` | — | `String` | Content type classification |

### Query Parameters

| Case | Parameters | Return Type | Description |
|------|-----------|-------------|-------------|
| `.queryParamValue(name:)` | `name: String` | `String` | Value of a URL query parameter |
| `.queryParamExists(name:)` | `name: String` | `Bool` | Whether a query parameter exists |

### Metrics

| Case | Parameters | Return Type | Description |
|------|-----------|-------------|-------------|
| `.responseTimeMs(aggregate:)` | `aggregate: Aggregate? = nil` | `Double` | Response time in milliseconds |
| `.responseBodySizeBytes(aggregate:)` | `aggregate: Aggregate? = nil` | `Int` | Response body size in bytes |
| `.requestBodySizeBytes(aggregate:)` | `aggregate: Aggregate? = nil` | `Int` | Request body size in bytes |

When `aggregate` is provided (`avg`, `min`, `max`, `sum`), occurrence is skipped and the metric is computed across all matched exchanges.

---

## SpanQuestion (Span-Level)

A meta question about an entire span of captured traffic. 13 cases.

```swift
public enum SpanQuestion: Encodable
```

### Inventory

| Case | Return Type | Description |
|------|-------------|-------------|
| `.totalRequestCount` | `Int` | Total number of exchanges in the span |
| `.domainsContacted` | `[String]` | Sorted list of unique domains |
| `.endpointsContacted` | `[String]` | Sorted list of unique endpoints |
| `.methodsUsed` | `[String]` | Sorted list of unique HTTP methods |
| `.uniqueExchanges` | `[{domain, endpoint, method, count}]` | Unique domain/endpoint/method combos with counts |

### Timing

| Case | Return Type | Description |
|------|-------------|-------------|
| `.totalDurationMs` | `Double` | First request start to last response end |
| `.spanStartTime` | `String` (ISO 8601) | Timestamp of the first exchange |
| `.spanEndTime` | `String` (ISO 8601) | Timestamp of the last exchange |

### Aggregates

| Case | Return Type | Description |
|------|-------------|-------------|
| `.avgResponseTimeMs` | `Double` | Average response time across all exchanges |
| `.slowestRequest` | `{domain, endpoint, method, occurrence}` | Identifies the slowest exchange |
| `.errorCount` | `Int` | Number of exchanges with status >= 400 |
| `.errorRate` | `Double` | Percentage of error responses (0-100) |
| `.statusCodeSummary` | `{String: Int}` | Map of status codes to counts |

---

## Aggregate

Aggregate modifier for metric questions.

```swift
public enum Aggregate: String, Encodable
```

| Case | Description |
|------|-------------|
| `.avg` | Average across all matched exchanges |
| `.min` | Minimum value |
| `.max` | Maximum value |
| `.sum` | Sum of all values |

---

## HTTPMethod

HTTP methods for target filtering.

```swift
public enum HTTPMethod: String, Codable, CaseIterable
```

Cases: `.GET`, `.POST`, `.PUT`, `.DELETE`, `.PATCH`, `.HEAD`, `.OPTIONS`

---

## QueryValue

A dynamically-typed JSON value returned by the Wire daemon.

```swift
public enum QueryValue: Decodable, Equatable, CustomStringConvertible
```

### Cases

| Case | Associated Value |
|------|-----------------|
| `.null` | — |
| `.bool(Bool)` | Boolean value |
| `.int(Int)` | Integer value |
| `.double(Double)` | Floating-point value |
| `.string(String)` | String value |
| `.array([QueryValue])` | Array of values |
| `.object([String: QueryValue])` | Dictionary of values |

### Convenience Accessors

| Accessor | Type | Notes |
|----------|------|-------|
| `.intValue` | `Int?` | Also converts exact `Double` values |
| `.doubleValue` | `Double?` | Also converts `Int` values |
| `.stringValue` | `String?` | |
| `.boolValue` | `Bool?` | |
| `.arrayValue` | `[QueryValue]?` | |
| `.objectValue` | `[String: QueryValue]?` | |
| `.isNull` | `Bool` | `true` if the value is `.null` |

---

## Answer

A single answer from the Wire daemon.

```swift
public struct Answer: Decodable
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `found` | `Bool` | Whether the question could be answered |
| `value` | `QueryValue?` | The answer value (nil if not found) |
| `reason` | `String?` | Error reason when `found` is false |

### Convenience Accessors

Shorthand for `value?.intValue`, etc.:

| Accessor | Type |
|----------|------|
| `.intValue` | `Int?` |
| `.doubleValue` | `Double?` |
| `.stringValue` | `String?` |
| `.boolValue` | `Bool?` |
| `.arrayValue` | `[QueryValue]?` |
| `.objectValue` | `[String: QueryValue]?` |

---

## QueryResponse

Response from `POST /query` (exchange-level queries).

```swift
public struct QueryResponse: Decodable
```

| Property | Type | Description |
|----------|------|-------------|
| `found` | `Bool` | Whether the scope + target resolved to at least one exchange |
| `matchedCount` | `Int?` | Number of exchanges matching the target filter |
| `occurrenceUsed` | `Int?` | Which occurrence index was selected |
| `reason` | `String?` | Error reason when top-level `found` is false |
| `answers` | `[Answer]` | One answer per question, in order |

**Two-level found:**
- Top-level `found: false` — no exchange matched (e.g., wrong domain/endpoint)
- Per-answer `found: false` — the exchange was found but the question couldn't be answered (e.g., missing header)

---

## SpanQueryResponse

Response from `POST /span/query` (span-level queries).

```swift
public struct SpanQueryResponse: Decodable
```

| Property | Type | Description |
|----------|------|-------------|
| `found` | `Bool` | Whether the span exists |
| `reason` | `String?` | Error reason (e.g., `"span_not_found"`) |
| `answers` | `[Answer]` | One answer per question, in order |

---

## StatusResponse

Response from `GET /status`.

```swift
public struct StatusResponse: Decodable
```

| Property | Type | Description |
|----------|------|-------------|
| `config` | `StatusConfig?` | Daemon configuration |
| `currentSpan` | `String?` | Name of the active span, or nil |
| `exchangeCount` | `Int` | Total captured exchanges |
| `spans` | `[String: SpanInfo]` | Map of span name to span info |

---

## StatusConfig

```swift
public struct StatusConfig: Decodable
```

| Property | Type |
|----------|------|
| `apiPort` | `Int?` |
| `proxyPort` | `Int?` |
| `outputDir` | `String?` |
| `verbose` | `Bool?` |

---

## SpanInfo

```swift
public struct SpanInfo: Decodable
```

| Property | Type | Description |
|----------|------|-------------|
| `startedAt` | `String?` | ISO 8601 start timestamp |
| `stoppedAt` | `String?` | ISO 8601 stop timestamp (nil if still active) |

---

## WireError

Errors thrown by the Wire client.

```swift
public enum WireError: Error, LocalizedError
```

| Case | Description |
|------|-------------|
| `.connectionFailed(underlying: Error)` | Could not connect to the Wire daemon |
| `.unexpectedStatus(Int, body: String?)` | Server returned a non-2xx HTTP status |
| `.decodingFailed(underlying: Error)` | Failed to decode the server response |
| `.timeout` | The request timed out |
