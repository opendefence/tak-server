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

## Reproduction still needed

1. Start the exact runtime with disposable file-auth state and normal logging.
2. Cause a controlled persistent-write failure, such as an unwritable test target or a full isolated filesystem.
3. Submit one user-management update through the real remote interface.
4. Record the request result, operator log, in-memory value, on-disk value, and value after restart.
5. Restore writable storage and test a retry without duplicating or losing the update.

## Handoff

Confirm the exception path and its callers in matching source before editing.
Propagate persistence failures through the service boundary and log a credential-free error at an appropriate level.
Define update ordering so a reported success means the authoritative file has been saved.
Coordinate with [003](../003-multiple-xml-writers/HANDOFF.md) and [004](../004-unsafe-xml-publication/HANDOFF.md) rather than adding a second writer or whole-file watcher.

Acceptance requires injected I/O failures to produce a visible error and a failed caller result, a recoverable authority, and a safe retry.
Verify the real remote interface and restart behavior. Do not rely only on a unit test of the catch block.
No failure-injection result or application patch is complete; the existing patch decision remains open.
