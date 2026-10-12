# 007: An unapproved same-UUID certificate receives account permissions

Status: open against the approved-set requirement. Reproduced with actual TAK classes in an isolated component test.
Affected candidate: TAK `5.8-RELEASE-84`; the artifact hashes match the [T1 environment](../ENVIRONMENT.md).
Evidence: [the integration component-probe record](evidence.txt), copied unchanged from `integration-tak` commit `d9164a4141dd0064b18250cfac0b07b862284d2e`, path `docs/evidence/i1-binary-probe.txt`.
Its SHA-256 is `sha256:9c7569cfd4eca905a338fb6f0fc0218d4b159b5ccb9ef19dca166d7a658844a1`.

## Reproduction and result

The integration probe loads the selected WAR's unmodified authentication classes in an isolated JVM.
Its source is `spikes/i1/BinaryProbe.java` at the integration revision above.
It creates a temporary CA and four distinct signed leaves. Main, TAK-only, and unapproved leaves share one UUID CN.
A fourth leaf has another UUID. The fixture alternates the stored scalar fingerprint between main and TAK-only.

Expected for the required strict mode: only the explicitly approved leaves receive the UUID account's permissions.
Observed: main, TAK-only, and the unapproved same-UUID leaf all receive `ROLE_READONLY` and both fixture group directions.
Changing the stored scalar fingerprint does not remove the unapproved leaf's permissions.
The other-UUID control receives only anonymous permissions in this fixture.
The inspected matching behavior accepts the fingerprint or account identifier; it does not enforce a complete approved leaf set.

This result depends on a CA-valid leaf with the same UUID. It does not establish acceptance of arbitrary untrusted certificates.
The test invokes actual components but performs no network TLS handshake, live CoT routing, protected HTTP request, or session-resumption test.
Its successful process exit means the probe reproduced the unexpected behavior, not that strict authentication passed.
The evidence also contains a separate contact-handler observation; that behavior is not the authentication finding.

## Adopted fix and handoff

The user adopted strict fingerprint authentication. Policy commit `7f1e42c` is merged into the implementation branch by `fc07196`.
Its [policy and conformance tests](../../extensions/strict-fingerprint/README.md) passed 46 assertions again during consolidation.
TAK does not call the policy yet. The running server remains unchanged and still lacks the required enforcement.

Fresh server source will not be available. Follow the [consolidated plan](../../docs/implementation-plan.md) for external injection against pinned binaries, explicit strict mode, trusted complete-set management, both JVM projections, admission checks, sessions, and completed-authentication evidence.
Do not store a fingerprint list in the old scalar field, alternate registrations, or remove the whole account to revoke one leaf.
This authentication adoption does not authorize unrelated XML persistence patches.

Acceptance requires two approved same-UUID leaves to work, a third unapproved leaf to receive no routed CoT or protected HTTP access, and independent single-leaf revocation without losing account permissions.
Also test stale/expired/unavailable/restarted state, concurrent updates, readback in both JVMs, existing and resumed sessions, caches/tokens, and the documented revocation bound.
Repeat with one final image/extension/configuration/vendor-JAR/management tuple and the actual integration client.
Missing or incompatible injection must prevent strict startup in both JVMs.
No external report was submitted. No live enforcement or production-readiness claim is made.
