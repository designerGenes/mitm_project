import XCTest
@testable import WireKit

/// Verify that all request models encode to JSON matching the Python API format.
final class EncodingTests: XCTestCase {
    let encoder = JSONEncoder()

    private func encode<T: Encodable>(_ value: T) throws -> [String: Any] {
        let data = try encoder.encode(value)
        return try JSONSerialization.jsonObject(with: data) as! [String: Any]
    }

    private func encodeToString<T: Encodable>(_ value: T) throws -> String {
        let data = try encoder.encode(value)
        return String(data: data, encoding: .utf8)!
    }

    // MARK: - Scope

    func testScopeSpan() throws {
        let json = try encodeToString(Scope.span("login"))
        XCTAssertEqual(json, "\"login\"")
    }

    func testScopeUnspanned() throws {
        let json = try encodeToString(Scope.unspanned)
        XCTAssertEqual(json, "\"unspanned\"")
    }

    func testScopeAll() throws {
        let json = try encodeToString(Scope.all)
        XCTAssertEqual(json, "\"all\"")
    }

    // MARK: - QueryTarget

    func testQueryTargetFull() throws {
        let target = QueryTarget(domain: "api.example.com", endpoint: "/users", method: .GET, occurrence: 0)
        let json = try encode(target)
        XCTAssertEqual(json["domain"] as? String, "api.example.com")
        XCTAssertEqual(json["endpoint"] as? String, "/users")
        XCTAssertEqual(json["method"] as? String, "GET")
        XCTAssertEqual(json["occurrence"] as? Int, 0)
    }

    func testQueryTargetPartial() throws {
        let target = QueryTarget(domain: "api.example.com")
        let json = try encode(target)
        XCTAssertEqual(json["domain"] as? String, "api.example.com")
        XCTAssertNil(json["endpoint"])
        XCTAssertNil(json["method"])
        XCTAssertNil(json["occurrence"])
    }

    func testQueryTargetEmpty() throws {
        let target = QueryTarget()
        let json = try encode(target)
        XCTAssertNil(json["domain"])
    }

    func testQueryTargetNegativeOccurrence() throws {
        let target = QueryTarget(occurrence: -1)
        let json = try encode(target)
        XCTAssertEqual(json["occurrence"] as? Int, -1)
    }

    // MARK: - SpanFilter

    func testSpanFilter() throws {
        let filter = SpanFilter(domain: "api.example.com", method: .POST)
        let json = try encode(filter)
        XCTAssertEqual(json["domain"] as? String, "api.example.com")
        XCTAssertEqual(json["method"] as? String, "POST")
        XCTAssertNil(json["endpoint"])
    }

    // MARK: - Question Encoding

    func testQuestionRequestExists() throws {
        let json = try encode(Question.requestExists)
        XCTAssertEqual(json["type"] as? String, "request_exists")
    }

    func testQuestionRequestCount() throws {
        let json = try encode(Question.requestCount)
        XCTAssertEqual(json["type"] as? String, "request_count")
    }

    func testQuestionResponseStatus() throws {
        let json = try encode(Question.responseStatus)
        XCTAssertEqual(json["type"] as? String, "response_status")
    }

    func testQuestionResponseHeaderValue() throws {
        let json = try encode(Question.responseHeaderValue(name: "Content-Type"))
        XCTAssertEqual(json["type"] as? String, "response_header_value")
        XCTAssertEqual(json["name"] as? String, "Content-Type")
    }

    func testQuestionRequestHeaderValue() throws {
        let json = try encode(Question.requestHeaderValue(name: "Authorization"))
        XCTAssertEqual(json["type"] as? String, "request_header_value")
        XCTAssertEqual(json["name"] as? String, "Authorization")
    }

    func testQuestionResponseHeaderExists() throws {
        let json = try encode(Question.responseHeaderExists(name: "X-Custom"))
        XCTAssertEqual(json["type"] as? String, "response_header_exists")
        XCTAssertEqual(json["name"] as? String, "X-Custom")
    }

    func testQuestionRequestHeaderExists() throws {
        let json = try encode(Question.requestHeaderExists(name: "Authorization"))
        XCTAssertEqual(json["type"] as? String, "request_header_exists")
    }

    func testQuestionResponseBodyKeyPath() throws {
        let json = try encode(Question.responseBodyKeyPath(path: "data.users[0].name"))
        XCTAssertEqual(json["type"] as? String, "response_body_key_path")
        XCTAssertEqual(json["path"] as? String, "data.users[0].name")
    }

    func testQuestionCountAtKeyPath() throws {
        let json = try encode(Question.countAtKeyPath(path: "items"))
        XCTAssertEqual(json["type"] as? String, "count_at_key_path")
        XCTAssertEqual(json["path"] as? String, "items")
    }

    func testQuestionResponseBodyContains() throws {
        let json = try encode(Question.responseBodyContains(substring: "error"))
        XCTAssertEqual(json["type"] as? String, "response_body_contains")
        XCTAssertEqual(json["substring"] as? String, "error")
    }

    func testQuestionResponseBodyRaw() throws {
        let json = try encode(Question.responseBodyRaw)
        XCTAssertEqual(json["type"] as? String, "response_body_raw")
    }

    func testQuestionResponseContentType() throws {
        let json = try encode(Question.responseContentType)
        XCTAssertEqual(json["type"] as? String, "response_content_type")
    }

    func testQuestionRequestBodyKeyPath() throws {
        let json = try encode(Question.requestBodyKeyPath(path: "username"))
        XCTAssertEqual(json["type"] as? String, "request_body_key_path")
        XCTAssertEqual(json["path"] as? String, "username")
    }

    func testQuestionRequestBodyRaw() throws {
        let json = try encode(Question.requestBodyRaw)
        XCTAssertEqual(json["type"] as? String, "request_body_raw")
    }

    func testQuestionRequestContentType() throws {
        let json = try encode(Question.requestContentType)
        XCTAssertEqual(json["type"] as? String, "request_content_type")
    }

    func testQuestionQueryParamValue() throws {
        let json = try encode(Question.queryParamValue(name: "page"))
        XCTAssertEqual(json["type"] as? String, "query_param_value")
        XCTAssertEqual(json["name"] as? String, "page")
    }

    func testQuestionQueryParamExists() throws {
        let json = try encode(Question.queryParamExists(name: "sort"))
        XCTAssertEqual(json["type"] as? String, "query_param_exists")
        XCTAssertEqual(json["name"] as? String, "sort")
    }

    func testQuestionResponseTimeMsNoAggregate() throws {
        let json = try encode(Question.responseTimeMs())
        XCTAssertEqual(json["type"] as? String, "response_time_ms")
        XCTAssertNil(json["aggregate"])
    }

    func testQuestionResponseTimeMsWithAggregate() throws {
        let json = try encode(Question.responseTimeMs(aggregate: .avg))
        XCTAssertEqual(json["type"] as? String, "response_time_ms")
        XCTAssertEqual(json["aggregate"] as? String, "avg")
    }

    func testQuestionResponseBodySizeBytes() throws {
        let json = try encode(Question.responseBodySizeBytes(aggregate: .max))
        XCTAssertEqual(json["type"] as? String, "response_body_size_bytes")
        XCTAssertEqual(json["aggregate"] as? String, "max")
    }

    func testQuestionRequestBodySizeBytes() throws {
        let json = try encode(Question.requestBodySizeBytes(aggregate: .sum))
        XCTAssertEqual(json["type"] as? String, "request_body_size_bytes")
        XCTAssertEqual(json["aggregate"] as? String, "sum")
    }

    // MARK: - SpanQuestion Encoding

    func testSpanQuestionTotalRequestCount() throws {
        let json = try encode(SpanQuestion.totalRequestCount)
        XCTAssertEqual(json["type"] as? String, "total_request_count")
    }

    func testSpanQuestionDomainsContacted() throws {
        let json = try encode(SpanQuestion.domainsContacted)
        XCTAssertEqual(json["type"] as? String, "domains_contacted")
    }

    func testSpanQuestionEndpointsContacted() throws {
        let json = try encode(SpanQuestion.endpointsContacted)
        XCTAssertEqual(json["type"] as? String, "endpoints_contacted")
    }

    func testSpanQuestionMethodsUsed() throws {
        let json = try encode(SpanQuestion.methodsUsed)
        XCTAssertEqual(json["type"] as? String, "methods_used")
    }

    func testSpanQuestionUniqueExchanges() throws {
        let json = try encode(SpanQuestion.uniqueExchanges)
        XCTAssertEqual(json["type"] as? String, "unique_exchanges")
    }

    func testSpanQuestionTotalDurationMs() throws {
        let json = try encode(SpanQuestion.totalDurationMs)
        XCTAssertEqual(json["type"] as? String, "total_duration_ms")
    }

    func testSpanQuestionSpanStartTime() throws {
        let json = try encode(SpanQuestion.spanStartTime)
        XCTAssertEqual(json["type"] as? String, "span_start_time")
    }

    func testSpanQuestionSpanEndTime() throws {
        let json = try encode(SpanQuestion.spanEndTime)
        XCTAssertEqual(json["type"] as? String, "span_end_time")
    }

    func testSpanQuestionAvgResponseTimeMs() throws {
        let json = try encode(SpanQuestion.avgResponseTimeMs)
        XCTAssertEqual(json["type"] as? String, "avg_response_time_ms")
    }

    func testSpanQuestionSlowestRequest() throws {
        let json = try encode(SpanQuestion.slowestRequest)
        XCTAssertEqual(json["type"] as? String, "slowest_request")
    }

    func testSpanQuestionErrorCount() throws {
        let json = try encode(SpanQuestion.errorCount)
        XCTAssertEqual(json["type"] as? String, "error_count")
    }

    func testSpanQuestionErrorRate() throws {
        let json = try encode(SpanQuestion.errorRate)
        XCTAssertEqual(json["type"] as? String, "error_rate")
    }

    func testSpanQuestionStatusCodeSummary() throws {
        let json = try encode(SpanQuestion.statusCodeSummary)
        XCTAssertEqual(json["type"] as? String, "status_code_summary")
    }

    // MARK: - Full Request Encoding

    func testQueryRequestEncoding() throws {
        let request = QueryRequest(
            scope: .span("login"),
            target: QueryTarget(domain: "api.example.com", endpoint: "/auth", method: .POST),
            questions: [.responseStatus, .responseHeaderValue(name: "Content-Type")]
        )
        let json = try encode(request)

        XCTAssertEqual(json["scope"] as? String, "login")

        let target = json["target"] as! [String: Any]
        XCTAssertEqual(target["domain"] as? String, "api.example.com")
        XCTAssertEqual(target["endpoint"] as? String, "/auth")
        XCTAssertEqual(target["method"] as? String, "POST")

        let questions = json["questions"] as! [[String: Any]]
        XCTAssertEqual(questions.count, 2)
        XCTAssertEqual(questions[0]["type"] as? String, "response_status")
        XCTAssertEqual(questions[1]["type"] as? String, "response_header_value")
        XCTAssertEqual(questions[1]["name"] as? String, "Content-Type")
    }

    func testSpanQueryRequestEncoding() throws {
        let request = SpanQueryRequest(
            scope: .span("login"),
            filter: SpanFilter(domain: "api.example.com"),
            questions: [.totalRequestCount, .domainsContacted]
        )
        let json = try encode(request)

        XCTAssertEqual(json["scope"] as? String, "login")

        let filter = json["filter"] as! [String: Any]
        XCTAssertEqual(filter["domain"] as? String, "api.example.com")

        let questions = json["questions"] as! [[String: Any]]
        XCTAssertEqual(questions.count, 2)
        XCTAssertEqual(questions[0]["type"] as? String, "total_request_count")
        XCTAssertEqual(questions[1]["type"] as? String, "domains_contacted")
    }

    func testSpanQueryRequestNoFilter() throws {
        let request = SpanQueryRequest(
            scope: .all,
            filter: nil,
            questions: [.errorCount]
        )
        let json = try encode(request)
        XCTAssertEqual(json["scope"] as? String, "all")
        // filter should be null or absent — not a real filter object
        XCTAssertNil(json["filter"] as? [String: Any])
    }
}
