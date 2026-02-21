import Foundation

/// Static facade for the Watcher client — the primary API for iOS UI tests.
///
/// Usage:
/// ```swift
/// // Optional: configure a custom port (default 9090)
/// Watcher.configure(port: 9091)
///
/// // Start a span
/// try Watcher.startSpan(named: "login")
///
/// // ... UI interactions that trigger network calls ...
///
/// // Stop the span
/// try Watcher.stopSpan()
///
/// // Query a specific exchange
/// let answer = try Watcher.query(
///     scope: .span("login"),
///     target: .init(domain: "api.example.com", endpoint: "/auth", method: .POST),
///     question: .responseStatus
/// )
/// XCTAssertEqual(answer.intValue, 200)
/// ```
public enum Watcher {
    private static var _client = WatcherClient()

    /// The underlying client instance.
    public static var client: WatcherClient { _client }

    /// Configure the connection to the Watcher daemon.
    /// Call this in your test setUp if not using the default port.
    public static func configure(
        port: Int = 9090,
        host: String = "localhost",
        session: URLSession = .shared,
        timeout: TimeInterval = 10
    ) {
        _client = WatcherClient(port: port, host: host, session: session, timeout: timeout)
    }

    // MARK: - Span Control

    /// Start a named span. Auto-closes any previously active span.
    public static func startSpan(named name: String) throws {
        try _client.startSpan(named: name)
    }

    /// Stop the current span.
    public static func stopSpan() throws {
        try _client.stopSpan()
    }

    // MARK: - Exchange-Level Query

    /// Send an exchange-level query with multiple questions.
    public static func query(
        scope: Scope,
        target: QueryTarget = .init(),
        questions: [Question]
    ) throws -> QueryResponse {
        try _client.query(scope: scope, target: target, questions: questions)
    }

    /// Convenience: single question, returns just the answer.
    public static func query(
        scope: Scope,
        target: QueryTarget = .init(),
        question: Question
    ) throws -> Answer {
        try _client.query(scope: scope, target: target, question: question)
    }

    // MARK: - Span-Level Query

    /// Send a span-level meta query with multiple questions.
    public static func spanQuery(
        scope: Scope,
        filter: SpanFilter? = nil,
        questions: [SpanQuestion]
    ) throws -> SpanQueryResponse {
        try _client.spanQuery(scope: scope, filter: filter, questions: questions)
    }

    /// Convenience: single span question, returns just the answer.
    public static func spanQuery(
        scope: Scope,
        filter: SpanFilter? = nil,
        question: SpanQuestion
    ) throws -> Answer {
        try _client.spanQuery(scope: scope, filter: filter, question: question)
    }

    // MARK: - Admin

    /// Clear all captured data and spans.
    public static func reset() throws {
        try _client.reset()
    }

    /// Get daemon status.
    public static func status() throws -> StatusResponse {
        try _client.status()
    }

    /// Check if the daemon is alive.
    public static func health() throws -> Bool {
        try _client.health()
    }
}
