import Foundation

// MARK: - QueryValue

/// A dynamically-typed JSON value returned by the Watcher daemon.
public enum QueryValue: Decodable, Equatable, CustomStringConvertible {
    case null
    case bool(Bool)
    case int(Int)
    case double(Double)
    case string(String)
    case array([QueryValue])
    case object([String: QueryValue])

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if container.decodeNil() {
            self = .null
            return
        }
        // Bool must be checked before Int because Swift's JSONDecoder
        // will happily decode a Bool as Int (true→1, false→0).
        if let value = try? container.decode(Bool.self) {
            self = .bool(value)
            return
        }
        if let value = try? container.decode(Int.self) {
            self = .int(value)
            return
        }
        if let value = try? container.decode(Double.self) {
            self = .double(value)
            return
        }
        if let value = try? container.decode(String.self) {
            self = .string(value)
            return
        }
        if let value = try? container.decode([QueryValue].self) {
            self = .array(value)
            return
        }
        if let value = try? container.decode([String: QueryValue].self) {
            self = .object(value)
            return
        }
        throw DecodingError.typeMismatch(
            QueryValue.self,
            .init(codingPath: decoder.codingPath, debugDescription: "Unsupported JSON value type")
        )
    }

    // MARK: Convenience Accessors

    public var intValue: Int? {
        if case .int(let v) = self { return v }
        if case .double(let v) = self { return Int(exactly: v) }
        return nil
    }

    public var doubleValue: Double? {
        if case .double(let v) = self { return v }
        if case .int(let v) = self { return Double(v) }
        return nil
    }

    public var stringValue: String? {
        if case .string(let v) = self { return v }
        return nil
    }

    public var boolValue: Bool? {
        if case .bool(let v) = self { return v }
        return nil
    }

    public var arrayValue: [QueryValue]? {
        if case .array(let v) = self { return v }
        return nil
    }

    public var objectValue: [String: QueryValue]? {
        if case .object(let v) = self { return v }
        return nil
    }

    public var isNull: Bool {
        if case .null = self { return true }
        return false
    }

    public var description: String {
        switch self {
        case .null: return "null"
        case .bool(let v): return String(v)
        case .int(let v): return String(v)
        case .double(let v): return String(v)
        case .string(let v): return "\"\(v)\""
        case .array(let v): return "[\(v.map(\.description).joined(separator: ", "))]"
        case .object(let v):
            let pairs = v.map { "\"\($0)\": \($1)" }.joined(separator: ", ")
            return "{\(pairs)}"
        }
    }
}

// MARK: - Answer

/// A single answer from the Watcher daemon.
public struct Answer: Decodable {
    public let found: Bool
    public let value: QueryValue?
    public let reason: String?

    public init(found: Bool, value: QueryValue?, reason: String?) {
        self.found = found
        self.value = value
        self.reason = reason
    }

    // Typed convenience accessors
    public var intValue: Int? { value?.intValue }
    public var doubleValue: Double? { value?.doubleValue }
    public var stringValue: String? { value?.stringValue }
    public var boolValue: Bool? { value?.boolValue }
    public var arrayValue: [QueryValue]? { value?.arrayValue }
    public var objectValue: [String: QueryValue]? { value?.objectValue }
}

// MARK: - QueryResponse

/// Response from `POST /query` (exchange-level).
public struct QueryResponse: Decodable {
    public let found: Bool
    public let matchedCount: Int?
    public let occurrenceUsed: Int?
    public let reason: String?
    public let answers: [Answer]

    private enum CodingKeys: String, CodingKey {
        case found
        case matchedCount = "matched_count"
        case occurrenceUsed = "occurrence_used"
        case reason
        case answers
    }
}

// MARK: - SpanQueryResponse

/// Response from `POST /span/query` (span-level).
public struct SpanQueryResponse: Decodable {
    public let found: Bool
    public let reason: String?
    public let answers: [Answer]
}

// MARK: - StatusResponse

/// Response from `GET /status`.
public struct StatusResponse: Decodable {
    public let config: StatusConfig?
    public let currentSpan: String?
    public let exchangeCount: Int
    public let spans: [String: SpanInfo]

    private enum CodingKeys: String, CodingKey {
        case config
        case currentSpan = "current_span"
        case exchangeCount = "exchange_count"
        case spans
    }
}

public struct StatusConfig: Decodable {
    public let apiPort: Int?
    public let proxyPort: Int?
    public let outputDir: String?
    public let verbose: Bool?

    private enum CodingKeys: String, CodingKey {
        case apiPort = "api_port"
        case proxyPort = "proxy_port"
        case outputDir = "output_dir"
        case verbose
    }
}

public struct SpanInfo: Decodable {
    public let startedAt: String?
    public let stoppedAt: String?

    private enum CodingKeys: String, CodingKey {
        case startedAt = "started_at"
        case stoppedAt = "stopped_at"
    }
}

// MARK: - Simple Status (for admin endpoints)

struct SimpleResponse: Decodable {
    let status: String
}
