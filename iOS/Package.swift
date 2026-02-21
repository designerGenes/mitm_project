// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "WatcherClient",
    platforms: [
        .iOS(.v16),
        .macOS(.v13),
    ],
    products: [
        .library(name: "WatcherClient", targets: ["WatcherClient"]),
    ],
    targets: [
        .target(name: "WatcherClient"),
        .testTarget(name: "WatcherClientTests", dependencies: ["WatcherClient"]),
        .testTarget(name: "IntegrationTests", dependencies: ["WatcherClient"]),
    ]
)
