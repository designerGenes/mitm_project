import Foundation

// MARK: - Scope

/// Selects which exchanges to query.
public enum Scope: Encodable, Equatable {
    /// Only exchanges tagged to the named span.
    case span(String)
    /// Only exchanges with no span.
    case unspanned
    /// All exchanges regardless of span.
    case all

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .span(let name): try container.encode(name)
        case .unspanned: try container.encode("unspanned")
        case .all: try container.encode("all")
        }
    }
}

// MARK: - HTTPMethod

/// HTTP methods for target filtering.
public enum HTTPMethod: String, Codable, CaseIterable {
    case GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
}

// MARK: - QueryTarget

/// Filters exchanges by domain, endpoint, method, and selects by occurrence.
public struct QueryTarget: Encodable, Equatable {
    public var domain: String?
    public var endpoint: String?
    public var method: HTTPMethod?
    public var occurrence: Int?

    public init(
        domain: String? = nil,
        endpoint: String? = nil,
        method: HTTPMethod? = nil,
        occurrence: Int? = nil
    ) {
        self.domain = domain
        self.endpoint = endpoint
        self.method = method
        self.occurrence = occurrence
    }
}

// MARK: - SpanFilter

/// Optional filter for span-level queries.
public struct SpanFilter: Encodable, Equatable {
    public var domain: String?
    public var endpoint: String?
    public var method: HTTPMethod?

    public init(
        domain: String? = nil,
        endpoint: String? = nil,
        method: HTTPMethod? = nil
    ) {
        self.domain = domain
        self.endpoint = endpoint
        self.method = method
    }
}

// MARK: - Aggregate

/// Aggregate modifier for metric questions.
public enum Aggregate: String, Encodable {
    case avg, min, max, sum
}

// MARK: - Internal Request Bodies

struct QueryRequest: Encodable {
    let scope: Scope
    let target: QueryTarget
    let questions: [Question]
}

struct SpanQueryRequest: Encodable {
    let scope: Scope
    let filter: SpanFilter?
    let questions: [SpanQuestion]
}

struct SpanStartRequest: Encodable {
    let name: String
}
