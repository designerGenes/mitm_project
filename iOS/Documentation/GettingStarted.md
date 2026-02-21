# Getting Started with WatcherClient

WatcherClient is a Swift library for querying HTTP traffic captured by the Watcher daemon. It's designed for iOS UI tests — you interact with your app, then ask Watcher what network calls happened and assert on the results.

## Installation

### Swift Package Manager

Add the dependency to your `Package.swift`:

```swift
dependencies: [
    .package(url: "https://github.com/your-org/WatcherClient.git", from: "0.1.0"),
]
```

Or add it to a test target in an existing package:

```swift
.testTarget(
    name: "YourUITests",
    dependencies: ["WatcherClient"]
),
```

**In Xcode:** File > Add Package Dependencies, then enter the repository URL.

The package supports iOS 16+ and macOS 13+.

### CocoaPods

```ruby
target 'YourUITests' do
  pod 'WatcherClient'
end
```

Then run `pod install`.

## Prerequisites

### Start the Watcher Daemon

The daemon captures traffic via mitmproxy. Start it before running tests:

```bash
# Install (if not already)
cd python && uv sync

# Run in the foreground (recommended for development)
uv run watcher start --foreground --verbose

# Or run as a background launchd service
uv run watcher start
```

The daemon exposes two ports:
- **8080** — mitmproxy (route your app's traffic through this)
- **9090** — HTTP API (WatcherClient talks to this)

### Verify it's Running

```bash
uv run watcher status
# or: curl http://localhost:9090/health
```

## Configuration

WatcherClient connects to `localhost:9090` by default. If you're using custom ports, configure it in your test setUp:

```swift
import WatcherClient

// Default — connects to localhost:9090
Watcher.configure()

// Custom port
Watcher.configure(port: 9091)

// Full customization
Watcher.configure(
    port: 9090,
    host: "localhost",
    timeout: 15  // seconds
)
```

## Your First Test

Here's a complete example that captures traffic from a login flow and asserts on the results:

```swift
import XCTest
import WatcherClient

final class LoginTests: XCTestCase {

    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launch()

        // Configure and verify daemon is running
        Watcher.configure(port: 9090)
        let healthy = (try? Watcher.health()) ?? false
        try XCTSkipUnless(healthy, "Watcher daemon not running on :9090")

        // Clear previous data
        try Watcher.reset()
    }

    func testLoginReturns200() throws {
        // 1. Start a span to tag traffic
        try Watcher.startSpan(named: "login")

        // 2. Interact with the UI (triggers network calls)
        app.textFields["email"].tap()
        app.textFields["email"].typeText("alice@example.com")
        app.secureTextFields["password"].tap()
        app.secureTextFields["password"].typeText("secret")
        app.buttons["Log In"].tap()

        // 3. Wait for the request to complete
        let loggedIn = app.staticTexts["Welcome"].waitForExistence(timeout: 5)
        XCTAssertTrue(loggedIn)

        // 4. Stop the span
        try Watcher.stopSpan()

        // 5. Query the captured traffic
        let answer = try Watcher.query(
            scope: .span("login"),
            target: .init(domain: "api.example.com", endpoint: "/auth", method: .POST),
            question: .responseStatus
        )

        // 6. Assert
        XCTAssertTrue(answer.found)
        XCTAssertEqual(answer.intValue, 200)
    }
}
```

## Proxy Session Setup (Integration Tests)

For integration tests that generate traffic directly (without a UI), create a URLSession routed through mitmproxy:

```swift
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

Traffic from this session flows through mitmproxy and gets captured by Watcher. The iOS Simulator shares the host Mac's network stack, so `127.0.0.1` reaches the daemon.

## Core Concepts

### Spans

Spans tag traffic with a name. Start a span before the action you want to test, stop it after:

```swift
try Watcher.startSpan(named: "checkout")
// ... user actions that trigger network calls ...
try Watcher.stopSpan()
```

Only one span can be active at a time. Starting a new span auto-closes the previous one.

### Queries

Queries ask questions about captured traffic. Every query has three parts:

1. **Scope** — which span to look in (`.span("login")`, `.unspanned`, `.all`)
2. **Target** — which exchange to select (domain, endpoint, method, occurrence)
3. **Question** — what to ask about it (`.responseStatus`, `.responseBodyKeyPath(path:)`, etc.)

```swift
let answer = try Watcher.query(
    scope: .span("login"),
    target: .init(domain: "api.example.com", endpoint: "/auth"),
    question: .responseStatus
)
```

### Answers

Every answer has a `found` property and an optional typed value:

```swift
if answer.found {
    XCTAssertEqual(answer.intValue, 200)
}
```

## Next Steps

- [API Reference](APIReference.md) — complete reference for all types and methods
- [Query Guide](QueryGuide.md) — cookbook of query examples by category
- [Testing Patterns](TestingPatterns.md) — XCUITest best practices with Watcher
