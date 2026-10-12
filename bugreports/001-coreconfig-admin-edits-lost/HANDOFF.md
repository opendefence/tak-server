# 001: Administrator edits are lost with separate role IPs

Status: open, reproduced. Impact: accepted administrator configuration is lost on restart.
Affected candidate: TAK `5.8-RELEASE-84`; see [environment](../ENVIRONMENT.md).
Evidence: [selected responses and file observations](evidence.json).

## Shared-Pod control experiment

The user selected a shared Pod after the original separate-Pod reproduction.
With the same image, PVC, and shared-file mapping, both administrator edits reached the canonical XML.
The disabled peer and recency value survived a full Pod replacement from `10.244.0.25` to `10.244.0.26`.
Authenticated user-list reads and bidirectional CoT passed after replacement.
See [selected control evidence](single-pod-evidence.json) and [the follow-up findings](../../docs/t1-single-pod-findings.md).
This supports the address-locality explanation. It does not exclude every possible concurrent-write race.
The upstream defect remains relevant to separate role addresses. Co-location avoids this tested trigger without a TAK patch.

## Reproduction

1. Start the three roles using the shared environment. Confirm the test peer is absent and the recency value is `43200`.
2. As the certificate-authenticated administrator, send `POST /Marti/api/outgoingconnections` with this body:

   ```json
   {"displayName":"t1_persistence_peer","address":"127.0.0.1","port":19001,"enabled":false,"reconnectInterval":60,"protocolVersion":2}
   ```

3. Read `GET /Marti/api/federationconfig`. Preserve its fields and change only `data.missionFederationDisruptionToleranceRecencySeconds` to `43201`.
4. Send that modified `data` object to `PUT /Marti/api/federationconfig`. Keep the full response and request private: they include truststore credentials.
5. Read both resources again. Compare the canonical XML checksum and the two selected values on the PVC.
6. Replace messaging, then restart config and API as described in [002](../002-ignite-reconnect-stalls/HANDOFF.md). Read both resources again.

Expected: successful saves reach the canonical XML and survive restart.
Actual: both writes returned HTTP 200 and appeared in API reads, but neither reached the XML.
Its SHA-256 stayed unchanged. After restarts, the peer was absent and the recency value returned to `43200`.
The test exercised the API used by the admin UI, not browser interaction.

## Cause and scope

Inspection of `IgniteHolder.areTakserverIgnitesLocal()` shows that it compares messaging and API node address sets.
`DistributedConfiguration.saveChanges()` permits the non-cluster config service to save only when those address sets satisfy that test.
Separate Pod IPs make the test false once both roles are present.
`CoreConfigFacade` delegates administrator mutations to this service, leaving edits in memory/cache without publishing the file.
The compatibility symlink was correct, and the canonical file existed with mode `0600`.

## Write-race assessment

The T1 test used one shared CoreConfig file. A competing writer could therefore restore old contents.
Before/after checksums alone cannot distinguish that race from a skipped save. No process-level write trace was captured.
However, direct `javap` inspection confirms that the save guard bypasses `JAXBUtils` when cluster mode and the locality test are false.
This mechanism does not depend on shared files or concurrent writes. Private follower files do not change the guard.
The locality helper also returns true when the API address set is empty.
Thus startup topology can change save eligibility before and after API joins, independently of filesystem races.
The web admin and REST API require the API role. The pre-API case explains startup saves, not administrator edits made before API is available.

Repeat the edit with private follower CoreConfigs and trace the persistent owner's writes before changing TAK.
Keep the roles running with stable, distinct addresses during the edit.
Capture the save branch and file activity to distinguish no save from a save followed by an overwrite.
The guard is verified by bytecode; an additional race in the original run remains unexcluded.

## JNI observer assessment

An Ignite client reached through JNI can, in principle, observe `config-cache` updates for key `coreConfig` or listen for `CONFIG_TOPIC_KEY` notifications.
The selected TAK classes already use these mechanisms. The topic carries an invalidation signal, so its consumer must fetch the current configuration.
Apache Ignite documents [continuous queries](https://ignite.apache.org/docs/ignite2/latest/key-value-api/continuous-queries) for cache changes.
This is an interface-level feasibility assessment, not a live JNI validation.

The inspected `CoreConfig` remote interface has `saveChanges()` and `saveChangesAndUpdateCache()`, but no force-save bypass.
Both use the guarded distributed save path. Repeating either call from JNI does not remove the address condition.
Calling `LocalConfiguration.saveChanges()` through JNI invokes the client JVM's singleton and filesystem, not the server JVM's singleton.
It can only save the desired snapshot locally if the client explicitly fetches and installs that snapshot and has access to the destination.

Two bypass designs are possible, but neither is an existing remote force-save operation:

- Run a persistence hook inside the config JVM. It can access the owner's current configuration and bypass the guard. It requires server-side code and must still address publication and error handling.
- Let an external observer fetch and atomically persist snapshots. It becomes a persistent writer and needs exclusive ownership, restart coordination, reconnect reconciliation, and protection against older snapshots overwriting newer state.

An asynchronous observer cannot make the original admin HTTP response certify durable storage.
A crash between API success and observer publication can still lose the edit.
A hook triggered after a notification has the same acknowledgement gap unless the request waits for persistence.
Calling `CoreConfigFacade.saveChanges()` from its own topic listener would also emit another notification; avoid a notification loop.
A watcher can be a recovery aid, but accepting it as the primary saver changes the persistence contract.
No watcher, hook, or forced save was installed or executed.

## Handoff

For an upstream fix, the vendor must reproduce this against its matching source or a fixed build.
Fresh server source will not be available locally. Any locally adopted workaround must use external injection as specified in the [current plan](../../docs/implementation-plan.md).
The proposed fix makes the configuration service the persistent writer independently of IP equality.
Keep save failures visible to the caller. Isolate follower files as described in [003](../003-multiple-xml-writers/HANDOFF.md) before deciding whether startup paths need an application change. Review publication separately in [004](../004-unsafe-xml-publication/HANDOFF.md).
Do not globally change `areTakserverIgnitesLocal()` or enable TAK cluster mode to bypass this condition.
The selected shared-Pod architecture does not require this source patch to pass the tested saves.

Acceptance requires both edits to reach the PVC before successful completion and survive config/API restart, full rollout, and a supported upgrade.
Managed-input reconciliation must preserve these administrator-owned fields.
Regression checks must also cover the existing same-address mode and offline tools.
No upstream fix, supported-upgrade result, or complete release acceptance is claimed.
