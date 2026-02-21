import XCTest
@testable import WireKit

/// Verify that response models decode correctly from JSON matching the Python API.
final class DecodingTests: XCTestCase {
    let decoder = JSONDecoder()

    private func decode<T: Decodable>(_ type: T.Type, from json: String) throws -> T {
        let data = json.data(using: .utf8)!
        return try decoder.decode(type, from: data)
    }

    // MARK: - QueryValue

    func testQueryValueInt() throws {
        let val = try decode(QueryValue.self, from: "42")
        XCTAssertEqual(val, .int(42))
        XCTAssertEqual(val.intValue, 42)
        XCTAssertEqual(val.doubleValue, 42.0)
    }

    func testQueryValueDouble() throws {
        let val = try decode(QueryValue.self, from: "3.14")
        XCTAssertEqual(val, .double(3.14))
        XCTAssertEqual(val.doubleValue, 3.14)
    }

    func testQueryValueString() throws {
        let val = try decode(QueryValue.self, from: "\"hello\"")
        XCTAssertEqual(val, .string("hello"))
        XCTAssertEqual(val.stringValue, "hello")
    }

    func testQueryValueBoolTrue() throws {
        let val = try decode(QueryValue.self, from: "true")
        XCTAssertEqual(val, .bool(true))
        XCTAssertEqual(val.boolValue, true)
    }

    func testQueryValueBoolFalse() throws {
        let val = try decode(QueryValue.self, from: "false")
        XCTAssertEqual(val, .bool(false))
        XCTAssertEqual(val.boolValue, false)
    }

    func testQueryValueNull() throws {
        let val = try decode(QueryValue.self, from: "null")
        XCTAssertEqual(val, .null)
        XCTAssertTrue(val.isNull)
    }

    func testQueryValueArray() throws {
        let val = try decode(QueryValue.self, from: "[1, \"two\", true]")
        XCTAssertEqual(val.arrayValue?.count, 3)
        XCTAssertEqual(val.arrayValue?[0], .int(1))
        XCTAssertEqual(val.arrayValue?[1], .string("two"))
        XCTAssertEqual(val.arrayValue?[2], .bool(true))
    }

    func testQueryValueObject() throws {
        let val = try decode(QueryValue.self, from: "{\"name\": \"Alice\", \"age\": 30}")
        let obj = val.objectValue!
        XCTAssertEqual(obj["name"], .string("Alice"))
        XCTAssertEqual(obj["age"], .int(30))
    }

    func testQueryValueNested() throws {
        let json = "{\"users\": [{\"name\": \"Alice\"}, {\"name\": \"Bob\"}]}"
        let val = try decode(QueryValue.self, from: json)
        let users = val.objectValue!["users"]!.arrayValue!
        XCTAssertEqual(users.count, 2)
        XCTAssertEqual(users[0].objectValue!["name"], .string("Alice"))
    }

    func testQueryValueDescription() throws {
        XCTAssertEqual(QueryValue.null.description, "null")
        XCTAssertEqual(QueryValue.int(42).description, "42")
        XCTAssertEqual(QueryValue.bool(true).description, "true")
        XCTAssertEqual(QueryValue.string("hi").description, "\"hi\"")
    }

    func testQueryValueConvenienceNilCases() throws {
        let val = QueryValue.string("hello")
        XCTAssertNil(val.intValue)
        XCTAssertNil(val.boolValue)
        XCTAssertNil(val.arrayValue)
        XCTAssertNil(val.objectValue)
        XCTAssertFalse(val.isNull)
    }

    // MARK: - Answer

    func testAnswerFound() throws {
        let json = "{\"found\": true, \"value\": 200}"
        let answer = try decode(Answer.self, from: json)
        XCTAssertTrue(answer.found)
        XCTAssertEqual(answer.intValue, 200)
        XCTAssertNil(answer.reason)
    }

    func testAnswerNotFound() throws {
        let json = "{\"found\": false, \"value\": null, \"reason\": \"header_not_found\"}"
        let answer = try decode(Answer.self, from: json)
        XCTAssertFalse(answer.found)
        XCTAssertTrue(answer.value?.isNull ?? true)
        XCTAssertEqual(answer.reason, "header_not_found")
    }

    func testAnswerStringValue() throws {
        let json = "{\"found\": true, \"value\": \"application/json\"}"
        let answer = try decode(Answer.self, from: json)
        XCTAssertEqual(answer.stringValue, "application/json")
    }

    func testAnswerBoolValue() throws {
        let json = "{\"found\": true, \"value\": true}"
        let answer = try decode(Answer.self, from: json)
        XCTAssertEqual(answer.boolValue, true)
    }

    func testAnswerArrayValue() throws {
        let json = "{\"found\": true, \"value\": [\"api.example.com\", \"cdn.example.com\"]}"
        let answer = try decode(Answer.self, from: json)
        XCTAssertEqual(answer.arrayValue?.count, 2)
    }

    // MARK: - QueryResponse

    func testQueryResponseFound() throws {
        let json = """
        {
            "found": true,
            "matched_count": 3,
            "occurrence_used": 0,
            "answers": [
                {"found": true, "value": 200},
                {"found": true, "value": "application/json"}
            ]
        }
        """
        let resp = try decode(QueryResponse.self, from: json)
        XCTAssertTrue(resp.found)
        XCTAssertEqual(resp.matchedCount, 3)
        XCTAssertEqual(resp.occurrenceUsed, 0)
        XCTAssertNil(resp.reason)
        XCTAssertEqual(resp.answers.count, 2)
        XCTAssertEqual(resp.answers[0].intValue, 200)
        XCTAssertEqual(resp.answers[1].stringValue, "application/json")
    }

    func testQueryResponseNotFound() throws {
        let json = """
        {
            "found": false,
            "matched_count": 0,
            "occurrence_used": null,
            "reason": "no_matching_exchange",
            "answers": []
        }
        """
        let resp = try decode(QueryResponse.self, from: json)
        XCTAssertFalse(resp.found)
        XCTAssertEqual(resp.reason, "no_matching_exchange")
        XCTAssertTrue(resp.answers.isEmpty)
    }

    func testQueryResponseMixedAnswers() throws {
        let json = """
        {
            "found": true,
            "matched_count": 1,
            "occurrence_used": 0,
            "answers": [
                {"found": true, "value": 200},
                {"found": false, "value": null, "reason": "header_not_found"}
            ]
        }
        """
        let resp = try decode(QueryResponse.self, from: json)
        XCTAssertTrue(resp.found)
        XCTAssertTrue(resp.answers[0].found)
        XCTAssertFalse(resp.answers[1].found)
        XCTAssertEqual(resp.answers[1].reason, "header_not_found")
    }

    // MARK: - SpanQueryResponse

    func testSpanQueryResponseFound() throws {
        let json = """
        {
            "found": true,
            "answers": [
                {"found": true, "value": 14},
                {"found": true, "value": ["api.example.com", "cdn.example.com"]}
            ]
        }
        """
        let resp = try decode(SpanQueryResponse.self, from: json)
        XCTAssertTrue(resp.found)
        XCTAssertEqual(resp.answers.count, 2)
        XCTAssertEqual(resp.answers[0].intValue, 14)
        XCTAssertEqual(resp.answers[1].arrayValue?.count, 2)
    }

    func testSpanQueryResponseSpanNotFound() throws {
        let json = """
        {
            "found": false,
            "reason": "span_not_found",
            "answers": []
        }
        """
        let resp = try decode(SpanQueryResponse.self, from: json)
        XCTAssertFalse(resp.found)
        XCTAssertEqual(resp.reason, "span_not_found")
    }

    // MARK: - StatusResponse

    func testStatusResponse() throws {
        let json = """
        {
            "config": {
                "api_port": 9090,
                "proxy_port": 8080,
                "output_dir": "/tmp/traffic",
                "verbose": false
            },
            "current_span": "login",
            "exchange_count": 5,
            "spans": {
                "login": {"started_at": "2025-01-01T00:00:00", "stopped_at": null}
            }
        }
        """
        let resp = try decode(StatusResponse.self, from: json)
        XCTAssertEqual(resp.config?.apiPort, 9090)
        XCTAssertEqual(resp.config?.proxyPort, 8080)
        XCTAssertEqual(resp.config?.outputDir, "/tmp/traffic")
        XCTAssertEqual(resp.config?.verbose, false)
        XCTAssertEqual(resp.currentSpan, "login")
        XCTAssertEqual(resp.exchangeCount, 5)
        XCTAssertEqual(resp.spans.count, 1)
        XCTAssertNotNil(resp.spans["login"]?.startedAt)
        XCTAssertNil(resp.spans["login"]?.stoppedAt)
    }

    func testStatusResponseEmpty() throws {
        let json = """
        {
            "config": {},
            "current_span": null,
            "exchange_count": 0,
            "spans": {}
        }
        """
        let resp = try decode(StatusResponse.self, from: json)
        XCTAssertNil(resp.currentSpan)
        XCTAssertEqual(resp.exchangeCount, 0)
        XCTAssertTrue(resp.spans.isEmpty)
    }
}
