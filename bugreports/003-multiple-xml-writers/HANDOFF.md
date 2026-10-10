# 003: Java startup bypasses persistent-state writer ownership

Status: open, established by binary inspection. Concurrent data loss has not been reproduced.
Impact: the shared-volume deployment can have several Java writers despite the configuration wrapper lock.
Affected candidate: TAK `5.8-RELEASE-84`; see [environment](../ENVIRONMENT.md) and [inspection evidence](evidence.json).

## Finding

`LocalConfiguration` can save defaults, QoS changes, and version upgrades during initialization.
Its save method uses a JVM-local monitor. It does not acquire the wrapper's configuration-owner file lock.
`FileAuthenticator.init()` in the API retrieves file-auth state from messaging and writes the configured auth file before loading it locally.
`FileAuthenticator.saveChanges()` also writes that authority during user-management operations.
In this deployment, those paths point at shared PVC files.

Expected: config owns persistent CoreConfig writes, and the user-management service owns persistent file-auth writes.
Actual inspection: additional startup paths can write the same authorities without cross-process ownership enforcement.
The ordinary restart test preserved all three file-auth identities. It did not test overlapping writes or prove corruption.

## Reproduction still needed

1. Use disposable copies of the shared XML and file-auth state.
2. Trace file opens and writes by process while starting API beside messaging and while starting followers with configuration that needs defaults or an upgrade.
3. Hold the config wrapper lock and show whether follower Java writes still occur.
4. Overlap API startup with a controlled user update. Compare the acknowledged update, persistent XML, and state after restart.

Treat the race as a hypothesis until this test captures it. Do not infer corruption from file timestamps alone.

## Handoff

Validate these paths against matching source. Keep persistent writer ownership explicit by role.
Followers may use in-memory state or private runtime copies, but must not publish the shared authority during startup.
Preserve offline tool behavior and existing supported deployment modes.
Coordinate the change with [001](../001-coreconfig-admin-edits-lost/HANDOFF.md); fixing its save condition alone does not exclude other writers.

Acceptance requires process-level write traces, competing-owner rejection, simultaneous user-update/startup tests, and restart/upgrade preservation.
Only the designated owner may open each persistent authority for writing.
A proposed application change still needs the existing patch decision. No race reproduction or patch is complete.
