import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// A URLProtocol subclass that intercepts all requests for testing.
final class MockURLProtocol: URLProtocol {
    /// Handler called for each intercepted request.
    /// The URLRequest passed to the handler has httpBody restored from httpBodyStream
    /// when necessary (URLSession strips httpBody in URLProtocol).
    nonisolated(unsafe) static var requestHandler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        guard let handler = MockURLProtocol.requestHandler else {
            client?.urlProtocolDidFinishLoading(self)
            return
        }

        // URLSession strips httpBody when passing to URLProtocol.
        // Reconstruct it from httpBodyStream if needed.
        var req = request
        if req.httpBody == nil, let stream = request.httpBodyStream {
            stream.open()
            var data = Data()
            let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: 4096)
            defer { buffer.deallocate() }
            while stream.hasBytesAvailable {
                let read = stream.read(buffer, maxLength: 4096)
                guard read > 0 else { break }
                data.append(buffer, count: read)
            }
            stream.close()
            req.httpBody = data
        }

        do {
            let (response, data) = try handler(req)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}

    /// Create a URLSession configured to use MockURLProtocol.
    static func session() -> URLSession {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [MockURLProtocol.self]
        return URLSession(configuration: config)
    }
}
