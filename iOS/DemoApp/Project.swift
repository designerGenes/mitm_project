import ProjectDescription

let project = Project(
    name: "DemoApp",
    targets: [
        // MARK: - WireKit Framework
        // Reuses existing library sources from iOS/Sources/WireKit/
        .target(
            name: "WireKit",
            destinations: .iOS,
            product: .framework,
            bundleId: "com.wire.WireKit",
            deploymentTargets: .iOS("16.0"),
            infoPlist: .default,
            sources: ["../Sources/WireKit/**"]
        ),

        // MARK: - Demo Host App
        // Minimal UIKit app — just enough to host XCUITests
        .target(
            name: "DemoApp",
            destinations: .iOS,
            product: .app,
            bundleId: "com.wire.DemoApp",
            deploymentTargets: .iOS("16.0"),
            infoPlist: .extendingDefault(with: [
                "UILaunchScreen": .dictionary([:]),
            ]),
            sources: ["Sources/DemoApp/**"],
            dependencies: [
                .target(name: "WireKit"),
            ]
        ),

        // MARK: - XCUITests
        // 18 tests demonstrating WireKit queries against the Python daemon
        .target(
            name: "WireUITests",
            destinations: .iOS,
            product: .uiTests,
            bundleId: "com.wire.WireUITests",
            deploymentTargets: .iOS("16.0"),
            infoPlist: .extendingDefault(with: [
                "NSAppTransportSecurity": .dictionary([
                    "NSAllowsArbitraryLoads": .boolean(true),
                ]),
            ]),
            sources: ["Tests/WireUITests/**"],
            dependencies: [
                .target(name: "DemoApp"),
                .target(name: "WireKit"),
            ]
        ),
    ]
)
