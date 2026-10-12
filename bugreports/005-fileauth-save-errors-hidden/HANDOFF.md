# 005: File-auth persistence errors are suppressed

Status: open, established by binary inspection. End-to-end failure injection is pending.
Impact: a file-auth update may affect memory/cache without a durable save or a visible error.
Affected candidate: TAK `5.8-RELEASE-84`; see [environment](../ENVIRONMENT.md) and [inspection evidence](evidence.json).

## Finding

When a control update and user are present, `FileAuthenticator.saveChanges()` publishes that update before calling `JAXBUtils.saveJAXifiedObject()`.
The save call catches `Exception`; the inspected handler only emits a debug message when debug logging is enabled.
The handler does not rethrow the failure to its caller.
The declared exceptions therefore do not establish that a persistence error reaches the user-management request.

Expected: callers can distinguish a durable update from a failed save, and an operator can see the failure without enabling debug logs.
Actual inspection: the persistent write can fail after the control update, with its exception suppressed.
The ordinary T1 user-registration and restart tests succeeded. They did not exercise this failure path or prove a successful HTTP response after a failed save.

## Effect of private role files

This finding concerns `UserAuthenticationFile.xml`, not CoreConfig persistence.
Private CoreConfigs do not change the save exception handler.
An API-local file-auth copy can fail without losing the messaging owner's persistent file; test that case separately.
The reported durability risk concerns failure on the actual persistent file-auth owner.
Inject the failure there before claiming an acknowledged user update is lost.

## Live storage verification

Rechecked the owned T1 environment on 2026-10-10 without changing application state.
The live CoreConfig selects `/opt/tak/data/UserAuthenticationFile.xml`.
The `tak-data` PVC is Bound and mounted at `/opt/tak/data` in API, messaging, and config Pods.
API and messaging report the same regular file, device `64772`, inode `176722332`, and mode `0644`.
The `.backup` file is also on that mount. No nested mount or symlink redirects the live file elsewhere.
Selected observations and source hashes are retained in [evidence](evidence.json).

This is persistent across Pod replacement, as also observed in the earlier identity checks.
The test PV uses node-local storage with reclaim policy `Delete`; it is not a backup or proof of survival after node/cluster removal.
The open question in this report is error propagation when a persistent write fails, not whether the current file is on a PVC.

## Reproduction still needed

1. Start the exact runtime with disposable file-auth state and normal logging.
2. Cause a controlled persistent-write failure, such as an unwritable test target or a full isolated filesystem.
3. Submit one user-management update through the real remote interface.
4. Record the request result, operator log, in-memory value, on-disk value, and value after restart.
5. Restore writable storage and test a retry without duplicating or losing the update.

## Handoff

Confirm the exception path and its callers in the pinned bytecode before implementing any workaround.
Fresh server source will not be available. Any locally adopted fix must use external injection as specified in the [current plan](../../docs/implementation-plan.md).
Propagate persistence failures through the service boundary and log a credential-free error at an appropriate level.
Define update ordering so a reported success means the authoritative file has been saved.
Coordinate with [003](../003-multiple-xml-writers/HANDOFF.md) and [004](../004-unsafe-xml-publication/HANDOFF.md) rather than adding a second writer or whole-file watcher.

Acceptance requires injected I/O failures to produce a visible error and a failed caller result, a recoverable authority, and a safe retry.
Verify the real remote interface and restart behavior. Do not rely only on a unit test of the catch block.
No failure-injection result or application patch is complete; the existing patch decision remains open.
