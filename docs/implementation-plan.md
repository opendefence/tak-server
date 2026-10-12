# Consolidated implementation plan

Updated: 2026-10-11. Branch: `implementation/t0-foundation`.
This plan combines the completed T1 packaging decisions with the adopted strict fingerprint work.
The [checkpoint](implementation-status.md) records current progress and the next model gate.

## Inputs and authority

| Input | Pinned reference | Result |
| --- | --- | --- |
| Server runtime investigation | `a38531b`; [T1 follow-up](t1-single-pod-findings.md) | Shared server Pod, persistent authority, private follower files, native JKS, and basic recovery verified. |
| Strict fingerprint branch | `7f1e42c1112753cfa323d77182767ccbab1dc3eb`, merged by `fc07196` | Initial independent Java policy and tests imported without changes. The current pinned image also has admission hooks. |
| Integration handoff | `integration-tak` commit `d9164a4141dd0064b18250cfac0b07b862284d2e`, `docs/tak-server-change-handoff.md` | Authentication, observation, capability, and final acceptance requirements incorporated below. |

The [integration handoff](../../integration-tak/docs/tak-server-change-handoff.md) records adoption of the strict fingerprint change.
The user's 2026-10-11 decision assigns integrated strict authentication to the `tak-operator` in `integration-tak`.
Its [remaining work list](../../integration-tak/docs/remaining-work-handoff.md#integrated-strict-authentication-ownership) owns contracts, projection, freshness, sessions, observation, and coupled acceptance.
Only required image changes remain in this workstream. This supersedes the earlier broad server assignment.
The adopted external extension remains authorized. Do not request adoption again.
It does not authorize the separate XML publication or file-auth error-handling patches in reports 004 and 005.
The unmodified T1 runtime remains the packaging baseline, not the final strict-authentication image.
The user confirmed that fresh server source will not be available.
All server behavior changes must use external launchers or runtime injections against the vendor binaries.
This constraint supersedes the matching-source prerequisite in the imported handoff and earlier plans.

Use one Pod with separate config, messaging, and API containers. Plugin manager is optional in the same Pod.
Keep the `tak-operator` JNI process in a separate Pod with its own Ignite profile.
Deploy both Pods in the `integration-tak` namespace owned by the sibling integration manifests.
The server's integrated overlay must not create another namespace or own the sibling's workloads.
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

Keep the pinned TAK `5.8-RELEASE-92` WAR and vendor JARs unchanged on disk.
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
| Server | Image, shipped policy and hooks, required in-image management/evidence interfaces, binary compatibility, runtime state, native deployment, and image acceptance. |
| `integration-tak` | `tak-operator` strict-authentication contracts, Core projection and readback, freshness, sessions, observation, durable reporting, and coupled live acceptance. Also owns client packages, grants, and UI. Consume the server base without copying it. |
| Core | Immutable identity, effective permissions, approved credentials, purpose/generation mapping, issuance, durable activation evidence, and mapped predecessor revocation. |

The integration workstream owns resolution of the [Core contracts](../../integration-tak/docs/core-contracts.md).
Do not invent Core CRDs or treat fixture inputs as an agreed API.
Agree any required image interface with the `tak-operator` workstream before implementing it.
Strict fingerprint approval applies only to integrated deployments backed by
OpenDefence Core User authority. Standalone uses TAK's legacy certificate
authentication and administrator bootstrap without approval projection.

### Image interface handoff

The current image installs pinned admission hooks when `TAK_AUTH_MODE=strict`.
The integrated overlay selects legacy mode.
Strict approval state starts empty; trusted updates and both-JVM readback remain missing.
Integration can continue independently where existing APIs suffice.

For a required image change, provide its digest, unchanged vendor checksums, extension version, and active-mode check.
Document the interface schema, errors, access controls, and compatibility limits.
Verify missing or incompatible injection fails before client traffic.
The integration workstream owns the writer, freshness renewal, observer, and final coupled acceptance.
Use its [image change handoff](../../integration-tak/docs/tak-server-change-handoff.md) for reproduced gaps.

## T2 implementation slices

T2 resumed after the user's explicit `Switched; resume T2` confirmation for `gpt-6.1-sol` / `high`.
The user confirmed `Switched; resume T1` on 2026-10-10 for the CoT investigation.
The [T1 follow-up](t1-cot-cache-findings.md) isolates the native base's reduced Ignite cache maximum.
Runtime model metadata is unavailable; user confirmation is the gate evidence.
See [native layout evidence](t2-native-layout.md).
Implement each coherent slice in small reviewed commits. Test injection seams against the pinned binaries before wiring strict authentication.

### 1. Package the proven Pod and storage layout

- [ ] Create one versioned Kustomize base and standalone/integrated overlays using ordinary OCI builds, Java 17, and the actual Python 3.12 runtime.
- [x] Add a namespace-neutral server base and an integrated overlay targeting `integration-tak`, created by the sibling integration manifests. Its NetworkPolicy admits the `tak-operator` Pod to Ignite. Strict-mode acceptance and a pinned production image remain open.
- [x] Add Zarf standalone/integrated flavors with deploy-time parameters for public native environment inputs and ordered schema/grants/server components. Read PostgreSQL connection/migration values from CNPG's generated application Secret; consume a separate CNPG-managed runtime role Secret and installation-generated store-password Secret. Keep the package aligned with overlay changes. A connected local-image standalone Zarf deployment passed; building an offline package from a published digest remains open.
- [ ] Wire installation-owned one-time generation and retention for the CNPG runtime role password Secret and JKS store-password Secret, followed by issuer-managed JKS issuance. Keep values out of Zarf parameters and preserve them on redeploy/renewal; validate CNPG role and privilege grants before declaring either flavor self-contained.
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
- [ ] Complete production adoption of the versioned SchemaManager Job, database-side exclusion, and separate migration credentials. Keep `takdb_base.sql` as a legacy upgrade fixture until adoption evidence is complete.
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
The API launcher now waits up to 180 seconds for the messaging CoT listener before starting its JVM, and exits for a Kubernetes retry if it never appears. A delayed-messaging rollout passed; reproduce the original missing-metrics-service failure on a fresh install before closing this race.
Then test password and trust rotation, automatic issuer renewal, and the actual standalone overlay.

### 4. Maintain image support for integrated strict authentication

The `tak-operator` owns the [strict-authentication work list](../../integration-tak/docs/remaining-work-handoff.md#integrated-strict-authentication-ownership).
Keep controller work and Core contracts in that repository.
This slice covers only code and interfaces shipped in the TAK image.

- [x] Inspect pinned messaging and HTTP authentication seams. The [vendor compatibility probe](t2-strict-hook-inspection.md) rejects unsupported hashes and inspected signatures.
- [x] Implement an external launcher/extension for messaging and API. The agent pins the vendor tuple and transformed class bytes, verifies both classloader paths before TAK startup, and fails closed on missing/incompatible injection. Live negative CoT/HTTP checks passed; integration owns approved-client and revocation acceptance.
- [x] Add explicit `TAK_AUTH_MODE` startup validation outside the vendor CoreConfig schema. A missing/incompatible agent fails strict startup; empty, invalidated, or restarted approval state denies access without a legacy fallback. Keep separate future management settings outside the vendor schema.
- [x] Permit the `tak-operator`'s exact mTLS leaf through strict HTTP admission when its public certificate is supplied by `tak-integration-admin/tls.crt`. Its issuer must already be in TAK client trust, and the `tak-operator` must register that leaf as an administrator through JNI. The exception applies only to the API JVM; TAK's REST authorization still decides access. The certificate alone is not the approval-management endpoint.
- [ ] Provide a trusted policy update/readback interface if existing APIs cannot reach the in-JVM state. Use 8443 and the existing integration administrator mTLS identity. Require complete sets, explicit deadlines, conditional revisions, immutable readback, and clear conflicts and limit errors in both JVMs.
- [ ] Close reproduced gaps in admission, session hooks, or the policy identity model that require image changes. Preserve chain/client-usage validation, TAK role authorization, and denial before protected access. The current exact-CN model needs compatibility review against integration's per-certificate records and Core's UUID URI SAN.
- [ ] Version the extension, configuration, and required management capability with the unchanged WAR and `UserManager.jar`. Expose the active mode and artifact identifiers. Add a companion management JAR only if the interface needs one.

Reuse `StrictFingerprintPolicy`. Its state is private to one JVM and is empty after restart.
Its 60-second authority lease is enforced in the image; the `tak-operator` owns renewal and invalidation.
The exact `tak-integration-admin` leaf pin permits only the API path, not general installed integration access or 8089.
Integration owns installed identity inventory, permission projection, complete-set readback, session handling, and revocation timing.
A disconnect after authentication cannot establish strict admission.

### 5. Provide image authentication evidence only when needed

Integration owns completed-authentication observation, recovery, and durable Core reporting.
It must first inspect existing APIs against its acceptance requirements.

- [ ] If existing APIs cannot establish completed authentication, expose the smallest versioned signal/query in the image. Bind it to the exact connection, UUID, leaf SHA-256, approval revision, and time. Support recovery without requiring a CoT message or HTTP application transaction.

`ConnectionInfo` receives peer metadata before authentication and has no authentication-status field.
TLS success or connection presence alone cannot establish activation.
Keep activation semantics, callsign handling, and observer tests in the integration workstream.

### 6. Complete standalone operation, CI, and cleanup

- [ ] Provide Kind/existing-cluster standalone overlays and a narrow legacy-authentication admin bootstrap Job without Core, RMAPI, integration CRDs, `tak-operator`, or sibling checkouts. Do not add standalone fingerprint approvals.
- [x] Add a local Taskfile using the pinned `opendefence/base` Kind task. In the disposable standalone cluster, generate passwords through ESO, create the CNPG/PostGIS database and managed runtime role, issue JKS identities through cert-manager, deploy with Zarf, and require an authenticated HTTPS smoke check. Production issuer/retention/adoption remain open; strict-mode acceptance belongs to integrated deployment.
- [ ] Expose appropriate CoT/federation TCP services and preserve TAK `/Marti` mTLS semantics separately from `/integrations/tak/api/v1`.
- [ ] Verify the [standalone administrator and enrollment procedure](../k8s/README.md#standalone-administrators-and-user-enrollment) with a fresh personal administrator certificate and a separate ordinary user. Prove browser access, user group permissions, client import, and persistence after restart. Keep password-based automatic enrollment outside the supported contract until its issuer and endpoint are configured and tested.
- [ ] Finish native replacement checks after removing Compose deployment, obsolete OSS build, RM bootstrap, duplicate user/ZIP wrappers, and Azure/DevSpace paths. Retain `build_compose.yml` for distribution builds, optional pinned APK/update content, and historical LFS data.
- [ ] Provide coordinated backup/restore for database, XML, file-auth, trust, content, and identities. Uninstall must retain data. Integration separately excludes live grants from restore.
- [ ] Finish [CI migration](ci-migration.md): pinned actions, PR-tagged images tested by published digest, `arc-runner-set`, native AMD64/ARM64 BuildKit with `/etc/buildkit/tls/{ca.crt,tls.crt,tls.key}`, and disposable Kubernetes validation of the exact candidate.
- [x] Configure main to publish the runtime image to `ghcr.io/opendefence/tak-server` for AMD64/ARM64, verify the published digest, and build, sign, and publish both Zarf flavors to `ghcr.io/opendefence/zarf/tak-server`. Live runner/deployment acceptance and offline deployment of those packages remain open; see [CI migration](ci-migration.md).

#### Federation setup and restart acceptance

Test two independent TAK servers with separate databases, storage, identities, and trust roots.
Configure federation through the administrator REST API on HTTPS 8443.
Use the same API as the web UI. Do not seed peer configuration by editing XML for this test.
The pinned `5.8-RELEASE-92` WAR contains these routes in `Marti/federation/js/services.js`:
`/Marti/api/federationconfig`, `/Marti/api/federates`, `/Marti/api/federatedetails/{id}`,
`/Marti/api/federategroups/{id}`, `/Marti/api/outgoingconnections/{name}`, and `/Marti/api/activeconnections`.
The [native federation test](../tests/federation/README.md) uses these APIs against the pinned server.
It imports CA trust with `POST /Marti/api/federatecertificates` and a multipart `file` field.
It creates a version 2 outgoing connection with `POST /Marti/api/outgoingconnections`.
It assigns bidirectional group permissions with `POST /Marti/api/federategroups`.
The runner checks administrator access and denies ordinary-client settings reads and group updates.
It verifies cross-server CoT before and after each restart.
The test runs on demand. Its helper unit tests run in the existing CI test suite.

- [x] Confirm REST methods and request bodies for CA upload, outgoing connections, and group permissions against the pinned server. Use verified HTTPS and a distinct administrator identity on each server. Reject ordinary-client reads and group updates. Record requests in the test and sanitized state in `outputs/federation/result.json`.
- [x] Import peer trust through the supported API. Discover certificate peer identities. Assign group permissions and create an outgoing connection. Read them back through REST.
- [x] Prove bidirectional CoT delivery between clients on different native servers in a permitted group.
- [x] Record peer identities, outgoing connection settings, group permissions, and federation trust before restart. Restart config, messaging, and API containers separately. Then replace the complete server Pod. Repeat on both native peers. Keep each PVC and database. Require REST readback, unchanged trust, automatic reconnection, and fresh cross-peer traffic without repeating setup calls. The 2026-10-12 run passed all nine stages.
- [ ] Test explicit group mappings and reject traffic outside permitted groups. Confirm that the web UI shows the same state as REST. Repeat restart checks with these mappings.
- [ ] Check mission and file transfer for each enabled federation feature, including advertised HTTPS URLs and their required ports.
- [ ] Test trust changes while federation is active. During exploratory setup, a repeated CA upload caused `duplicate federation connection` and disabled the outgoing connection. The test runner reuses existing trust entries. Investigate live trust reload separately.
- [ ] Interrupt the network and restart the remote peer. Measure recovery against a declared timeout. Reject an untrusted peer and a non-administrator configuration request. Record failures as well as successful reconnects.
- [ ] Run the same setup, traffic, and persistence checks against a fully standalone remote TAK server. That peer must use an independent supported TAK distribution and its own CA, with no OpenDefence Core, `tak-operator`, Kubernetes, or Linkerd dependency. Test each direction as the connection initiator. Record both TAK versions and endpoint settings.

#### Future Linkerd experiment between two clusters

Use the federation test above as the application check for connecting two separate OpenDefence deployments.
This experiment is an open future item. It does not replace direct standalone interoperability.
Follow the pinned Linkerd version's [multicluster guidance](https://linkerd.io/2-edge/tasks/multicluster/).
Service mirroring supplies local Service addresses for a remote cluster through its gateway.
Do not assume that one cluster can route directly to the other cluster's ClusterIP.

- [ ] Connect two test clusters with Linkerd multicluster gateways and the required mesh trust. Export only the TAK federation endpoints needed by the test. Keep the two TAK peers distinct. Do not export Ignite, PostgreSQL, or the full stack by default.
- [ ] Configure outgoing federation with the mirrored Service DNS names and internal ports. Verify DNS, gateway reachability, network policy, and return traffic. Check every advertised mission/file URL as well as the federation socket.
- [ ] Add an isolated test overlay for the required proxy configuration. The current TAK base explicitly disables Linkerd injection. Preserve TAK TLS and certificate checks through the mesh. Keep mesh trust separate from TAK federation trust. Use [opaque TCP ports](https://linkerd.io/2-edge/features/protocol-detection/) where required by the selected Linkerd version.
- [ ] Repeat REST setup, group isolation, traffic, container restart, and Pod replacement checks through the mirrored endpoints. Restart a gateway and interrupt the cluster link. Prove recovery without changing peer settings or replacing truststores.
- [ ] Record the remaining requirements for connecting two complete OpenDefence stacks. A passing TAK federation test establishes only the tested TAK paths.

### 7. Retire fragile distribution scripts and legacy wrappers

The user requested this cleanup on 2026-10-10. Implement it after the CoT investigation and replacement checks pass.
Remove the six named scripts from supported workflows and image packaging. Do not replace them with renamed shell wrappers.

| Retire | Current consumers | Replacement |
| --- | --- | --- |
| `scripts/makeCert.sh` and copied `data/certs/makeCert.sh` | Source helper and Compose initializer removed; old PVC copies may remain | Native identities use issuer-managed or supplied JKS and coherent password Secrets. Import existing certificates without changing fingerprints; do not execute stale PVC copies. |
| `scripts/delete_user.sh`, `disable_admin.sh`, `enable_admin.sh`, `enable_user.sh` | Removed from source and image; old README examples replaced | The native bootstrap Job uses `user-manager.sh` for initial admin registration. Integrated role management and strict complete-set projection belong to `tak-operator`; required image interfaces are in slice 4. Standalone user/admin management acceptance remains open. Never revoke one leaf by deleting its account or demote an administrator by deleting and recreating the user. |
| `scripts/make_client_zip.sh` | Removed with `templates/missionpkg`, `pwgen`, and runtime `zip` | Integrated issuance/export and client packages belong to Core and `integration-tak`. Standalone package import from externally issued credentials remains an acceptance check. |
| Vendor `makeRootCa.sh`, `cert-metadata.sh`, and copied certificate helper files | Legacy initializer removed; the vendor distribution still bundles these helpers | Use native identity inputs and the schema Job. Keep signing keys outside ordinary server Pods. Preserve existing trust and identities on adoption; do not copy executable certificate helpers into the PVC. |
| Vendor `make-connection-package.sh`, `revokeCert.sh`, and `generateClusterCerts*.sh` | Bundled in the pinned distribution and copied to `data/certs`; no direct repository caller found | Use the owning integration's package export, explicit approval removal plus PKI revocation, and issuer-managed cluster identities. Check external callers before removing the files from supported images or PVC initialization. |
| Vendor `/opt/tak/enable_admin.sh` | Bundled second admin entrypoint; no direct repository caller found | Use the verified standalone management/bootstrap interface above. Exclude this entrypoint from supported workflows. |
| Vendor `setenv.sh` | No maintained runtime caller; the image test compares its pinned JVM options | Pinned image JVM/IGNITE options and launcher heap defaults replace its values. Remove the bundled script and update the parity test when the distribution-script audit is complete. Keep vendor JAR/WAR bytes unchanged. |
| Downloaded `wait-for-it.sh` | Removed from image with its only caller, the Compose initializer | Native schema Jobs have bounded database checks and server startup uses a bounded messaging-listener wait. |
| Vendor database setup, `upgrade-db.sh`, clear, archive, and restore scripts | Bundled in the pinned distribution; no maintained Compose initializer remains | Use the versioned schema Job and the coordinated backup/restore procedure in slice 6. Never run a vendor clear or restore script against adopted data. Verify no supported caller before image cleanup. |

- [ ] Audit direct calls, sourced files, transitive vendor helpers, image entrypoints, and copy operations against the pinned distribution. Include optional plugin/retention roles, schema tooling, tests, CI, README, AGENTS, and integration consumers. Record each remaining dependency and its replacement before removal.
- [ ] Reuse `user_manager.py` and existing launchers only where their binary interface meets the required contract. The maintained `user-manager.sh` no longer sources `setenv.sh`, but the integrated strict writer belongs to `tak-operator`; required image interfaces are in slice 4.
- [ ] Update supported commands, fixtures, tests, image copies, environment variables, and dependencies together. Retain historical reports as evidence. Stop executing stale helper copies on existing PVCs; never wipe a PVC to remove scripts.
- [ ] Prove fresh and repeated standalone bootstrap, identity import/renewal, user enable/disable, and admin promotion/demotion while preserving administrator federation trust. Prove single-leaf approval removal, preserved UUID/groups/other approved leaves, and client package import in the integrated workflow.
- [ ] Require an image/caller check that supported startup, management, migration, and package workflows do not execute these scripts. Repeat binary compatibility checks for each TAK release before removing the last fallback.

## T3 acceptance and T4 fixes

T3 uses `gpt-6-astra` / `high`; T4 uses `gpt-6.1-sol` / `high`.
Escalate unexplained runtime/design behavior through T1 `gpt-6-astra` / `xhigh` with a reproduction.
Use the final image, base, external extension/configuration, and vendor/management JAR tuple together. Preserve sanitized inputs, checksums, assertions, outcomes, and limits.
Integration owns the strict admission, projection, session, and authentication-evidence acceptance below.
This server plan retains those shared release gates for image consumers.
Standalone acceptance uses legacy certificate authentication.

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
| Federation | REST setup and readback, bidirectional traffic, group isolation, persistent peer settings and trust, and automatic recovery after individual container restarts and complete Pod replacement. Repeat against a fully standalone remote TAK distribution. Track the two-cluster Linkerd experiment separately. |
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

## LDAP interval binary compatibility follow-up

- [x] For `5.8-RELEASE-92`, inspect the direct consumers and their downstream timing paths. [Release-92 evidence](release-92-candidate.md) establishes seconds in both; restore the default to `60`. The second practical test was inconclusive.
- [ ] Whenever the TAK Server binary version changes, inspect the actual bytecode of every `updateinterval` consumer and its downstream scheduler/comparison before retaining `60`.
