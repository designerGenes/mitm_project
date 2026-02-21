import Foundation

// MARK: - Exchange-Level Questions

/// A question to ask about a single captured HTTP exchange.
public enum Question: Encodable {
    // Existence & Counting (skip occurrence, operate on filtered list)
    case requestExists
    case requestCount

    // Status
    case responseStatus

    // Headers
    case responseHeaderValue(name: String)
    case requestHeaderValue(name: String)
    case responseHeaderExists(name: String)
    case requestHeaderExists(name: String)

    // Response Body
    case responseBodyKeyPath(path: String)
    case countAtKeyPath(path: String)
    case responseBodyContains(substring: String)
    case responseBodyRaw
    case responseContentType

    // Request Body
    case requestBodyKeyPath(path: String)
    case requestBodyRaw
    case requestContentType

    // Query Params
    case queryParamValue(name: String)
    case queryParamExists(name: String)

    // Metrics (optional aggregate skips occurrence, operates on all matches)
    case responseTimeMs(aggregate: Aggregate? = nil)
    case responseBodySizeBytes(aggregate: Aggregate? = nil)
    case requestBodySizeBytes(aggregate: Aggregate? = nil)

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)

        switch self {
        case .requestExists:
            try container.encode("request_exists", forKey: .type)
        case .requestCount:
            try container.encode("request_count", forKey: .type)
        case .responseStatus:
            try container.encode("response_status", forKey: .type)
        case .responseHeaderValue(let name):
            try container.encode("response_header_value", forKey: .type)
            try container.encode(name, forKey: .name)
        case .requestHeaderValue(let name):
            try container.encode("request_header_value", forKey: .type)
            try container.encode(name, forKey: .name)
        case .responseHeaderExists(let name):
            try container.encode("response_header_exists", forKey: .type)
            try container.encode(name, forKey: .name)
        case .requestHeaderExists(let name):
            try container.encode("request_header_exists", forKey: .type)
            try container.encode(name, forKey: .name)
        case .responseBodyKeyPath(let path):
            try container.encode("response_body_key_path", forKey: .type)
            try container.encode(path, forKey: .path)
        case .countAtKeyPath(let path):
            try container.encode("count_at_key_path", forKey: .type)
            try container.encode(path, forKey: .path)
        case .responseBodyContains(let substring):
            try container.encode("response_body_contains", forKey: .type)
            try container.encode(substring, forKey: .substring)
        case .responseBodyRaw:
            try container.encode("response_body_raw", forKey: .type)
        case .responseContentType:
            try container.encode("response_content_type", forKey: .type)
        case .requestBodyKeyPath(let path):
            try container.encode("request_body_key_path", forKey: .type)
            try container.encode(path, forKey: .path)
        case .requestBodyRaw:
            try container.encode("request_body_raw", forKey: .type)
        case .requestContentType:
            try container.encode("request_content_type", forKey: .type)
        case .queryParamValue(let name):
            try container.encode("query_param_value", forKey: .type)
            try container.encode(name, forKey: .name)
        case .queryParamExists(let name):
            try container.encode("query_param_exists", forKey: .type)
            try container.encode(name, forKey: .name)
        case .responseTimeMs(let aggregate):
            try container.encode("response_time_ms", forKey: .type)
            try container.encodeIfPresent(aggregate, forKey: .aggregate)
        case .responseBodySizeBytes(let aggregate):
            try container.encode("response_body_size_bytes", forKey: .type)
            try container.encodeIfPresent(aggregate, forKey: .aggregate)
        case .requestBodySizeBytes(let aggregate):
            try container.encode("request_body_size_bytes", forKey: .type)
            try container.encodeIfPresent(aggregate, forKey: .aggregate)
        }
    }

    private enum CodingKeys: String, CodingKey {
        case type, name, path, substring, aggregate
    }
}

// MARK: - Span-Level Questions

/// A meta question to ask about an entire span of captured traffic.
public enum SpanQuestion: Encodable {
    // Inventory
    case totalRequestCount
    case domainsContacted
    case endpointsContacted
    case methodsUsed
    case uniqueExchanges

    // Timing
    case totalDurationMs
    case spanStartTime
    case spanEndTime

    // Aggregates
    case avgResponseTimeMs
    case slowestRequest
    case errorCount
    case errorRate
    case statusCodeSummary

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)

        switch self {
        case .totalRequestCount:
            try container.encode("total_request_count", forKey: .type)
        case .domainsContacted:
            try container.encode("domains_contacted", forKey: .type)
        case .endpointsContacted:
            try container.encode("endpoints_contacted", forKey: .type)
        case .methodsUsed:
            try container.encode("methods_used", forKey: .type)
        case .uniqueExchanges:
            try container.encode("unique_exchanges", forKey: .type)
        case .totalDurationMs:
            try container.encode("total_duration_ms", forKey: .type)
        case .spanStartTime:
            try container.encode("span_start_time", forKey: .type)
        case .spanEndTime:
            try container.encode("span_end_time", forKey: .type)
        case .avgResponseTimeMs:
            try container.encode("avg_response_time_ms", forKey: .type)
        case .slowestRequest:
            try container.encode("slowest_request", forKey: .type)
        case .errorCount:
            try container.encode("error_count", forKey: .type)
        case .errorRate:
            try container.encode("error_rate", forKey: .type)
        case .statusCodeSummary:
            try container.encode("status_code_summary", forKey: .type)
        }
    }

    private enum CodingKeys: String, CodingKey {
        case type
    }
}
