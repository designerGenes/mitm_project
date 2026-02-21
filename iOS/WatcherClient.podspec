Pod::Spec.new do |s|
  s.name         = 'WatcherClient'
  s.version      = '0.1.0'
  s.summary      = 'Swift client for the Watcher HTTP traffic capture daemon.'
  s.description  = <<-DESC
    WatcherClient provides a Swift API for controlling spans, querying captured
    HTTP traffic, and inspecting exchange data from the Watcher daemon. Designed
    for use in XCUITests to verify network behavior of iOS applications.
  DESC

  s.homepage     = 'https://github.com/example/watcher'
  s.license      = { :type => 'MIT' }
  s.author       = 'Watcher Team'

  s.source       = { :git => 'https://github.com/example/watcher.git', :tag => s.version.to_s }
  s.source_files = 'Sources/WatcherClient/**/*.swift'

  s.ios.deployment_target = '16.0'
  s.swift_version = '5.9'
end
