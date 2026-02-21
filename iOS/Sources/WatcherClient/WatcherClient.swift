import Foundation

#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// Instance-based client for talking to the Watcher daemon over HTTP.
///
/// All methods are synchronous (blocking) — designed for use in XCTest
/// where you interact with the UI, then assert on captured traffic.
public final class WatcherClient: @unchecked Sendable {
    public let baseURL: URL
    public let session: URLSession
    public let timeout: TimeInterval

    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    public init(
        port: Int = 9090,
        host: String = "localhost",
        session: URLSession = .shared,
        timeout: TimeInterval = 10
    ) {
        self.baseURL = URL(string: "http://\(host):\(port)")!
        self.session = session
        self.timeout = timeout
    }

    // MARK: - Span Control

    /// Start a named span. Auto-closes any previously active span.
    public func startSpan(named name: String) throws {
        let _: SimpleResponse = try post("/span/start", body: SpanStartRequest(name: name))
    }

    /// Stop the current span.
    public func stopSpan() throws {
        let _: SimpleResponse = try postNoBody("/span/stop")
    }

    // MARK: - Exchange-Level Query

    /// Send an exchange-level query with multiple questions.
    public func query(
        scope: Scope,
        target: QueryTarget = .init(),
        questions: [Question]
    ) throws -> QueryResponse {
        let body = QueryRequest(scope: scope, target: target, questions: questions)
        return try post("/query", body: body)
    }

    /// Convenience: send a single exchange-level question, return just the answer.
    public func query(
        scope: Scope,
        target: QueryTarget = .init(),
        question: Question
    ) throws -> Answer {
        let response = try query(scope: scope, target: target, questions: [question])
        guard response.found else {
            return Answer(found: false, value: nil, reason: response.reason)
        }
        return response.answers.first ?? Answer(found: false, value: nil, reason: "no_answer")
    }

    // MARK: - Span-Level Query

    /// Send a span-level meta query with multiple questions.
    public func spanQuery(
        scope: Scope,
        filter: SpanFilter? = nil,
        questions: [SpanQuestion]
    ) throws -> SpanQueryResponse {
        let body = SpanQueryRequest(scope: scope, filter: filter, questions: questions)
        return try post("/span/query", body: body)
    }

    /// Convenience: send a single span-level question, return just the answer.
    public func spanQuery(
        scope: Scope,
        filter: SpanFilter? = nil,
        question: SpanQuestion
    ) throws -> Answer {
        let response = try spanQuery(scope: scope, filter: filter, questions: [question])
        guard response.found else {
            return Answer(found: false, value: nil, reason: response.reason)
        }
        return response.answers.first ?? Answer(found: false, value: nil, reason: "no_answer")
    }

    // MARK: - Admin

    /// Clear all captured data and spans.
    public func reset() throws {
        let _: SimpleResponse = try postNoBody("/reset")
    }

    /// Get daemon status.
    public func status() throws -> StatusResponse {
        return try get("/status")
    }

    /// Check if the daemon is alive.
    public func health() throws -> Bool {
        let resp: SimpleResponse = try get("/health")
        return resp.status == "ok"
    }

    // MARK: - HTTP Helpers

    private func get<T: Decodable>(_ path: String) throws -> T {
        var request = makeRequest(path: path)
        request.httpMethod = "GET"
        return try perform(request)
    }

    private func post<T: Decodable, B: Encodable>(_ path: String, body: B) throws -> T {
        var request = makeRequest(path: path)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(body)
        return try perform(request)
    }

    private func postNoBody<T: Decodable>(_ path: String) throws -> T {
        var request = makeRequest(path: path)
        request.httpMethod = "POST"
        return try perform(request)
    }

    private func makeRequest(path: String) -> URLRequest {
        let url = baseURL.appendingPathComponent(path)
        var request = URLRequest(url: url)
        request.timeoutInterval = timeout
        return request
    }

    private func perform<T: Decodable>(_ request: URLRequest) throws -> T {
        let semaphore = DispatchSemaphore(value: 0)
        var result: Result<T, Error>!

        let task = session.dataTask(with: request) { [decoder] data, response, error in
            defer { semaphore.signal() }

            if let error = error {
                let nsError = error as NSError
                if nsError.domain == NSURLErrorDomain &&
                    (nsError.code == NSURLErrorCannotConnectToHost ||
                     nsError.code == NSURLErrorNetworkConnectionLost ||
                     nsError.code == NSURLErrorNotConnectedToInternet) {
                    result = .failure(WatcherError.connectionFailed(underlying: error))
                } else {
                    result = .failure(WatcherError.connectionFailed(underlying: error))
                }
                return
            }

            guard let httpResponse = response as? HTTPURLResponse else {
                result = .failure(WatcherError.unexpectedStatus(-1, body: nil))
                return
            }

            guard let data = data else {
                result = .failure(WatcherError.unexpectedStatus(httpResponse.statusCode, body: nil))
                return
            }

            guard (200...299).contains(httpResponse.statusCode) else {
                let body = String(data: data, encoding: .utf8)
                result = .failure(WatcherError.unexpectedStatus(httpResponse.statusCode, body: body))
                return
            }

            do {
                let decoded = try decoder.decode(T.self, from: data)
                result = .success(decoded)
            } catch {
                result = .failure(WatcherError.decodingFailed(underlying: error))
            }
        }
        task.resume()

        let waitResult = semaphore.wait(timeout: .now() + timeout)
        if waitResult == .timedOut {
            task.cancel()
            throw WatcherError.timeout
        }

        return try result.get()
    }
}
