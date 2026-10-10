# Consolidated implementation plan

Updated: 2026-10-10. Branch: `implementation/t0-foundation`.
This plan combines the completed T1 packaging decisions with the adopted strict fingerprint work.
The [checkpoint](implementation-status.md) records current progress and the next model gate.

## Inputs and authority

| Input | Pinned reference | Result |
| --- | --- | --- |
| Server runtime investigation | `a38531b`; [T1 follow-up](t1-single-pod-findings.md) | Shared server Pod, persistent authority, private follower files, native JKS, and basic recovery verified. |
| Strict fingerprint branch | `7f1e42c1112753cfa323d77182767ccbab1dc3eb`, merged by `fc07196` | Independent Java policy and tests imported without changes. No TAK entry point calls it. |
| Integration handoff | `integration-tak` commit `d9164a4141dd0064b18250cfac0b07b862284d2e`, `docs/tak-server-change-handoff.md` | Authentication, observation, capability, and final acceptance requirements incorporated below. |

The [integration handoff](../../integration-tak/docs/tak-server-change-handoff.md) records adoption of the strict fingerprint change.
The user's consolidation request brings that scope into this server workstream. Do not request adoption again.
It is a specific exception to the older restriction on TAK application changes.
It does not authorize the separate XML publication or file-auth error-handling patches in reports 004 and 005.
The unmodified T1 runtime remains the packaging baseline, not the final strict-authentication image.
The user confirmed that fresh server source will not be available.
All server behavior changes must use external launchers or runtime injections against the vendor binaries.
This constraint supersedes the matching-source prerequisite in the imported handoff and earlier plans.

Use one Pod with separate config, messaging, and API containers. Plugin manager is optional in the same Pod.
Keep the integration JNI/operator process in a separate Pod with its own Ignite profile.
These decisions supersede the original separate-Pod server requirement.
Keep the original implementation handoff's remaining requirements and stage protocol.
Its supplied file remains untracked. The missing companion migration plan has not been recovered or replaced by an assumed specification.
Sibling links require the local integration checkout; the pinned commit and path identify the source for other recipients.

## Completed consolidation

- [x] Merge the strict policy branch without discarding the newer T1 work or rewriting either history.
- [x] Review the policy, callers, tests, and declared limits. Rerun all 46 assertions with eight signed leaves in the pinned Java 17 ARM64 container.
- [x] Record the current binary's approved-set failure in [report 007](../bugreports/007-unapproved-same-uuid-certificate/HANDOFF.md).
- [x] Add the binary compatibility requirements, ownership boundaries, implementation slices, and live acceptance checks to this plan.

The [policy README](../extensions/strict-fingerprint/README.md) contains the runnable test command.
The consolidation run used `--pull=never`, `--network none`, a read-only source mount, and tmpfs for generated keys.
Results are in ignored `outputs/consolidation/strict-policy-tests.log`.
Policy tests do not establish TLS, CoT, HTTP, or session enforcement in TAK.

## Dependencies and ownership

Keep the pinned TAK `5.8-RELEASE-84` WAR and vendor JARs unchanged on disk.
Compile external extension code against those artifacts. Record their checksums and the extension build provenance.
Use the [plugin launcher](../bugreports/006-pluginmanager-forces-localhost/HANDOFF.md) as the starting pattern.
First inspect the exact binary's startup, Spring, and authentication paths for replaceable components.
Use a Java instrumentation agent only where launcher or component replacement cannot cover the required path.
Do not assume that the plugin's private-field injection proves authentication coverage.
Reject unsupported artifact hashes or hook signatures. Verify installation before accepting client traffic.
Older public source can guide inspection, but the target bytecode and tests determine compatibility.
Fresh upstream source is not a dependency. Core contracts and proof of injection coverage remain dependencies.

| Owner | Responsibility |
| --- | --- |
| Server | Image, external extensions and their configuration schema, strict admission, trusted management and authentication-evidence interfaces, runtime state, deployment base, and acceptance tests. |
| Integration | Core projection and readback, separate JNI process, observer and any selected guard, client packages, grants, and UI. Consume the server base without copying it. |
| Core | Immutable identity, effective permissions, approved credentials, purpose/generation mapping, issuance, durable activation evidence, and mapped predecessor revocation. |

The [Core contracts](../../integration-tak/docs/core-contracts.md) remain open at the pinned integration revision.
Resolve UUID encoding/restore, permission freshness, credential inventory and deadlines, issuance/export authority, namespace/Secret access, UserBinding writers/readiness, HTTP authority, and durable activation reporting.
Do not invent Core CRDs or treat fixture inputs as an agreed API.
Agree the trusted management writer, transport, freshness bound, and capability versions with integration.

## T2 implementation slices

T2 resumed after the user's explicit `Switched; resume T2` confirmation for `gpt-6.1-sol` / `high`.
The user confirmed `Switched; resume T1` on 2026-10-10 for the CoT investigation.
The [T1 follow-up](t1-cot-cache-findings.md) isolates the native base's reduced Ignite cache maximum.
Runtime model metadata is unavailable; user confirmation is the gate evidence.
See [native layout evidence](t2-native-layout.md).
Implement each coherent slice in small reviewed commits. Test injection seams against the pinned binaries before wiring strict authentication.

### 1. Package the proven Pod and storage layout

- [ ] Create one versioned Kustomize base and standalone/integrated overlays using ordinary OCI builds, Java 17, and the actual Python 3.12 runtime.
- [x] Correct the 64 MiB Ignite cache maximum to the tested 256 MiB value. Recheck CoT from the rendered native base, then remove the experimental live override.
- [ ] Verify cache and container resource budgets under the intended load.
- [x] Package the experimental adapter in the image. Use one configuration owner, non-overlapping replacement, and the lifetime lock; a singleton StatefulSet is suitable.
- [x] Preserve `/opt/tak/data/CoreConfig_config.xml` and config-container compatibility links. Retain `coreconfig.py` ownership merge, XSD validation, restrictive modes, backup, and atomic startup publication.
- [x] Seed private follower files from the validated authority. Keep ConfigMaps/Secrets as inputs and administrator-owned peers, groups, policy, listeners, and federation trust on persistent storage.
- [x] Give messaging persistent file-auth and API a private file-auth directory, including its backup. Persist owner backups and tighten permissions.
- [ ] Inventory mission/content/audit writes before moving mounts.
- [x] Document `coreconfig.MANAGED`, LDAP replacement, and separately declared Service/NetworkPolicy exposure for additional listeners. Preserve PVCs; RWO is not a lock and local-path results do not prove node reattachment.

Reuse the [storage design](coreconfig-kubernetes-design.md). Do not add a whole-file watcher or force-save JNI loop.

### 2. Implement bounded recovery and optional roles

- [ ] Use explicit discovery available before readiness. Give external JNI a distinct profile and restrict network access to required participants.
- [ ] Detect failure through a non-mutating remote operation. Implement finite operation/recovery bounds and visible failure status; specify container versus coordinated Pod replacement.
- [ ] Require integration observers to resubscribe and rescan after Ignite reconnect. Existing socket and marker probes cannot establish RPC health.
- [ ] Package the optional XML-preserving plugin launcher against the exact release. Keep its private-field workaround isolated and fail clearly on incompatibility. Keep retention as a long-running JAR unless one-shot support is proven.

T1 recovery times are observations, not an SLA. Optional roles remain unsupported beyond their recorded acceptance until their remaining tests pass.

### 3. Finish identities and database migration

- [ ] Consume coherent issuer-managed or supplied identity/password Secrets, preferring tested native JKS. Verify the served certificate after renewal and use only proven reload or coordinated replacement.
- [ ] Keep RSA CoT/JWT separate from HTTPS. Separate CoT client trust, federation trust, and outbound Java roots; retain administrator federation state.
- [ ] Use cert-manager/external PKI without mounting CA signing keys in ordinary Pods. Import existing identities first and preserve fingerprints and PVCs.
- [ ] Replace `firstrun.done` with a versioned SchemaManager Job, database-side exclusion, and separate migration credentials. Verify whether `takdb_base.sql` is required before deleting it.
- [ ] Retire the legacy certificate generators and their consumers under the script replacement plan below. Preserve existing identities and administrator trust during adoption.

The separate [schema Job](../k8s/schema/job.yaml) is a tested candidate for an empty database.
Its external launcher runs the pinned SchemaManager JAR's Flyway migrations without the vendor `repair` path.
Fresh, repeat, and concurrent runs passed with separate credentials in disposable databases.
A changed checksum stopped the Job without changing migration history.
Flyway provides database-side locking. The legacy SQL dump is unnecessary for an empty database.
Documented data grants keep the runtime role separate from the migration owner.
The repository's seeded legacy dump required exact V7/V9 checksum reconciliation.
The disposable upgraded schema matched a fresh install. Seeded roles and three added CoT, mission, and user rows survived.
An interrupted disposable Job stopped at blocked V98; a new Job applied V98–V106 and matched the fresh schema.
Test a full production-like data set, reviewed adoption, and other failure points before closing this item.
An [isolated fresh install and HTTPS renewal](t2-standalone-renewal.md) passed with supplied JKS stores and an unchanged password.
First startup exposed an API/message-service race; fix that ordering or make the failed API JVM exit promptly.
Then test password and trust rotation, automatic issuer renewal, and the actual standalone overlay.

### 4. Wire strict authentication and management

- [ ] Implement an external launcher/extension for messaging and API. Use the smallest replacement that covers the inspected call paths. If instrumentation is needed, pin its class/method targets and verify classloader behavior against the selected artifacts.
- [ ] Add an explicit strict file-auth mode in validated extension configuration. Keep new settings outside the unchanged vendor CoreConfig schema. Fail startup if required injection is absent or incompatible. Invalid or unavailable strict state must deny access without falling back to legacy mode.
- [ ] Expose a trusted complete-set update for one UUID's approved leaf fingerprints, explicit deadline, and conditional revision. Provide immutable readback and clear conflicts, failures, and limit errors.
- [ ] Apply and acknowledge the projection in both messaging and API JVMs. Bind permission and credential readback to the requested projection; preserve roles, groups, and the UUID account when one leaf is removed. Resolve uncertain writes by readback before retry.
- [ ] Define the owner that invalidates approval on stale/unavailable authority and enforces its freshness bound. Missing, expired, invalidated, and restarted state must deny access.
- [ ] Enforce after TLS chain/client-usage validation and before every role, group, cache, token, LDAP, or anonymous grant. Audit enabled certificate entry points and disable unsupported transports until tested.
- [ ] Stop denied messaging before the first CoT is routed. Cover protected HTTP, cached principals, existing connections, tokens, and resumed TLS sessions. Define and measure the revocation bound.
- [ ] Package and version the external extension, its configuration schema, and management capability with the unchanged WAR and `UserManager.jar`. Add a companion management JAR only if the new interface needs one. Expose the active strict mode, extension version, and vendor artifact identifiers so integration rejects incompatible or inactive enforcement.

Reuse `StrictFingerprintPolicy`. Its state is private to one JVM and is empty after restart.
Its random revisions are neither Core generations nor durable activation events.
Validate the current limits of 1,024 accounts, 32 fingerprints per account, and 256 account characters against intended deployments.
Do not encode a list in the legacy scalar field, alternate registrations, or delete the shared account to revoke one leaf.
A prior policy decision is not cancelled by concurrent removal; connection enforcement remains required.
Keep the optional disconnect guard decision open. A post-authentication guard cannot replace strict admission.

### 5. Provide completed-authentication evidence

- [ ] Inspect existing APIs for a completed-authentication signal. If none suffices, expose the smallest signal/query through the external strict-authentication extension.
- [ ] Bind positive evidence to the exact connection, UUID, leaf SHA-256, applied approval revision, and observation time. Provide an authenticated current-state recovery query for missed notifications.
- [ ] Support activation without requiring CoT or an HTTP application transaction. Test short-lived connections, stale/revoked/superseded observations, restart, reconnect, and resumption.

`ConnectionInfo` receives the peer leaf before TAK authentication completes and has no authentication-status field.
TLS success or connection/subscription presence alone cannot establish activation.
Integration owns observation and durable reporting; Core owns independent main/TAK-only activation and exact predecessor revocation.
Downloads and manual acknowledgement are not activation. Planned overlap has no default forced-cutover timer.
Do not build a second identity or issuance system in TAK.

The component probe also shows that later CoT replaces contact-map callsign edits.
Do not promise a durable callsign through that API. Bind any server contact update to an authenticated CoT UID and preserve identity and permissions.
Client preferences and a `client-update-required` outcome belong to integration.

### 6. Complete standalone operation, CI, and cleanup

- [ ] Provide Kind/existing-cluster standalone overlays and a narrow admin bootstrap Job without Core, RMAPI, integration CRDs/operator, or sibling checkouts. Strict standalone bootstrap must explicitly populate approvals; no implicit admin bypass.
- [ ] Expose appropriate CoT/federation TCP services and preserve TAK `/Marti` mTLS semantics separately from `/integrations/tak/api/v1`.
- [ ] After native replacements pass, remove Compose deployment/build orchestration, RM bootstrap/host/manifest logic, duplicate user/ZIP wrappers, and obsolete Azure/DevSpace paths. Keep APK/update content optional and pinned; retain historical LFS data.
- [ ] Provide coordinated backup/restore for database, XML, file-auth, trust, content, and identities. Uninstall must retain data. Integration separately excludes live grants from restore.
- [ ] Finish [CI migration](ci-migration.md): pinned actions, non-publishing PRs, `arc-runner-set`, native AMD64/ARM64 BuildKit with `/etc/buildkit/tls/{ca.crt,tls.crt,tls.key}`, and disposable Kubernetes validation of the exact candidate.
- [ ] Keep `TAK_PUBLISH_ENABLED` unset until acceptance passes. Target `ghcr.io/opendefence/tak-server`; add no Snyk placeholder. Publication still needs separate authorization and an independent destination clone check.

### 7. Retire fragile distribution scripts and legacy wrappers

The user requested this cleanup on 2026-10-10. Implement it after the CoT investigation and replacement checks pass.
Remove the six named scripts from supported workflows and image packaging. Do not replace them with renamed shell wrappers.

| Retire | Current consumers | Replacement |
| --- | --- | --- |
| `scripts/makeCert.sh` and copied `data/certs/makeCert.sh` | `standalone_init.py`, `make_client_zip.sh`, README and AGENTS examples | Issuer-managed or supplied identities and coherent password Secrets. Use cert-manager/external PKI for standalone issuance. Import existing certificates without changing fingerprints. |
| `scripts/delete_user.sh`, `disable_admin.sh`, `enable_admin.sh`, `enable_user.sh` | Wrapper chaining and operator examples; direct legacy `UserManager.jar certmod` calls | The trusted management interface in slice 4 for integrated projections. Use a narrow standalone bootstrap/management command against the same verified interface. Update roles and complete approval sets explicitly, with readback. Do not revoke one leaf by deleting its account or demote an administrator by deleting and recreating the user. |
| `scripts/make_client_zip.sh` | README and AGENTS client-package instructions; `templates/missionpkg` | Keep integrated issuance/export and client packages in Core and `integration-tak`. Document standalone package creation from externally issued credentials through a verified client import workflow. Remove server-side ZIP generation and retire its templates/dependencies once no supported consumer remains. |
| Vendor `makeRootCa.sh`, `cert-metadata.sh`, and copied certificate helper files | `standalone_init.py` copies the distribution certificate directory, edits metadata, and invokes CA generation | Replace the legacy standalone initializer with native identity inputs and the schema Job. Keep signing keys outside ordinary server Pods. Preserve existing trust and identities on adoption; do not copy executable certificate helpers into the PVC. |
| Vendor `make-connection-package.sh`, `revokeCert.sh`, and `generateClusterCerts*.sh` | Bundled in the pinned distribution and copied to `data/certs`; no direct repository caller found | Use the owning integration's package export, explicit approval removal plus PKI revocation, and issuer-managed cluster identities. Check external callers before removing the files from supported images or PVC initialization. |
| Vendor `/opt/tak/enable_admin.sh` | Bundled second admin entrypoint; no direct repository caller found | Use the verified standalone management/bootstrap interface above. Exclude this entrypoint from supported workflows. |
| Vendor `setenv.sh` | `run-tak.sh`, `user-manager.sh`, and the old account wrappers | Record the required options from the pinned binary tuple. Set explicit JVM, loader, profile, heap, Ignite, and TLS options in the maintained launcher. Verify server and management startup without sourcing vendor shell code. Keep vendor JAR/WAR bytes unchanged. |
| Downloaded `wait-for-it.sh` | Dockerfile, `standalone_init.py`, `firstrun_rm.sh`, and `enable_admin.sh` | Remove with obsolete bootstrap paths. Use bounded database checks in the schema Job and non-mutating remote readiness checks for server/bootstrap dependencies. An open socket is insufficient. |
| Vendor database setup, `upgrade-db.sh`, clear, archive, and restore scripts | Bundled in the pinned distribution; old Compose initialization uses `takdb_base.sql` instead | Use the versioned schema Job and the coordinated backup/restore procedure in slice 6. Never run a vendor clear or restore script against adopted data. Verify no supported caller before image cleanup. |

- [ ] Audit direct calls, sourced files, transitive vendor helpers, image entrypoints, and copy operations against the pinned distribution. Include optional plugin/retention roles, schema tooling, tests, CI, README, AGENTS, and integration consumers. Record each remaining dependency and its replacement before removal.
- [ ] Reuse `user_manager.py` and existing launchers only where their binary interface meets the required contract. The current `user-manager.sh` still sources `setenv.sh`; it is not the finished replacement. Strict complete-set projection needs slice 4's interface.
- [ ] Update supported commands, fixtures, tests, image copies, environment variables, and dependencies together. Retain historical reports as evidence. Stop executing stale helper copies on existing PVCs; never wipe a PVC to remove scripts.
- [ ] Prove fresh and repeated standalone bootstrap, identity import/renewal, user enable/disable, admin promotion/demotion, and single-leaf revocation. Verify preserved UUID, groups, other approved leaves, and administrator federation trust. Verify client package import in the owning integration workflow.
- [ ] Require an image/caller check that supported startup, management, migration, and package workflows do not execute these scripts. Repeat binary compatibility checks for each TAK release before removing the last fallback.

## T3 acceptance and T4 fixes

T3 uses `gpt-6-astra` / `high`; T4 uses `gpt-6.1-sol` / `high`.
Escalate unexplained runtime/design behavior through T1 `gpt-6-astra` / `xhigh` with a reproduction.
Use the final image, base, external extension/configuration, and vendor/management JAR tuple together. Preserve sanitized inputs, checksums, assertions, outcomes, and limits.

| Area | Required evidence |
| --- | --- |
| Injection compatibility | Both JVMs install the required hooks before client admission. Missing extension, wrong artifact hash, changed hook signature, and classloader/injection failure prevent strict startup. Capability/readiness checks cannot report protected service when enforcement is absent. |
| Strict admission | Approved main and TAK-only leaves for one UUID receive intended permissions. A third CA-valid same-UUID leaf receives no routed CoT or protected HTTP access. |
| Projection and sessions | Single-leaf removal preserves the other leaf/account. Stale/concurrent/uncertain updates, authority loss, expiry, restart, new/existing/resumed sessions, caches, tokens, and enabled alternate transports obey the policy and measured revocation bound in both JVMs. |
| Authentication evidence | Only the exact approved successor's completed authentication qualifies. Resubscription and recovery scans reject stale, unrelated, revoked, and superseded observations. |
| Install and persistence | Fresh/repeat standalone apply works. Admin edits survive container restart, Pod replacement, managed-input change, and supported upgrade. Invalid XML and competing owners preserve state. |
| Save failures | Private writes cannot overwrite authority. Test persistent backup placement, interrupted owner saves/concurrent reads, disk/permission failure, and separate messaging-owner/API-private file-auth failure with RPC, memory, disk, restart, and retry observations. |
| Recovery | Messaging-only restart and full replacement restore JNI, HTTPS, CoT, and supported observer/plugin behavior within the declared bound or report explicit failure. |
| TLS and schema | Coherent renewal changes the served identity while preserving trust separation. Fresh/no-op/upgrade/concurrent/interrupted/retried schema Jobs are safe. |
| Storage and operation | Coordinated restore preserves identities/permissions; uninstall retains data. Test promised reattachment, both architectures, offline install/restart/upgrade, production NetworkPolicy, supported optional roles, and a real federation peer if advertised. |
| Integration | The actual integration consumes the final JAR/base/image and capability contract. Current Core authority and both applied server revisions determine readiness. |

Keep [reports 001–007](../bugreports/README.md) and their evidence limits explicit.
Reports 001/002 do not require restoring separate Pods or patching locality for the selected layout.
Report 003 needs file-auth isolation. Report 006 needs optional-role recovery checks.
Reports 004/005 still need fault injection; no failed-durable-save/successful-HTTP case has been demonstrated.
If packaging cannot satisfy durability, prepare the smallest external injection and reproduction for a separate decision.
Specify symlink handling, permissions, backup ordering, and crash guarantees before seeking that decision.

## T5 review and T6 delivery

T5 uses fresh `gpt-6-astra` / `high` review and Ponytail audit. Return fixes through T4 and rerun affected checks.
T6 uses `gpt-6.1-sol` / `medium` for closure, with no new runtime changes.
Deliver one versioned contract: image/build provenance, external extension source and checksums, and unchanged vendor WAR/JAR checksums; extension configuration/strict/management capability versions; reusable base/overlays; Services, Secrets, mounts, profiles, and network requirements; update/readback/observation semantics; operation/recovery bounds; renewal, upgrade, and restore procedures; supported platforms/storage/roles and acceptance limits.
Integration's I0 image still carries a 5.8.69 JAR and must be repinned to this final tuple.
Do not advertise strict authentication or production readiness before the coupled live acceptance passes.
