Pod::Spec.new do |s|
  s.name         = 'WireKit'
  s.version      = '0.1.0'
  s.summary      = 'Swift client for the WIRE HTTP traffic capture engine.'
  s.description  = <<-DESC
    WireKit provides a Swift API for controlling spans, querying captured
    HTTP traffic, and inspecting exchange data from the WIRE daemon (WIREd).
    Designed for use in XCUITests to verify network behavior of iOS applications.
  DESC

  s.homepage     = 'https://github.com/example/wire'
  s.license      = { :type => 'MIT' }
  s.author       = 'WIRE Team'

  s.source       = { :git => 'https://github.com/example/wire.git', :tag => s.version.to_s }
  s.source_files = 'Sources/WireKit/**/*.swift'

  s.ios.deployment_target = '16.0'
  s.swift_version = '5.9'
end
