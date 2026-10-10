# 003: Shared-file packaging exposes multiple Java writers

Status: reclassified as a deployment-specific risk, not an established upstream TAK defect. Concurrent data loss has not been reproduced.
Impact: the shared-volume deployment can have several Java writers despite the configuration wrapper lock.
Affected candidate: TAK `5.8-RELEASE-84`; see [environment](../ENVIRONMENT.md) and [inspection evidence](evidence.json).

## Finding

`LocalConfiguration` can save defaults, QoS changes, and version upgrades during initialization.
Its save method uses a JVM-local monitor. It does not acquire the wrapper's configuration-owner file lock.
`FileAuthenticator.init()` in the API retrieves file-auth state from messaging and writes the configured auth file before loading it locally.
`FileAuthenticator.saveChanges()` also writes that authority during user-management operations.
In this deployment, those paths point at shared PVC files.

Expected: config owns persistent CoreConfig writes, and the user-management service owns persistent file-auth writes. Followers may write private runtime copies.
Actual inspection: the T1 shared-file layout directs additional startup writers to the persistent authorities.
The ordinary restart test preserved all three file-auth identities. It did not test overlapping writes or prove corruption.

## Historical layout and correction

Before commit `d7682ca`, `scripts/start-tak.sh` selected `/opt/tak/data/CoreConfig_${1}.xml` for each role.
Each container linked its `/opt/tak/CoreConfig.xml` to that role's file.
Commit `d7682ca` changed every role to the canonical config-service file.
The inspected parent, `a36e91c`, regenerated the role files at startup; it is evidence for separate paths, not a safe persistence implementation to restore verbatim.

The user's intended model keeps only the config-service CoreConfig as persistent authority.
Other roles use private, writable bootstrap files and obtain runtime configuration through Ignite.
`CoreConfigFacade` supports this distinction: followers fetch remote configuration from the config service and refresh it on configuration notifications.
Verify direct local reads during bootstrap and upgrades before treating every follower file as disposable.
Startup writes to those private files do not violate persistent writer ownership.
The earlier report overstated the need for a TAK patch to prevent them.

File-auth needs separate isolation. The old template still used one `/opt/tak/data/UserAuthenticationFile.xml` path.
API initialization obtains that path from remote CoreConfig, so changing only its local CoreConfig attribute may not redirect the write.
The same path can resolve to different storage in each container. Verify messaging persistence and API-local storage before proposing application changes.

## Private CoreConfig fixture

The [shared-Pod follow-up](../../docs/t1-single-pod-findings.md) restored private CoreConfigs for messaging, API, and plugin manager.
Actual admin saves changed only the config authority among the four inspected CoreConfig files.
Follower hashes stayed unchanged while API reads returned the new settings.
Full Pod replacement preserved the edits and seeded fresh follower copies from the saved authority.
See [selected path and value evidence](../001-coreconfig-admin-edits-lost/private-files-evidence.json).
This validates the tested bootstrap and admin-save path. File-auth isolation, overlapping writes, upgrade paths, and process-level traces remain untested.

## Reproduction still needed

1. Compare the T1 shared-file layout with private follower CoreConfigs and separately isolated file-auth storage. Use disposable test state.
2. Trace file opens and writes by process while starting API beside messaging and while starting followers with configuration that needs defaults or an upgrade.
3. Hold the config wrapper lock and show whether follower Java writes still occur.
4. Overlap API startup with a controlled user update. Compare the acknowledged update, persistent XML, and state after restart.

Treat the race as a hypothesis until this test captures it. Do not infer corruption from file timestamps alone.

## Handoff

Restore file isolation in the deployment adapter before requiring an upstream writer patch. Keep persistent writer ownership explicit by role.
Followers may write private runtime copies, but must not publish the shared authority during startup.
Preserve offline tool behavior and existing supported deployment modes.
Coordinate the change with [001](../001-coreconfig-admin-edits-lost/HANDOFF.md); fixing its save condition alone does not exclude other writers.

Acceptance requires process-level write traces, competing-owner rejection, simultaneous user-update/startup tests, and restart/upgrade preservation.
Only the designated owner may open each persistent authority for writing.
An application change is needed only if verified runtime behavior cannot preserve this separation.
The private CoreConfig fixture passed; full ownership acceptance and a race reproduction remain incomplete.
