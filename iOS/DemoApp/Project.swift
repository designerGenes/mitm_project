import ProjectDescription

let project = Project(
    name: "DemoApp",
    targets: [
        // MARK: - WatcherClient Framework
        // Reuses existing library sources from iOS/Sources/WatcherClient/
        .target(
            name: "WatcherClient",
            destinations: .iOS,
            product: .framework,
            bundleId: "com.watcher.WatcherClient",
            deploymentTargets: .iOS("16.0"),
            infoPlist: .default,
            sources: ["../Sources/WatcherClient/**"]
        ),

        // MARK: - Demo Host App
        // Minimal UIKit app — just enough to host XCUITests
        .target(
            name: "DemoApp",
            destinations: .iOS,
            product: .app,
            bundleId: "com.watcher.DemoApp",
            deploymentTargets: .iOS("16.0"),
            infoPlist: .extendingDefault(with: [
                "UILaunchScreen": .dictionary([:]),
            ]),
            sources: ["Sources/DemoApp/**"],
            dependencies: [
                .target(name: "WatcherClient"),
            ]
        ),

        // MARK: - XCUITests
        // 18 tests demonstrating WatcherClient queries against the Python daemon
        .target(
            name: "WatcherUITests",
            destinations: .iOS,
            product: .uiTests,
            bundleId: "com.watcher.WatcherUITests",
            deploymentTargets: .iOS("16.0"),
            infoPlist: .extendingDefault(with: [
                "NSAppTransportSecurity": .dictionary([
                    "NSAllowsArbitraryLoads": .boolean(true),
                ]),
            ]),
            sources: ["Tests/WatcherUITests/**"],
            dependencies: [
                .target(name: "DemoApp"),
                .target(name: "WatcherClient"),
            ]
        ),
    ]
)
