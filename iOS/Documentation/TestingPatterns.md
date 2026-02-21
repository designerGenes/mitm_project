# Testing Patterns with WatcherClient

Best practices for using WatcherClient in XCUITests and integration tests.

## XCUITest Setup & Teardown

### Standard setUp pattern

```swift
import XCTest
import WatcherClient

final class MyFeatureTests: XCTestCase {

    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false

        app = XCUIApplication()
        app.launch()

        // Configure client (default port 9090)
        Watcher.configure(port: 9090)

        // Skip all tests if daemon is unreachable
        let healthy = (try? Watcher.health()) ?? false
        try XCTSkipUnless(healthy, "Watcher daemon not running on :9090")

        // Clear all data from previous tests
        try Watcher.reset()
    }

    override func tearDown() {
        app = nil
        super.tearDown()
    }
}
```

Key points:
- `XCTSkipUnless` gracefully skips tests when the daemon isn't running (CI without Watcher, local dev without starting the daemon)
- `Watcher.reset()` in setUp ensures a clean slate for each test
- `continueAfterFailure = false` stops the test on the first failure

### Why reset in setUp, not tearDown

Resetting in `setUp` is more robust because:
- If a test crashes, tearDown may not run
- Each test starts with a known clean state regardless of what happened before
- You can inspect captured data after a failed test (it hasn't been cleared yet)

---

## Proxy Session Configuration

For integration tests that generate HTTP traffic directly (without driving the UI), create a URLSession routed through mitmproxy:

```swift
/// URLSession configured to route through the mitmproxy.
private lazy var proxySession: URLSession = {
    let config = URLSessionConfiguration.ephemeral
    config.connectionProxyDictionary = [
        kCFNetworkProxiesHTTPEnable as String: true,
        kCFNetworkProxiesHTTPProxy as String: "127.0.0.1",
        kCFNetworkProxiesHTTPPort as String: 8080,
    ]
    config.timeoutIntervalForRequest = 10
    return URLSession(configuration: config)
}()
```

The iOS Simulator shares the host Mac's network stack, so `127.0.0.1` reaches the local mitmproxy. Use this session for all traffic you want Watcher to capture.

### Making requests through the proxy

```swift
@discardableResult
private func proxyGET(_ urlString: String) -> (Data?, HTTPURLResponse?) {
    let url = URL(string: urlString)!
    let expectation = expectation(description: "GET \(urlString)")
    var resultData: Data?
    var resultResponse: HTTPURLResponse?

    let task = proxySession.dataTask(with: url) { data, response, _ in
        resultData = data
        resultResponse = response as? HTTPURLResponse
        expectation.fulfill()
    }
    task.resume()
    wait(for: [expectation], timeout: 15)
    return (resultData, resultResponse)
}
```

### Wait for capture

After making requests through the proxy, add a brief delay before querying to let the daemon process the traffic:

```swift
private func waitForCapture() {
    Thread.sleep(forTimeInterval: 0.3)
}
```

For XCUITests, the natural delay of UI animations is usually sufficient. Only add explicit waits in integration tests that make requests directly.

---

## Span Lifecycle

### One span per test scenario

The most common pattern: start a span at the beginning of the user action, stop it after:

```swift
func testCheckoutFlow() throws {
    try Watcher.startSpan(named: "checkout")

    // Drive the UI
    app.buttons["Add to Cart"].tap()
    app.buttons["Checkout"].tap()
    app.buttons["Confirm"].tap()

    // Wait for the flow to complete
    let confirmation = app.staticTexts["Order Confirmed"]
    XCTAssertTrue(confirmation.waitForExistence(timeout: 10))

    try Watcher.stopSpan()

    // Now query the captured traffic
    let status = try Watcher.query(
        scope: .span("checkout"),
        target: .init(domain: "api.example.com", endpoint: "/orders", method: .POST),
        question: .responseStatus
    )
    XCTAssertEqual(status.intValue, 201)
}
```

### Multiple spans in one test

For tests that cover multiple distinct phases:

```swift
func testLoginThenBrowse() throws {
    // Phase 1: Login
    try Watcher.startSpan(named: "login")
    // ... login UI actions ...
    try Watcher.stopSpan()

    // Phase 2: Browse
    try Watcher.startSpan(named: "browse")
    // ... browsing UI actions ...
    try Watcher.stopSpan()

    // Assert on each phase independently
    let loginStatus = try Watcher.query(
        scope: .span("login"),
        target: .init(domain: "api.example.com", endpoint: "/auth", method: .POST),
        question: .responseStatus
    )
    XCTAssertEqual(loginStatus.intValue, 200)

    let browseCount = try Watcher.spanQuery(
        scope: .span("browse"),
        question: .totalRequestCount
    )
    XCTAssertTrue((browseCount.intValue ?? 0) > 0)
}
```

### Auto-close behavior

Starting a new span automatically closes the previous one. You don't need to call `stopSpan()` between spans:

```swift
try Watcher.startSpan(named: "step1")
// ... actions ...
try Watcher.startSpan(named: "step2")  // step1 is auto-closed
// ... actions ...
try Watcher.stopSpan()                 // stops step2
```

---

## Assertion Patterns

### Boolean assertions (found/not found)

```swift
let answer = try Watcher.query(
    scope: .span("test"),
    target: .init(domain: "api.example.com", endpoint: "/track"),
    question: .requestExists
)
XCTAssertTrue(answer.found)
XCTAssertEqual(answer.boolValue, true)
```

### Integer assertions (status codes, counts)

```swift
let status = try Watcher.query(
    scope: .span("test"),
    target: .init(domain: "api.example.com", endpoint: "/users"),
    question: .responseStatus
)
XCTAssertEqual(status.intValue, 200)
```

### String assertions (headers, body values)

```swift
let name = try Watcher.query(
    scope: .span("test"),
    target: .init(domain: "api.example.com", endpoint: "/me"),
    question: .responseBodyKeyPath(path: "user.name")
)
XCTAssertEqual(name.stringValue, "Alice")
```

### Array assertions (domains, methods, lists)

```swift
let domains = try Watcher.spanQuery(
    scope: .span("test"),
    question: .domainsContacted
)
let list = domains.arrayValue?.compactMap(\.stringValue) ?? []
XCTAssertTrue(list.contains("api.example.com"))
XCTAssertFalse(list.contains("evil.example.com"))
```

### Asserting absence

Verify a request was NOT made:

```swift
let tracking = try Watcher.query(
    scope: .span("gdpr_mode"),
    target: .init(domain: "analytics.example.com"),
    question: .requestExists
)
XCTAssertEqual(tracking.boolValue, false, "No analytics calls in GDPR mode")
```

### Asserting with reason

```swift
let answer = try Watcher.query(
    scope: .span("test"),
    target: .init(domain: "nonexistent.example.com"),
    question: .responseStatus
)
XCTAssertFalse(answer.found)
XCTAssertEqual(answer.reason, "no_matching_exchange")
```

---

## Multi-Question Efficiency

Instead of making 5 separate network requests to the daemon, combine questions:

```swift
// Instead of 5 separate queries...
let response = try Watcher.query(
    scope: .span("api_call"),
    target: .init(domain: "api.example.com", endpoint: "/users", method: .GET),
    questions: [
        .responseStatus,
        .responseHeaderExists(name: "content-type"),
        .responseContentType,
        .responseBodyKeyPath(path: "users[0].name"),
        .requestCount,
    ]
)

XCTAssertEqual(response.answers[0].intValue, 200)
XCTAssertEqual(response.answers[1].boolValue, true)
XCTAssertEqual(response.answers[2].stringValue, "json")
XCTAssertEqual(response.answers[3].stringValue, "Alice")
XCTAssertEqual(response.answers[4].intValue, 1)
```

This is a single HTTP call instead of five.

---

## Complete Annotated Test Example

A full XCUITest that exercises the most common patterns:

```swift
import XCTest
import WatcherClient

final class UserProfileTests: XCTestCase {

    private var app: XCUIApplication!

    // MARK: - Setup

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launch()

        Watcher.configure(port: 9090)
        let healthy = (try? Watcher.health()) ?? false
        try XCTSkipUnless(healthy, "Watcher daemon not running")
        try Watcher.reset()
    }

    override func tearDown() {
        app = nil
        super.tearDown()
    }

    // MARK: - Tests

    /// Verify the profile screen loads user data correctly.
    func testProfileLoadsUserData() throws {
        // -- Arrange: start span --
        try Watcher.startSpan(named: "profile_load")

        // -- Act: navigate to profile --
        app.tabBars.buttons["Profile"].tap()
        let nameLabel = app.staticTexts["user_name"]
        XCTAssertTrue(nameLabel.waitForExistence(timeout: 5))

        // -- Stop span --
        try Watcher.stopSpan()

        // -- Assert: verify the API call --
        let response = try Watcher.query(
            scope: .span("profile_load"),
            target: .init(
                domain: "api.example.com",
                endpoint: "/me",
                method: .GET
            ),
            questions: [
                .responseStatus,              // Should be 200
                .responseBodyKeyPath(path: "name"),  // Should match UI
                .requestHeaderExists(name: "authorization"),  // Should be authenticated
            ]
        )

        // The exchange was found
        XCTAssertTrue(response.found, "GET /me should have been captured")

        // Status is 200
        XCTAssertEqual(response.answers[0].intValue, 200,
                       "Profile endpoint should return 200")

        // Name is present in the response
        XCTAssertNotNil(response.answers[1].stringValue,
                        "Response should include user name")

        // Authorization header was sent
        XCTAssertEqual(response.answers[2].boolValue, true,
                       "Request should include auth header")

        // -- Assert: span-level checks --
        let errors = try Watcher.spanQuery(
            scope: .span("profile_load"),
            question: .errorCount
        )
        XCTAssertEqual(errors.intValue, 0, "No errors loading profile")
    }

    /// Verify that updating the profile sends the correct request body.
    func testProfileUpdate() throws {
        try Watcher.startSpan(named: "profile_update")

        // Navigate and edit
        app.tabBars.buttons["Profile"].tap()
        app.buttons["Edit"].tap()
        let nameField = app.textFields["name_field"]
        nameField.tap()
        nameField.clearAndEnterText("New Name")
        app.buttons["Save"].tap()

        // Wait for the save to complete
        let saved = app.staticTexts["Saved"].waitForExistence(timeout: 5)
        XCTAssertTrue(saved)

        try Watcher.stopSpan()

        // Verify the PUT/PATCH request body
        let name = try Watcher.query(
            scope: .span("profile_update"),
            target: .init(
                domain: "api.example.com",
                endpoint: "/me",
                method: .PUT
            ),
            question: .requestBodyKeyPath(path: "name")
        )
        XCTAssertEqual(name.stringValue, "New Name")

        // Verify the response status
        let status = try Watcher.query(
            scope: .span("profile_update"),
            target: .init(
                domain: "api.example.com",
                endpoint: "/me",
                method: .PUT
            ),
            question: .responseStatus
        )
        XCTAssertEqual(status.intValue, 200)
    }
}
```

---

## Tips

- **Use descriptive span names** — they appear in error messages and daemon status output.
- **Keep targets specific** — always include at least `domain` and `endpoint` to avoid matching unrelated requests.
- **Prefer the single-question convenience method** for simple assertions — it returns `Answer` directly instead of `QueryResponse`.
- **Use multi-question queries** when you need to assert multiple things about the same exchange — it's a single HTTP call.
- **Check `found` before accessing values** — if `found` is `false`, value accessors return `nil`.
- **Use span queries for high-level checks** — "did this flow make any error requests?" is a good sanity check to add to any test.
