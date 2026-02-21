import Foundation

/// Errors thrown by the Wire client.
public enum WireError: Error, LocalizedError {
    /// Could not connect to the Wire daemon.
    case connectionFailed(underlying: Error)
    /// Server returned a non-2xx HTTP status.
    case unexpectedStatus(Int, body: String?)
    /// Failed to decode the server response.
    case decodingFailed(underlying: Error)
    /// The request timed out.
    case timeout

    public var errorDescription: String? {
        switch self {
        case .connectionFailed(let error):
            return "Failed to connect to Wire daemon: \(error.localizedDescription)"
        case .unexpectedStatus(let code, let body):
            return "Unexpected HTTP status \(code)\(body.map { ": \($0)" } ?? "")"
        case .decodingFailed(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .timeout:
            return "Request timed out"
        }
    }
}
