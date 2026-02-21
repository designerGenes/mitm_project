// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "WireKit",
    platforms: [
        .iOS(.v16),
        .macOS(.v13),
    ],
    products: [
        .library(name: "WireKit", targets: ["WireKit"]),
    ],
    targets: [
        .target(name: "WireKit"),
        .testTarget(name: "WireKitTests", dependencies: ["WireKit"]),
        .testTarget(name: "IntegrationTests", dependencies: ["WireKit"]),
    ]
)
