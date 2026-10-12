# 006: Plugin manager replaces Ignite settings with localhost

Status: the affected class is unchanged in `5.8-RELEASE-84`. The supplied launcher works in a live startup test.
Evidence: [runtime and source identifiers](evidence.json).

## Source report

The user supplied `bugreports/old/tak-pluginmanager-localhost-20260913.zip` and its text report.
The ZIP contains a handoff, bytecode, startup and restart evidence, and `workaround/PluginLauncher.java` with a build script.
All 13 checksums in the extracted bundle passed.
The original runtime was TAK `5.8-RELEASE-69` on ARM64 with Ignite `2.18.0`.
Its unmodified plugin process waited on discovery at `127.0.0.1` in its own network namespace.
The workaround joined the remote messaging service and exposed the three plugin APIs.
The old report includes plugin, config, API, and retention restart observations. It does not establish messaging restart recovery.

## Current binary check

`tak.server.plugins.service.PluginService.main()` supplies `127.0.0.1` and disables multicast when rebuilding the Ignite configuration.
This replaces the XML binding and discovery settings before Ignite starts.
The `PluginService.class` checksum is identical in the supplied 5.8.69 report and the tested 5.8.84 JAR.
Direct `javap` inspection confirms the same override and private static `ignite` field.
This is stronger than assuming compatibility from the older report, but it is not a fresh live failure reproduction of the original launcher.

## Workaround and verification

The launcher builds the plugin profile from the loaded XML, starts the Ignite client, and assigns that client to `PluginService.ignite` through reflection.
It then starts the ordinary Spring application and creates the private readiness marker.
It changes the entry point without modifying TAK classes.
The same source is preserved at `025355ba9f76bf6c41187897f4a5fcac93b82afb:java/PluginLauncher.java`.
The PR's `scripts/run-tak.sh` supplies `-Dloader.main=fi.pvarki.tak.PluginLauncher` and the external JAR path.

The supplied source compiled against the exact 5.8.84 plugin JAR with Java 17.
The test used `jar xf` instead of `unzip` because the cached JDK image lacks `unzip`.
A temporary plugin Pod at `10.244.0.27` joined the messaging service at `10.244.0.26`.
Logs confirmed Ignite startup and availability of `pluginDataFeedApi`, `pluginMissionApi`, and `pluginCoreConfigApi`.
The launcher wrote its readiness marker. The authenticated admin user-list request still returned HTTP 200.
The temporary Pod was removed after evidence collection.
The same launcher then started inside the shared server Pod with a private CoreConfig and runtime volume.
All three plugin APIs were available again after full server Pod replacement.

Keep the workaround isolated and optional. Compile and exercise it for each selected release.
A shared Pod does not alone resolve the override when messaging binds only to the Pod IP, rather than loopback.
Use the XML-preserving launcher with that binding model.

## Upstream handoff

Make the normal plugin entry point use the loaded Ignite configuration.
Preserve the XML bind address, discovery seeds, and other supplied settings.
Provide a supported initialization method so an external launcher does not need private-field reflection.
Test both same-host and separate-address discovery with the plugin remote APIs.

No external report was submitted. No TAK binary was patched.
Third-party plugin callbacks, recovery of an existing plugin process after messaging loss, and compatibility with another release remain unverified.
