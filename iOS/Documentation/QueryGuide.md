# WireKit Query Guide

Cookbook-style examples for every query category. All examples assume the daemon is running and `Wire.configure()` has been called.

## Query Structure

Every exchange-level query has three parts:

```swift
let answer = try Wire.query(
    scope: .span("my_span"),           // 1. Which span to search
    target: .init(                      // 2. Which exchange to select
        domain: "api.example.com",
        endpoint: "/users",
        method: .GET
    ),
    question: .responseStatus           // 3. What to ask about it
)
```

All `target` fields are optional — omit any you don't need to filter on.

---

## Response Status & Headers

### Check the HTTP status code

```swift
let status = try Wire.query(
    scope: .span("checkout"),
    target: .init(domain: "api.example.com", endpoint: "/orders", method: .POST),
    question: .responseStatus
)
XCTAssertEqual(status.intValue, 201)
```

### Read a response header

```swift
let contentType = try Wire.query(
    scope: .span("api_call"),
    target: .init(domain: "api.example.com", endpoint: "/users"),
    question: .responseHeaderValue(name: "content-type")
)
XCTAssertTrue(contentType.stringValue?.contains("application/json") ?? false)
```

### Check if a response header exists

```swift
let hasCacheControl = try Wire.query(
    scope: .span("api_call"),
    target: .init(domain: "cdn.example.com"),
    question: .responseHeaderExists(name: "cache-control")
)
XCTAssertEqual(hasCacheControl.boolValue, true)
```

### Read a request header

```swift
let auth = try Wire.query(
    scope: .span("authenticated"),
    target: .init(domain: "api.example.com", endpoint: "/me"),
    question: .requestHeaderValue(name: "authorization")
)
XCTAssertTrue(auth.stringValue?.hasPrefix("Bearer ") ?? false)
```

---

## JSON Body Extraction

### Extract a value by key path

```swift
// Response: {"user": {"name": "Alice", "role": "admin"}}
let name = try Wire.query(
    scope: .span("profile"),
    target: .init(domain: "api.example.com", endpoint: "/me"),
    question: .responseBodyKeyPath(path: "user.name")
)
XCTAssertEqual(name.stringValue, "Alice")
```

### Nested key paths with arrays

```swift
// Response: {"data": {"teams": [{"name": "Engineering", "members": [...]}]}}
let teamName = try Wire.query(
    scope: .span("teams"),
    target: .init(domain: "api.example.com", endpoint: "/teams"),
    question: .responseBodyKeyPath(path: "data.teams[0].name")
)
XCTAssertEqual(teamName.stringValue, "Engineering")
```

### Count items in an array

```swift
// Response: {"items": [{"id": 1}, {"id": 2}, {"id": 3}]}
let count = try Wire.query(
    scope: .span("list"),
    target: .init(domain: "api.example.com", endpoint: "/items"),
    question: .countAtKeyPath(path: "items")
)
XCTAssertEqual(count.intValue, 3)
```

### Check if the response body contains a substring

```swift
let contains = try Wire.query(
    scope: .span("search"),
    target: .init(domain: "api.example.com", endpoint: "/search"),
    question: .responseBodyContains(substring: "no results")
)
XCTAssertEqual(contains.boolValue, false)
```

### Get the full response body

```swift
let body = try Wire.query(
    scope: .span("details"),
    target: .init(domain: "api.example.com", endpoint: "/config"),
    question: .responseBodyRaw
)
// body.objectValue is the parsed JSON dictionary
// body.stringValue is available for non-JSON bodies
```

### Check response content type

```swift
let contentType = try Wire.query(
    scope: .span("api_call"),
    target: .init(domain: "api.example.com", endpoint: "/data"),
    question: .responseContentType
)
XCTAssertEqual(contentType.stringValue, "json")
```

---

## Request Body Inspection

### Extract a value from the request body

```swift
// Request POST body: {"username": "alice", "role": "admin"}
let username = try Wire.query(
    scope: .span("create_user"),
    target: .init(domain: "api.example.com", endpoint: "/users", method: .POST),
    question: .requestBodyKeyPath(path: "username")
)
XCTAssertEqual(username.stringValue, "alice")
```

### Get the full request body

```swift
let body = try Wire.query(
    scope: .span("update"),
    target: .init(domain: "api.example.com", endpoint: "/settings", method: .PUT),
    question: .requestBodyRaw
)
```

---

## Query Parameter Extraction

### Get a query parameter value

```swift
// URL: /search?q=swift&page=2
let page = try Wire.query(
    scope: .span("search"),
    target: .init(domain: "api.example.com", endpoint: "/search"),
    question: .queryParamValue(name: "page")
)
XCTAssertEqual(page.stringValue, "2")
```

Note: Query parameter values are always strings.

### Check if a query parameter exists

```swift
let hasSort = try Wire.query(
    scope: .span("list"),
    target: .init(domain: "api.example.com", endpoint: "/items"),
    question: .queryParamExists(name: "sort")
)
XCTAssertEqual(hasSort.boolValue, true)
```

---

## Request Counting & Occurrence Selection

### Check if a request was made

```swift
let exists = try Wire.query(
    scope: .span("flow"),
    target: .init(domain: "analytics.example.com", endpoint: "/track", method: .POST),
    question: .requestExists
)
XCTAssertEqual(exists.boolValue, true)
```

### Count how many times a request was made

```swift
let count = try Wire.query(
    scope: .span("polling"),
    target: .init(domain: "api.example.com", endpoint: "/status", method: .GET),
    question: .requestCount
)
XCTAssertEqual(count.intValue, 3)
```

### Select a specific occurrence

When multiple requests match the same target, use `occurrence` to pick one:

```swift
// First request (index 0, the default)
let first = try Wire.query(
    scope: .span("pagination"),
    target: .init(domain: "api.example.com", endpoint: "/items", occurrence: 0),
    question: .queryParamValue(name: "page")
)
XCTAssertEqual(first.stringValue, "1")

// Second request (index 1)
let second = try Wire.query(
    scope: .span("pagination"),
    target: .init(domain: "api.example.com", endpoint: "/items", occurrence: 1),
    question: .queryParamValue(name: "page")
)
XCTAssertEqual(second.stringValue, "2")

// Most recent request (index -1)
let latest = try Wire.query(
    scope: .span("pagination"),
    target: .init(domain: "api.example.com", endpoint: "/items", occurrence: -1),
    question: .queryParamValue(name: "page")
)
XCTAssertEqual(latest.stringValue, "3")
```

---

## Multi-Question Queries

Send multiple questions in a single request for efficiency. Answers are returned in the same order.

```swift
let response = try Wire.query(
    scope: .span("api_call"),
    target: .init(domain: "api.example.com", endpoint: "/users", method: .GET),
    questions: [
        .responseStatus,
        .responseHeaderExists(name: "content-type"),
        .responseContentType,
        .responseBodyKeyPath(path: "users[0].name"),
        .countAtKeyPath(path: "users"),
    ]
)

XCTAssertTrue(response.found)
XCTAssertEqual(response.answers.count, 5)

// Access each answer by index (matches question order)
XCTAssertEqual(response.answers[0].intValue, 200)
XCTAssertEqual(response.answers[1].boolValue, true)
XCTAssertEqual(response.answers[2].stringValue, "json")
XCTAssertEqual(response.answers[3].stringValue, "Alice")
XCTAssertEqual(response.answers[4].intValue, 10)
```

---

## Metrics

### Response time

```swift
let time = try Wire.query(
    scope: .span("perf"),
    target: .init(domain: "api.example.com", endpoint: "/heavy"),
    question: .responseTimeMs()
)
XCTAssertTrue((time.doubleValue ?? 0) < 2000, "Should respond under 2 seconds")
```

### Aggregate metrics across multiple requests

```swift
// Average response time for all GET /items requests
let avg = try Wire.query(
    scope: .span("load_test"),
    target: .init(domain: "api.example.com", endpoint: "/items", method: .GET),
    question: .responseTimeMs(aggregate: .avg)
)
XCTAssertTrue((avg.doubleValue ?? 0) < 500)

// Max response body size
let maxSize = try Wire.query(
    scope: .span("load_test"),
    target: .init(domain: "api.example.com", endpoint: "/items"),
    question: .responseBodySizeBytes(aggregate: .max)
)
```

Supported aggregates: `.avg`, `.min`, `.max`, `.sum`

---

## Span-Level Queries

Span queries ask about an entire span of traffic, not a specific exchange.

### Total request count

```swift
let count = try Wire.spanQuery(
    scope: .span("full_flow"),
    question: .totalRequestCount
)
XCTAssertEqual(count.intValue, 15)
```

### Which domains were contacted

```swift
let domains = try Wire.spanQuery(
    scope: .span("full_flow"),
    question: .domainsContacted
)
let list = domains.arrayValue?.compactMap(\.stringValue) ?? []
XCTAssertTrue(list.contains("api.example.com"))
XCTAssertFalse(list.contains("evil.example.com"))
```

### Which endpoints were called

```swift
let endpoints = try Wire.spanQuery(
    scope: .span("full_flow"),
    question: .endpointsContacted
)
```

### Which HTTP methods were used

```swift
let methods = try Wire.spanQuery(
    scope: .span("full_flow"),
    question: .methodsUsed
)
let list = methods.arrayValue?.compactMap(\.stringValue) ?? []
XCTAssertTrue(list.contains("GET"))
XCTAssertTrue(list.contains("POST"))
```

### Unique exchange breakdown

```swift
let unique = try Wire.spanQuery(
    scope: .span("full_flow"),
    question: .uniqueExchanges
)
// Returns an array of {domain, endpoint, method, count} objects
```

### Timing

```swift
let duration = try Wire.spanQuery(
    scope: .span("full_flow"),
    question: .totalDurationMs
)
XCTAssertTrue((duration.doubleValue ?? 0) < 10_000, "Flow should complete under 10 seconds")
```

### Error tracking

```swift
let errors = try Wire.spanQuery(
    scope: .span("full_flow"),
    question: .errorCount
)
XCTAssertEqual(errors.intValue, 0, "No errors expected")

let rate = try Wire.spanQuery(
    scope: .span("full_flow"),
    question: .errorRate
)
XCTAssertTrue((rate.doubleValue ?? 100) < 5.0, "Error rate should be under 5%")
```

### Status code summary

```swift
let summary = try Wire.spanQuery(
    scope: .span("full_flow"),
    question: .statusCodeSummary
)
// Returns {"200": 10, "201": 2, "404": 1}
let codes = summary.objectValue ?? [:]
XCTAssertNil(codes["500"], "No server errors expected")
```

### Span queries with a filter

Narrow which exchanges within the span are considered:

```swift
// Count only requests to a specific domain
let count = try Wire.spanQuery(
    scope: .span("full_flow"),
    filter: SpanFilter(domain: "api.example.com"),
    question: .totalRequestCount
)

// Error rate for POST requests only
let rate = try Wire.spanQuery(
    scope: .span("full_flow"),
    filter: SpanFilter(method: .POST),
    question: .errorRate
)
```

---

## Error Handling & Not-Found Cases

### Exchange not found

When no exchange matches the scope + target, `found` is `false`:

```swift
let answer = try Wire.query(
    scope: .span("login"),
    target: .init(domain: "nonexistent.example.com"),
    question: .responseStatus
)

if !answer.found {
    // answer.reason == "no_matching_exchange"
    XCTFail("Expected request to nonexistent.example.com was not captured")
}
```

### Span not found

```swift
let answer = try Wire.spanQuery(
    scope: .span("span_that_never_existed"),
    question: .totalRequestCount
)
XCTAssertFalse(answer.found)
XCTAssertEqual(answer.reason, "span_not_found")
```

### Per-answer error reasons

Even when an exchange is found, individual questions can fail:

| Reason | Meaning |
|--------|---------|
| `key_not_found` | Key path doesn't exist in the JSON body |
| `index_out_of_bounds` | Array index exceeds length |
| `body_not_json` | Body couldn't be parsed as JSON |
| `body_empty` | No body present |
| `header_not_found` | Header name doesn't exist |
| `not_applicable` | Question doesn't apply to this exchange |

### Top-level error reasons

| Reason | Meaning |
|--------|---------|
| `no_matching_exchange` | Nothing matched scope + target |
| `occurrence_out_of_range` | Exchanges matched but the occurrence index was too high |
| `span_not_found` | The named span doesn't exist |

### Daemon not running

If the daemon is unreachable, methods throw `WireError.connectionFailed`:

```swift
do {
    let answer = try Wire.query(
        scope: .all,
        question: .requestCount
    )
} catch WireError.connectionFailed {
    XCTFail("Wire daemon is not running")
} catch WireError.timeout {
    XCTFail("Request timed out")
}
```

---

## Scopes: Choosing What to Search

| Scope | Use When |
|-------|----------|
| `.span("name")` | Querying traffic from a specific test scenario |
| `.unspanned` | Querying traffic captured outside any span |
| `.all` | Querying all captured traffic regardless of span |

`.span("name")` is the most common — it gives you isolated traffic for the test scenario you're interested in.
