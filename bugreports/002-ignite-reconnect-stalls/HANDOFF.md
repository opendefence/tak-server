# 002: Messaging replacement stalls remote services

Status: open, reproduced in the tested topology. Impact: remote administration and messaging startup remain unavailable.
Affected candidate: TAK `5.8-RELEASE-84` with Ignite `2.18.0`; see [environment](../ENVIRONMENT.md).
Evidence: [Pod addresses, selected error frames, and recovery times](evidence.json).

## Reproduction

1. Start all roles and confirm `GET /Marti/api/user-management/api/list-users` succeeds with the administrator certificate.
2. Confirm two authenticated clients exchange CoT in both directions.
3. In the disposable namespace, delete only the messaging Pod. Keep config and API running.
4. Confirm messaging receives a different Pod IP. Repeat the user-list request with a finite client timeout.
5. Compare the response against Pod readiness and inspect the API error and messaging startup logs.

Expected: remote calls reconnect, or readiness detects the failure and a bounded recovery procedure restores service.
Actual: messaging changed from `10.244.0.18` to `10.244.0.22`.
API and config retained socket readiness. The user-list request returned HTTP 500 with `IgniteClientDisconnectedException` in the remote `getUserList` path.
New messaging did not complete startup until config was restarted.
The wrapper probe's false readiness is an adapter defect; the stalled runtime and reconnection behavior need TAK/Ignite investigation.

## Recovery observed

Restart config using its `Recreate` deployment. Once config is ready, request an API restart.
Confirm messaging and the new API finish startup, then repeat the remote read and CoT exchange.
This single manual sequence restored tested traffic within 137 seconds of recovery starting.
It does not establish automatic recovery, a production time bound, or separate JNI-client recovery.
The restart also exposed the accepted-edit loss reported in [001](../001-coreconfig-admin-edits-lost/HANDOFF.md).

## Handoff

The root cause is unresolved. A changed address is the trigger, not proof of the underlying defect.
Reproduce with the same binaries, then capture Ignite topology, disconnect/reconnect events, service deployment, thread dumps, and discovery state across replacement.
Separate TAK service re-registration from Ignite client reconnect and DNS behavior before choosing a fix.
Do not assume that a new standalone CLI client proves existing API/config clients recovered.

Use a non-mutating remote invocation to detect failure. `getRemoteConfiguration()` can return cached state and is not sufficient by itself.
The observed admin user-list request is a diagnostic; it is not yet a minimal production readiness design.
The user later selected a shared Pod. This supersedes the original handoff's separate-Pod requirement.
Keep the original reproduction as upstream evidence rather than treating the topology change as an upstream fix.

## Shared-Pod follow-up

With config, messaging, and API in one Pod, a messaging-container restart kept the Pod IP at `10.244.0.26`.
The existing API and config containers did not restart.
Authenticated user-list reads and bidirectional CoT passed within 33 seconds of the restart request in this observation.
A full Pod replacement also restored those checks and preserved the tested administrator edits.
See [selected evidence](../001-coreconfig-admin-edits-lost/single-pod-evidence.json) and [the follow-up findings](../../docs/t1-single-pod-findings.md).
These results support coordinated Pod replacement and remove the independent new-IP role change from the intended deployment.
They do not prove a production time bound or repair the separate-Pod failure.

Acceptance requires repeated new-IP replacement, bounded detection, and recovery of existing API/config clients, a separate JNI client, verified HTTPS, and authenticated CoT.
Any coordinated recovery must cap retries, reject concurrent config owners, report failure, and preserve administrator state.
No automatic recovery implementation or source patch has been made.
