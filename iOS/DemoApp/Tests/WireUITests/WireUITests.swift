/// XCUITests that demonstrate calling the Wire Python backend with
/// realistic queries through the WireClient Swift library.
///
/// Prerequisites:
///   1. Start the WIRE daemon:  cd python && uv run wire start --foreground --verbose
///   2. Generate Xcode project:    cd iOS/DemoApp && tuist generate
///   3. Run tests:                 xcodebuild test -project DemoApp.xcodeproj -scheme DemoApp \
///                                   -destination 'platform=iOS Simulator,name=iPhone 16' \
///                                   -only-testing WireUITests
///
/// Tests are automatically skipped if the daemon is not running.

import XCTest
import WireKit

final class WireUITests: XCTestCase {

    // MARK: - Properties

    private var app: XCUIApplication!

    /// URLSession configured to route through the mitmproxy on port 8080.
    /// The iOS Simulator shares the host network stack, so 127.0.0.1 reaches the daemon.
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

    // MARK: - Setup / Teardown

    override func setUpWithError() throws {
        continueAfterFailure = false

        app = XCUIApplication()
        app.launch()

        Wire.configure(port: 18081)

        // Skip all tests if daemon is unreachable
        let healthy = (try? Wire.health()) ?? false
        try XCTSkipUnless(healthy, "WIRE daemon (WIREd) not running on :18081")

        try Wire.reset()
    }

    override func tearDown() {
        app = nil
        super.tearDown()
    }

    // MARK: - Helpers

    /// Make an HTTP GET through the mitmproxy and wait for completion.
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

    /// Make an HTTP POST through the mitmproxy with a JSON body.
    @discardableResult
    private func proxyPOST(_ urlString: String, json: [String: Any]) -> (Data?, HTTPURLResponse?) {
        let url = URL(string: urlString)!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: json)

        let expectation = expectation(description: "POST \(urlString)")
        var resultData: Data?
        var resultResponse: HTTPURLResponse?

        let task = proxySession.dataTask(with: request) { data, response, _ in
            resultData = data
            resultResponse = response as? HTTPURLResponse
            expectation.fulfill()
        }
        task.resume()
        wait(for: [expectation], timeout: 15)
        return (resultData, resultResponse)
    }

    /// Brief pause to let the daemon process captured traffic.
    private func waitForCapture() {
        Thread.sleep(forTimeInterval: 0.3)
    }

    // =========================================================================
    // MARK: - 1. Health & Status (2 tests)
    // =========================================================================

    /// Verify the daemon health endpoint returns true.
    func testHealthCheckReturnsTrue() throws {
        let healthy = try Wire.health()
        XCTAssertTrue(healthy, "Daemon should report healthy")
    }

    /// Verify status returns valid config with expected ports.
    func testStatusReturnsValidConfig() throws {
        let status = try Wire.status()
        XCTAssertEqual(status.exchangeCount, 0, "Should have zero exchanges after reset")
        XCTAssertNil(status.currentSpan, "No span should be active after reset")
        XCTAssertNotNil(status.config, "Status should include config")
    }

    // =========================================================================
    // MARK: - 2. Span Lifecycle (2 tests)
    // =========================================================================

    /// Verify starting and stopping a span updates daemon state.
    func testSpanStartStop() throws {
        try Wire.startSpan(named: "ui_lifecycle")

        let during = try Wire.status()
        XCTAssertEqual(during.currentSpan, "ui_lifecycle")

        try Wire.stopSpan()

        let after = try Wire.status()
        XCTAssertNil(after.currentSpan, "Span should be stopped")
        XCTAssertNotNil(after.spans["ui_lifecycle"], "Span should be in history")
    }

    /// Verify span appears in status with timing info after stop.
    func testSpanAppearsInStatus() throws {
        try Wire.startSpan(named: "status_span")
        try Wire.stopSpan()

        let status = try Wire.status()
        let span = status.spans["status_span"]
        XCTAssertNotNil(span, "Stopped span should appear in status")
        XCTAssertNotNil(span?.stoppedAt, "Stopped span should have stoppedAt timestamp")
    }

    // =========================================================================
    // MARK: - 3. Traffic Capture (2 tests)
    // =========================================================================

    /// Capture a GET request through the proxy and verify response status.
    func testCaptureGETResponseStatus() throws {
        try Wire.startSpan(named: "ui_get_status")

        proxyGET("http://httpbin.org/status/200")
        waitForCapture()

        try Wire.stopSpan()

        let answer = try Wire.query(
            scope: .span("ui_get_status"),
            target: .init(domain: "httpbin.org", endpoint: "/status/200", method: .GET),
            question: .responseStatus
        )
        XCTAssertTrue(answer.found)
        XCTAssertEqual(answer.intValue, 200, "Should capture 200 status")
    }

    /// Capture a POST with JSON body and verify request body is queryable.
    func testCapturePOSTRequestBody() throws {
        try Wire.startSpan(named: "ui_post_body")

        proxyPOST("http://httpbin.org/post", json: ["username": "alice", "role": "admin"])
        waitForCapture()

        try Wire.stopSpan()

        let username = try Wire.query(
            scope: .span("ui_post_body"),
            target: .init(domain: "httpbin.org", endpoint: "/post", method: .POST),
            question: .requestBodyKeyPath(path: "username")
        )
        XCTAssertTrue(username.found)
        XCTAssertEqual(username.stringValue, "alice")
    }

    // =========================================================================
    // MARK: - 4. Response Body Queries (2 tests)
    // =========================================================================

    /// Query a nested value from the JSON response body using a key path.
    func testResponseBodyKeyPath() throws {
        try Wire.startSpan(named: "ui_keypath")

        proxyGET("http://httpbin.org/get?greeting=hello")
        waitForCapture()

        try Wire.stopSpan()

        // httpbin /get echoes query params in "args"
        let greeting = try Wire.query(
            scope: .span("ui_keypath"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .responseBodyKeyPath(path: "args.greeting")
        )
        XCTAssertTrue(greeting.found, "Key path 'args.greeting' should exist")
        XCTAssertEqual(greeting.stringValue, "hello")
    }

    /// Query whether the response body contains a substring.
    func testResponseBodyContains() throws {
        try Wire.startSpan(named: "ui_contains")

        proxyGET("http://httpbin.org/get")
        waitForCapture()

        try Wire.stopSpan()

        let contains = try Wire.query(
            scope: .span("ui_contains"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .responseBodyContains(substring: "httpbin.org")
        )
        XCTAssertTrue(contains.found)
        XCTAssertEqual(contains.boolValue, true,
                       "httpbin /get response should contain 'httpbin.org'")
    }

    // =========================================================================
    // MARK: - 5. Request Inspection (2 tests)
    // =========================================================================

    /// Query a request header value from captured traffic.
    func testRequestHeaderValue() throws {
        try Wire.startSpan(named: "ui_req_header")

        proxyGET("http://httpbin.org/get")
        waitForCapture()

        try Wire.stopSpan()

        let host = try Wire.query(
            scope: .span("ui_req_header"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .requestHeaderValue(name: "host")
        )
        XCTAssertTrue(host.found)
        let hostValue = host.stringValue ?? ""
        XCTAssertTrue(hostValue.contains("httpbin.org"),
                      "Host header should contain httpbin.org, got: \(hostValue)")
    }

    /// Query captured URL query parameters.
    func testRequestQueryParams() throws {
        try Wire.startSpan(named: "ui_params")

        proxyGET("http://httpbin.org/get?page=3&sort=name")
        waitForCapture()

        try Wire.stopSpan()

        let page = try Wire.query(
            scope: .span("ui_params"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .queryParamValue(name: "page")
        )
        XCTAssertTrue(page.found)
        XCTAssertEqual(page.stringValue, "3")

        let sortExists = try Wire.query(
            scope: .span("ui_params"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .queryParamExists(name: "sort")
        )
        XCTAssertEqual(sortExists.boolValue, true)
    }

    // =========================================================================
    // MARK: - 6. Counting & Occurrence (2 tests)
    // =========================================================================

    /// Count exchanges for a domain/endpoint combination.
    func testCountExchanges() throws {
        try Wire.startSpan(named: "ui_count")

        proxyGET("http://httpbin.org/get")
        proxyGET("http://httpbin.org/get")
        proxyGET("http://httpbin.org/get")
        waitForCapture()

        try Wire.stopSpan()

        let count = try Wire.query(
            scope: .span("ui_count"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .requestCount
        )
        XCTAssertTrue(count.found)
        XCTAssertEqual(count.intValue, 3, "Should have captured 3 requests")
    }

    /// Select a specific occurrence by index (first vs last).
    func testOccurrenceIndex() throws {
        try Wire.startSpan(named: "ui_occurrence")

        proxyGET("http://httpbin.org/get?seq=first")
        proxyGET("http://httpbin.org/get?seq=second")
        proxyGET("http://httpbin.org/get?seq=last")
        waitForCapture()

        try Wire.stopSpan()

        // First occurrence (index 0)
        let first = try Wire.query(
            scope: .span("ui_occurrence"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET, occurrence: 0),
            question: .queryParamValue(name: "seq")
        )
        XCTAssertEqual(first.stringValue, "first")

        // Most recent (index -1)
        let last = try Wire.query(
            scope: .span("ui_occurrence"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET, occurrence: -1),
            question: .queryParamValue(name: "seq")
        )
        XCTAssertEqual(last.stringValue, "last")
    }

    // =========================================================================
    // MARK: - 7. Multi-Question Queries (2 tests)
    // =========================================================================

    /// Send multiple questions in a single query and verify all answers returned.
    func testMultipleQuestionsInSingleQuery() throws {
        try Wire.startSpan(named: "ui_multi_q")

        proxyGET("http://httpbin.org/get")
        waitForCapture()

        try Wire.stopSpan()

        let response = try Wire.query(
            scope: .span("ui_multi_q"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            questions: [
                .responseStatus,
                .responseHeaderExists(name: "content-type"),
                .responseContentType,
                .requestExists,
            ]
        )
        XCTAssertTrue(response.found)
        XCTAssertEqual(response.answers.count, 4, "Should have 4 answers")
    }

    /// Verify each answer in a multi-question query has the expected values.
    func testMultipleQuestionsAnswerValues() throws {
        try Wire.startSpan(named: "ui_multi_vals")

        proxyGET("http://httpbin.org/get")
        waitForCapture()

        try Wire.stopSpan()

        let response = try Wire.query(
            scope: .span("ui_multi_vals"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            questions: [
                .responseStatus,
                .requestExists,
            ]
        )
        XCTAssertEqual(response.answers[0].intValue, 200, "Status should be 200")
        XCTAssertEqual(response.answers[1].boolValue, true, "Request should exist")
    }

    // =========================================================================
    // MARK: - 8. Span-Level Queries (2 tests)
    // =========================================================================

    /// Query total request count across a span.
    func testSpanTotalRequestCount() throws {
        try Wire.startSpan(named: "ui_span_count")

        proxyGET("http://httpbin.org/get")
        proxyGET("http://httpbin.org/status/201")
        proxyPOST("http://httpbin.org/post", json: ["key": "value"])
        waitForCapture()

        try Wire.stopSpan()

        let count = try Wire.spanQuery(
            scope: .span("ui_span_count"),
            question: .totalRequestCount
        )
        XCTAssertTrue(count.found)
        XCTAssertEqual(count.intValue, 3, "Should have 3 exchanges in span")
    }

    /// Query domains contacted within a span.
    func testSpanDomainsContacted() throws {
        try Wire.startSpan(named: "ui_domains")

        proxyGET("http://httpbin.org/get")
        proxyGET("http://example.com")
        waitForCapture()

        try Wire.stopSpan()

        let domains = try Wire.spanQuery(
            scope: .span("ui_domains"),
            question: .domainsContacted
        )
        XCTAssertTrue(domains.found)
        let domainList = domains.arrayValue?.compactMap(\.stringValue) ?? []
        XCTAssertTrue(domainList.contains("httpbin.org"), "Should include httpbin.org")
        XCTAssertTrue(
            domainList.contains("example.com") || domainList.contains("www.example.com"),
            "Should include example.com, got: \(domainList)"
        )
    }

    // =========================================================================
    // MARK: - 9. Error / Not-Found (2 tests)
    // =========================================================================

    /// Query a non-existent domain returns found=false.
    func testQueryNonExistentDomainReturnsNotFound() throws {
        try Wire.startSpan(named: "ui_notfound")
        proxyGET("http://httpbin.org/get")
        waitForCapture()
        try Wire.stopSpan()

        let answer = try Wire.query(
            scope: .span("ui_notfound"),
            target: .init(domain: "nonexistent.example.com", endpoint: "/nope"),
            question: .responseStatus
        )
        XCTAssertFalse(answer.found, "No exchange should match a domain we never called")
        XCTAssertEqual(answer.reason, "no_matching_exchange")
    }

    /// Query a non-existent span returns found=false with span_not_found reason.
    func testQueryNonExistentSpanReturnsNotFound() throws {
        let answer = try Wire.spanQuery(
            scope: .span("span_that_never_existed"),
            question: .totalRequestCount
        )
        XCTAssertFalse(answer.found)
        XCTAssertEqual(answer.reason, "span_not_found")
    }
}
