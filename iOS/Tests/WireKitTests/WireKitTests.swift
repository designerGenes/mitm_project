import XCTest
@testable import WireKit

/// Tests for the WireClient HTTP interactions using MockURLProtocol.
final class WireKitTests: XCTestCase {
    var client: WireClient!
    var session: URLSession!

    override func setUp() {
        super.setUp()
        session = MockURLProtocol.session()
        client = WireClient(port: 9090, session: session)
    }

    override func tearDown() {
        MockURLProtocol.requestHandler = nil
        super.tearDown()
    }

    private func mockResponse(
        statusCode: Int = 200,
        json: String
    ) {
        MockURLProtocol.requestHandler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: statusCode,
                httpVersion: nil,
                headerFields: ["Content-Type": "application/json"]
            )!
            let data = json.data(using: .utf8)!
            return (response, data)
        }
    }

    // MARK: - Health

    func testHealth() throws {
        mockResponse(json: "{\"status\": \"ok\"}")
        let healthy = try client.health()
        XCTAssertTrue(healthy)
    }

    func testHealthNotOk() throws {
        mockResponse(json: "{\"status\": \"degraded\"}")
        let healthy = try client.health()
        XCTAssertFalse(healthy)
    }

    // MARK: - Status

    func testStatus() throws {
        let json = """
        {
            "config": {"api_port": 9090, "proxy_port": 8080},
            "current_span": "test",
            "exchange_count": 3,
            "spans": {"test": {"started_at": "2025-01-01T00:00:00", "stopped_at": null}}
        }
        """
        mockResponse(json: json)
        let status = try client.status()
        XCTAssertEqual(status.currentSpan, "test")
        XCTAssertEqual(status.exchangeCount, 3)
    }

    // MARK: - Span Control

    func testStartSpan() throws {
        var capturedBody: [String: Any]?
        MockURLProtocol.requestHandler = { request in
            if let body = request.httpBody {
                capturedBody = try? JSONSerialization.jsonObject(with: body) as? [String: Any]
            }
            let response = HTTPURLResponse(
                url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil
            )!
            return (response, "{\"status\": \"started\", \"name\": \"login\"}".data(using: .utf8)!)
        }

        try client.startSpan(named: "login")

        XCTAssertEqual(capturedBody?["name"] as? String, "login")
    }

    func testStopSpan() throws {
        var capturedMethod: String?
        var capturedPath: String?
        MockURLProtocol.requestHandler = { request in
            capturedMethod = request.httpMethod
            capturedPath = request.url?.path
            let response = HTTPURLResponse(
                url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil
            )!
            return (response, "{\"status\": \"stopped\", \"name\": \"login\"}".data(using: .utf8)!)
        }

        try client.stopSpan()

        XCTAssertEqual(capturedMethod, "POST")
        XCTAssertTrue(capturedPath?.hasSuffix("/span/stop") ?? false)
    }

    // MARK: - Exchange-Level Query

    func testQueryMultipleQuestions() throws {
        let responseJson = """
        {
            "found": true,
            "matched_count": 1,
            "occurrence_used": 0,
            "answers": [
                {"found": true, "value": 200},
                {"found": true, "value": "application/json"}
            ]
        }
        """
        var capturedBody: [String: Any]?
        MockURLProtocol.requestHandler = { request in
            if let body = request.httpBody {
                capturedBody = try? JSONSerialization.jsonObject(with: body) as? [String: Any]
            }
            let response = HTTPURLResponse(
                url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil
            )!
            return (response, responseJson.data(using: .utf8)!)
        }

        let resp = try client.query(
            scope: .span("login"),
            target: .init(domain: "api.example.com", endpoint: "/auth", method: .POST),
            questions: [.responseStatus, .responseHeaderValue(name: "Content-Type")]
        )

        XCTAssertTrue(resp.found)
        XCTAssertEqual(resp.answers.count, 2)
        XCTAssertEqual(resp.answers[0].intValue, 200)
        XCTAssertEqual(resp.answers[1].stringValue, "application/json")

        // Verify request body
        XCTAssertEqual(capturedBody?["scope"] as? String, "login")
        let target = capturedBody?["target"] as! [String: Any]
        XCTAssertEqual(target["domain"] as? String, "api.example.com")
    }

    func testQuerySingleQuestion() throws {
        let responseJson = """
        {
            "found": true,
            "matched_count": 1,
            "occurrence_used": 0,
            "answers": [{"found": true, "value": 200}]
        }
        """
        mockResponse(json: responseJson)

        let answer = try client.query(
            scope: .span("login"),
            target: .init(domain: "api.example.com", endpoint: "/auth", method: .POST),
            question: .responseStatus
        )

        XCTAssertTrue(answer.found)
        XCTAssertEqual(answer.intValue, 200)
    }

    func testQueryNotFound() throws {
        let responseJson = """
        {
            "found": false,
            "matched_count": 0,
            "occurrence_used": null,
            "reason": "no_matching_exchange",
            "answers": []
        }
        """
        mockResponse(json: responseJson)

        let answer = try client.query(
            scope: .span("login"),
            target: .init(domain: "api.example.com", endpoint: "/unknown"),
            question: .responseStatus
        )

        XCTAssertFalse(answer.found)
        XCTAssertEqual(answer.reason, "no_matching_exchange")
    }

    // MARK: - Span-Level Query

    func testSpanQuery() throws {
        let responseJson = """
        {
            "found": true,
            "answers": [
                {"found": true, "value": 14},
                {"found": true, "value": ["api.example.com", "cdn.example.com"]}
            ]
        }
        """
        var capturedBody: [String: Any]?
        MockURLProtocol.requestHandler = { request in
            if let body = request.httpBody {
                capturedBody = try? JSONSerialization.jsonObject(with: body) as? [String: Any]
            }
            let response = HTTPURLResponse(
                url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil
            )!
            return (response, responseJson.data(using: .utf8)!)
        }

        let resp = try client.spanQuery(
            scope: .span("login"),
            filter: SpanFilter(domain: "api.example.com"),
            questions: [.totalRequestCount, .domainsContacted]
        )

        XCTAssertTrue(resp.found)
        XCTAssertEqual(resp.answers[0].intValue, 14)

        // Verify filter was sent
        let filter = capturedBody?["filter"] as! [String: Any]
        XCTAssertEqual(filter["domain"] as? String, "api.example.com")
    }

    func testSpanQuerySingleQuestion() throws {
        let responseJson = """
        {
            "found": true,
            "answers": [{"found": true, "value": 5}]
        }
        """
        mockResponse(json: responseJson)

        let answer = try client.spanQuery(
            scope: .span("login"),
            question: .totalRequestCount
        )

        XCTAssertTrue(answer.found)
        XCTAssertEqual(answer.intValue, 5)
    }

    // MARK: - Reset

    func testReset() throws {
        var capturedMethod: String?
        var capturedPath: String?
        MockURLProtocol.requestHandler = { request in
            capturedMethod = request.httpMethod
            capturedPath = request.url?.path
            let response = HTTPURLResponse(
                url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil
            )!
            return (response, "{\"status\": \"reset\"}".data(using: .utf8)!)
        }

        try client.reset()

        XCTAssertEqual(capturedMethod, "POST")
        XCTAssertTrue(capturedPath?.hasSuffix("/reset") ?? false)
    }

    // MARK: - Error Handling

    func testHTTPError() throws {
        mockResponse(statusCode: 500, json: "{\"detail\": \"Internal Server Error\"}")

        XCTAssertThrowsError(try client.health()) { error in
            guard case WireError.unexpectedStatus(let code, _) = error else {
                XCTFail("Expected unexpectedStatus, got \(error)")
                return
            }
            XCTAssertEqual(code, 500)
        }
    }

    func testConnectionError() throws {
        MockURLProtocol.requestHandler = { _ in
            throw URLError(.cannotConnectToHost)
        }

        XCTAssertThrowsError(try client.health()) { error in
            guard case WireError.connectionFailed = error else {
                XCTFail("Expected connectionFailed, got \(error)")
                return
            }
        }
    }

    func testDecodingError() throws {
        mockResponse(json: "not valid json {{{")

        XCTAssertThrowsError(try client.status()) { error in
            guard case WireError.decodingFailed = error else {
                XCTFail("Expected decodingFailed, got \(error)")
                return
            }
        }
    }

    // MARK: - Wire Static Facade

    func testWireConfigureAndQuery() throws {
        Wire.configure(port: 9090, session: session)

        let responseJson = """
        {
            "found": true,
            "matched_count": 1,
            "occurrence_used": 0,
            "answers": [{"found": true, "value": 201}]
        }
        """
        mockResponse(json: responseJson)

        let answer = try Wire.query(
            scope: .span("test"),
            target: .init(endpoint: "/users", method: .POST),
            question: .responseStatus
        )

        XCTAssertEqual(answer.intValue, 201)
    }
}
