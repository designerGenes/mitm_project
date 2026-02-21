/// Live integration tests that demonstrate calling the Wire Python backend
/// with realistic query patterns — the same patterns used in XCUITests.
///
/// Prerequisites:
///   1. Start the WIRE daemon:  cd python && uv run wire start --foreground --verbose
///   2. Run these tests:           cd iOS && swift test --filter IntegrationTests
///
/// These tests generate HTTP traffic through the mitmproxy (port 8080), then
/// use the WireKit client to query the captured traffic (port 9090).
/// Tests are automatically skipped if the daemon is not running.

import XCTest
@testable import WireKit

final class LiveIntegrationTests: XCTestCase {

    // MARK: - Setup

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

    override func setUp() {
        super.setUp()
        Wire.configure(port: 9090)

        // Skip entire test class if daemon is not reachable
        guard (try? Wire.health()) == true else {
            continueAfterFailure = false
            XCTFail("WIRE daemon (WIREd) not running on :9090. Start it with: uv run wire start --foreground")
            return
        }
        try? Wire.reset()
    }

    // MARK: - Helpers

    /// Make an HTTP request through the mitmproxy and wait for completion.
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
    // MARK: - 1. Daemon Health & Status
    // =========================================================================

    /// Verify the daemon is alive and responding.
    func testDaemonHealthCheck() throws {
        let healthy = try Wire.health()
        XCTAssertTrue(healthy, "Daemon should report healthy")
    }

    /// Verify status reports empty state after reset.
    func testStatusAfterReset() throws {
        let status = try Wire.status()
        XCTAssertEqual(status.exchangeCount, 0, "Should have zero exchanges after reset")
        XCTAssertNil(status.currentSpan, "No span should be active")
        XCTAssertTrue(status.spans.isEmpty, "Span history should be empty")
    }

    // =========================================================================
    // MARK: - 2. Span Lifecycle
    // =========================================================================

    /// Verify that starting and stopping a span updates the daemon state.
    func testSpanStartStop() throws {
        try Wire.startSpan(named: "lifecycle_test")

        let during = try Wire.status()
        XCTAssertEqual(during.currentSpan, "lifecycle_test")

        try Wire.stopSpan()

        let after = try Wire.status()
        XCTAssertNil(after.currentSpan, "Span should be stopped")
        XCTAssertNotNil(after.spans["lifecycle_test"], "Span should be in history")
    }

    /// Verify that starting a new span auto-closes the previous one.
    func testSpanAutoClose() throws {
        try Wire.startSpan(named: "first")
        try Wire.startSpan(named: "second")

        let status = try Wire.status()
        XCTAssertEqual(status.currentSpan, "second")
        // "first" should exist in history with a stopped_at timestamp
        XCTAssertNotNil(status.spans["first"]?.stoppedAt,
                        "First span should have been auto-closed")
    }

    // =========================================================================
    // MARK: - 3. Traffic Capture & Basic Queries
    // =========================================================================

    /// Capture a GET request and verify it was recorded.
    func testCaptureGETRequest() throws {
        try Wire.startSpan(named: "get_test")

        proxyGET("http://httpbin.org/get")
        waitForCapture()

        try Wire.stopSpan()

        // Verify the request exists
        let exists = try Wire.query(
            scope: .span("get_test"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .requestExists
        )
        XCTAssertTrue(exists.found, "Query should find the exchange")
        XCTAssertEqual(exists.boolValue, true, "Request should exist")
    }

    /// Capture a request and verify the response status code.
    func testQueryResponseStatus() throws {
        try Wire.startSpan(named: "status_test")

        proxyGET("http://httpbin.org/status/200")
        waitForCapture()

        try Wire.stopSpan()

        let answer = try Wire.query(
            scope: .span("status_test"),
            target: .init(domain: "httpbin.org", endpoint: "/status/200", method: .GET),
            question: .responseStatus
        )
        XCTAssertTrue(answer.found)
        XCTAssertEqual(answer.intValue, 200, "Should capture 200 status")
    }

    /// Capture a request and verify a response header value.
    func testQueryResponseHeader() throws {
        try Wire.startSpan(named: "header_test")

        proxyGET("http://httpbin.org/get")
        waitForCapture()

        try Wire.stopSpan()

        let contentType = try Wire.query(
            scope: .span("header_test"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .responseHeaderValue(name: "content-type")
        )
        XCTAssertTrue(contentType.found)
        let value = contentType.stringValue ?? ""
        XCTAssertTrue(value.contains("application/json"),
                      "httpbin /get returns JSON, got: \(value)")
    }

    // =========================================================================
    // MARK: - 4. JSON Body Queries
    // =========================================================================

    /// Verify we can extract a value from the JSON response body using a key path.
    func testQueryResponseBodyKeyPath() throws {
        try Wire.startSpan(named: "body_test")

        proxyGET("http://httpbin.org/get?greeting=hello")
        waitForCapture()

        try Wire.stopSpan()

        // httpbin /get echoes query params in "args"
        let greeting = try Wire.query(
            scope: .span("body_test"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .responseBodyKeyPath(path: "args.greeting")
        )
        XCTAssertTrue(greeting.found, "Key path 'args.greeting' should exist")
        XCTAssertEqual(greeting.stringValue, "hello")
    }

    /// Verify POST request body is captured and queryable.
    func testQueryRequestBody() throws {
        try Wire.startSpan(named: "post_test")

        proxyPOST("http://httpbin.org/post", json: ["username": "alice", "role": "admin"])
        waitForCapture()

        try Wire.stopSpan()

        let username = try Wire.query(
            scope: .span("post_test"),
            target: .init(domain: "httpbin.org", endpoint: "/post", method: .POST),
            question: .requestBodyKeyPath(path: "username")
        )
        XCTAssertTrue(username.found)
        XCTAssertEqual(username.stringValue, "alice")
    }

    /// Verify response body substring search.
    func testQueryResponseBodyContains() throws {
        try Wire.startSpan(named: "contains_test")

        proxyGET("http://httpbin.org/get")
        waitForCapture()

        try Wire.stopSpan()

        let contains = try Wire.query(
            scope: .span("contains_test"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .responseBodyContains(substring: "httpbin.org")
        )
        XCTAssertTrue(contains.found)
        XCTAssertEqual(contains.boolValue, true,
                       "httpbin /get response should contain 'httpbin.org'")
    }

    // =========================================================================
    // MARK: - 5. Query Parameters
    // =========================================================================

    /// Verify captured query parameters can be queried.
    func testQueryParamValue() throws {
        try Wire.startSpan(named: "params_test")

        proxyGET("http://httpbin.org/get?page=3&sort=name")
        waitForCapture()

        try Wire.stopSpan()

        let page = try Wire.query(
            scope: .span("params_test"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .queryParamValue(name: "page")
        )
        XCTAssertTrue(page.found)
        XCTAssertEqual(page.stringValue, "3")

        let sortExists = try Wire.query(
            scope: .span("params_test"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .queryParamExists(name: "sort")
        )
        XCTAssertEqual(sortExists.boolValue, true)
    }

    // =========================================================================
    // MARK: - 6. Multiple Requests & Occurrence Selection
    // =========================================================================

    /// Verify request counting across multiple calls to the same endpoint.
    func testRequestCount() throws {
        try Wire.startSpan(named: "count_test")

        // Make 3 requests to the same endpoint
        proxyGET("http://httpbin.org/get")
        proxyGET("http://httpbin.org/get")
        proxyGET("http://httpbin.org/get")
        waitForCapture()

        try Wire.stopSpan()

        let count = try Wire.query(
            scope: .span("count_test"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET),
            question: .requestCount
        )
        XCTAssertTrue(count.found)
        XCTAssertEqual(count.intValue, 3, "Should have captured 3 requests")
    }

    /// Verify occurrence selection: first vs most recent request.
    func testOccurrenceSelection() throws {
        try Wire.startSpan(named: "occurrence_test")

        proxyGET("http://httpbin.org/get?seq=first")
        proxyGET("http://httpbin.org/get?seq=second")
        proxyGET("http://httpbin.org/get?seq=last")
        waitForCapture()

        try Wire.stopSpan()

        // First occurrence (index 0)
        let first = try Wire.query(
            scope: .span("occurrence_test"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET, occurrence: 0),
            question: .queryParamValue(name: "seq")
        )
        XCTAssertEqual(first.stringValue, "first")

        // Most recent (index -1)
        let last = try Wire.query(
            scope: .span("occurrence_test"),
            target: .init(domain: "httpbin.org", endpoint: "/get", method: .GET, occurrence: -1),
            question: .queryParamValue(name: "seq")
        )
        XCTAssertEqual(last.stringValue, "last")
    }

    // =========================================================================
    // MARK: - 7. Multi-Question Query
    // =========================================================================

    /// Verify sending multiple questions in a single query request.
    func testMultipleQuestionsInSingleQuery() throws {
        try Wire.startSpan(named: "multi_q")

        proxyGET("http://httpbin.org/get")
        waitForCapture()

        try Wire.stopSpan()

        let response = try Wire.query(
            scope: .span("multi_q"),
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

        XCTAssertEqual(response.answers[0].intValue, 200, "Status should be 200")
        XCTAssertEqual(response.answers[1].boolValue, true, "Content-Type header should exist")
        XCTAssertNotNil(response.answers[2].stringValue, "Content type should be a string")
        XCTAssertEqual(response.answers[3].boolValue, true, "Request should exist")
    }

    // =========================================================================
    // MARK: - 8. Span-Level Queries
    // =========================================================================

    /// Verify total request count across a span.
    func testSpanTotalRequestCount() throws {
        try Wire.startSpan(named: "span_count")

        proxyGET("http://httpbin.org/get")
        proxyGET("http://httpbin.org/status/201")
        proxyPOST("http://httpbin.org/post", json: ["key": "value"])
        waitForCapture()

        try Wire.stopSpan()

        let count = try Wire.spanQuery(
            scope: .span("span_count"),
            question: .totalRequestCount
        )
        XCTAssertTrue(count.found)
        XCTAssertEqual(count.intValue, 3, "Should have captured 3 exchanges in span")
    }

    /// Verify domains contacted in a span.
    func testSpanDomainsContacted() throws {
        try Wire.startSpan(named: "domains_test")

        proxyGET("http://httpbin.org/get")
        proxyGET("http://example.com")
        waitForCapture()

        try Wire.stopSpan()

        let domains = try Wire.spanQuery(
            scope: .span("domains_test"),
            question: .domainsContacted
        )
        XCTAssertTrue(domains.found)
        let domainList = domains.arrayValue?.compactMap(\.stringValue) ?? []
        XCTAssertTrue(domainList.contains("httpbin.org"), "Should include httpbin.org")
        XCTAssertTrue(domainList.contains("example.com") || domainList.contains("www.example.com"),
                      "Should include example.com, got: \(domainList)")
    }

    /// Verify methods used in a span.
    func testSpanMethodsUsed() throws {
        try Wire.startSpan(named: "methods_test")

        proxyGET("http://httpbin.org/get")
        proxyPOST("http://httpbin.org/post", json: ["a": 1])
        waitForCapture()

        try Wire.stopSpan()

        let methods = try Wire.spanQuery(
            scope: .span("methods_test"),
            question: .methodsUsed
        )
        XCTAssertTrue(methods.found)
        let methodList = methods.arrayValue?.compactMap(\.stringValue) ?? []
        XCTAssertTrue(methodList.contains("GET"))
        XCTAssertTrue(methodList.contains("POST"))
    }

    /// Verify span query with a domain filter.
    func testSpanQueryWithFilter() throws {
        try Wire.startSpan(named: "filter_test")

        proxyGET("http://httpbin.org/get")
        proxyGET("http://httpbin.org/status/200")
        proxyGET("http://example.com")
        waitForCapture()

        try Wire.stopSpan()

        // Filter to only httpbin.org
        let count = try Wire.spanQuery(
            scope: .span("filter_test"),
            filter: SpanFilter(domain: "httpbin.org"),
            question: .totalRequestCount
        )
        XCTAssertTrue(count.found)
        XCTAssertEqual(count.intValue, 2,
                       "Only 2 requests went to httpbin.org")
    }

    // =========================================================================
    // MARK: - 9. Not-Found Cases
    // =========================================================================

    /// Verify query returns found=false for an unrecorded endpoint.
    func testQueryNotFound() throws {
        try Wire.startSpan(named: "notfound_test")
        proxyGET("http://httpbin.org/get")
        waitForCapture()
        try Wire.stopSpan()

        let answer = try Wire.query(
            scope: .span("notfound_test"),
            target: .init(domain: "nonexistent.example.com", endpoint: "/nope"),
            question: .responseStatus
        )
        XCTAssertFalse(answer.found, "No exchange should match a domain we never called")
        XCTAssertEqual(answer.reason, "no_matching_exchange")
    }

    /// Verify span query returns found=false for a nonexistent span.
    func testSpanQueryNotFound() throws {
        let answer = try Wire.spanQuery(
            scope: .span("span_that_never_existed"),
            question: .totalRequestCount
        )
        XCTAssertFalse(answer.found)
        XCTAssertEqual(answer.reason, "span_not_found")
    }
}
