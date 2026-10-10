# T1 runtime findings

T1 runtime decisions are complete after the [shared-Pod follow-up](t1-single-pod-findings.md).
The user selected co-location, which supersedes the original separate-Pod constraint.
The earlier separate-Pod observations below remain valid. Their application-patch proposal is not the selected implementation path.
The user confirmed `gpt-6-astra` / `xhigh` with `Switched; resume T1`.
This is user confirmation, not runtime metadata verification.
All observations below are from 2026-10-10.
Individual TAK defects now have [bug reports with handoffs and sanitized evidence](../bugreports/README.md).
The index distinguishes reproduced failures from findings that still need fault-injection tests.

## Tested candidate

The experiment uses the [T0 runtime](t0-foundation.md) and selected PR #136 scripts.
It does not cherry-pick the PR's older `5.8-RELEASE-69` distribution selection.
No production code or TAK binary was changed during this experiment.

| Item | Value |
| --- | --- |
| TAK | `5.8-RELEASE-84`, hardened, ARM64 |
| Java / image Python | Temurin `17.0.20.1+1` / Python `3.12.3` |
| PR revision | `025355ba9f76bf6c41187897f4a5fcac93b82afb` |
| Experimental image | `localhost/tak-server:t1-5.8.84-pr136` |
| Image manifest | `sha256:a3c022ec0806378523ed86dc9949599fb3b5331cf4deb78293dd4ee9efd9fffe` |
| Image configuration | `sha256:e08d276f2329b78a5e6f308674a3af14331fa8b384cc471c76fb20968544f13b` |
| `UserManager.jar` SHA-256 | `4ad7adcb9a09156d7122bfb2d4ddf3fd6705fb612f4d521335a5e08b449d24f6` |
| `takserver.war` SHA-256 | `64309513e45ba1e92084d457cd787b35d1c570ab918a11fd1ce1e5bdd4d6f26c` |
| Kind context / namespace | `kind-tak-server-t0` / `tak-server-t1` |
| cert-manager / CloudNativePG | `v1.21.2` / `v1.30.0` |
| Database image | `ghcr.io/cloudnative-pg/postgis:15.19-3.6.4-202608311017-standard-trixie@sha256:5c28ebba3202ff027da64bafeabb2a48983cbfec2f74ce1b36c9e635f35da763` |

The image overlays the PR's startup, Ignite, healthcheck, Java trust, and UserManager adapters.
The CoreConfig merge, identity, and standalone modules remain from imported main.
All 27 unit tests passed inside the experimental image.
The image was saved and explicitly loaded into the owned Kind cluster.

Config, messaging, and API ran in separate Pods, each with one service container.
Each role used its Pod IP and a private runtime volume.
Discovery used a headless Service with `publishNotReadyAddresses`.
The shared data PVC used local-path storage and same-node affinity.
TAK cluster mode was not enabled.
These storage and CNI choices do not prove node reattachment or NetworkPolicy enforcement.

## Blocking administrator persistence failure

Two actual administrator API writes returned HTTP 200:

1. `POST /Marti/api/outgoingconnections` added the disabled peer `t1_persistence_peer`, at `127.0.0.1:19001`.
2. `PUT /Marti/api/federationconfig` changed `missionFederationDisruptionToleranceRecencySeconds` from `43200` to `43201`.

Subsequent GET requests returned both edits.
The canonical file `/opt/tak/data/CoreConfig_config.xml` contained neither edit.
Its SHA-256 remained `a8236875ea677b9b871617c39eea8964502f8abb266603f476006f7c1297af55`.
After messaging replacement and config/API restarts, the peer was absent and the timing value was `43200` again.
This is a reproduced data-loss defect, not a failed input validation or a template merge result.
The test used the API consumed by the administration UI; no browser interaction was performed.

The selected binary explains the result:

- `IgniteHolder.areTakserverIgnitesLocal()` compares the messaging and API node address sets. Different Pod IPs make it false when both roles are present.
- `DistributedConfiguration.saveChanges()` saves only for TAK cluster mode, or for a config profile when that address comparison is true.
- With separate Pods and cluster mode disabled, administrator changes update memory and the distributed cache but skip the file save.
- `CoreConfigFacade` delegates administrator mutations to the distributed configuration service. An external whole-file watcher would not fix this ownership contract safely.

The compatibility link `/opt/tak/CoreConfig.xml` resolved to the canonical PVC file.
`/opt/tak/conf/CoreConfig.xml` did not exist in this test.
The canonical XML had mode `0600`.
The loss is therefore not explained by a broken compatibility link.
Direct bytecode review confirms that the guard bypasses the save call when cluster mode and the locality condition are false.
The before/after hashes do not exclude an additional overwrite race in the shared-file experiment.
Repeat with private follower files and process-level write traces before finalizing the patch scope. See [001](../bugreports/001-coreconfig-admin-edits-lost/HANDOFF.md).

## Actual Java writers

Inspection used the exact recorded JAR and WAR, with `javap` and CFR `0.152`.
Decompiled material remains in ignored local evidence. It is not included in Git.

| Code path | Observed behavior and consequence |
| --- | --- |
| `LocalConfiguration` constructor | Prefers an existing `conf/CoreConfig.xml`. TAK cluster mode also changes to that path. Defaults, QoS migration, and version upgrades can call `saveChanges()` during initialization. |
| `LocalConfiguration.saveChanges()` | Uses an in-JVM monitor and calls `JAXBUtils`. It does not honor the wrapper's configuration-owner file lock. |
| `DistributedConfiguration.saveChanges()` | Uses the address comparison described above. A config wrapper lock does not change its decision. |
| `JAXBUtils.saveJAXifiedObject()` | Marshals to memory, copies the old file to `<path>.backup`, then opens `FileOutputStream` on the destination. It follows the symlink and truncates the target. It does not atomically replace the file. |
| `FileAuthenticator.init()` in API | Fetches file-auth state from the messaging service and writes the configured file path. API startup is another writer when that path is shared. |
| `FileAuthenticator.saveChanges()` | Sends the file-auth control message, then writes the configured auth file with `JAXBUtils`. Save exceptions can be logged only at debug level and suppressed. |

The JVM backup `/opt/tak/CoreConfig.xml.backup` was a regular file in the container layer.
It did not resolve through the canonical XML symlink into the PVC.
The wrapper's atomic merge and persistent backup remain useful, but do not make Java saves atomic or persistent backups complete.

File-auth used `/opt/tak/data/UserAuthenticationFile.xml`.
All three registered identities survived the tested messaging/config/API replacements.
The auth file and its backup had mode `0644`; this must be tightened for credentials and hashes.
The experiment does not establish safety under concurrent writers or interruption during a save.
Persistent XML, file-auth, and federation trust must remain authoritative state.
Other application content paths still need the full inventory required by the handoff.

Historical review found that commit `d7682ca` replaced per-role CoreConfig paths with the shared authority.
Follower startup writes are not an upstream ownership defect when they target private files.
Report [003](../bugreports/003-multiple-xml-writers/HANDOFF.md) is reclassified as a deployment-specific risk.
Only the config-service CoreConfig needs persistence; followers need private bootstrap files and runtime configuration from Ignite.
Validate direct local reads before discarding any bootstrap values.
File-auth storage must be isolated separately because its path comes from remote CoreConfig.

## Messaging replacement and recovery

The original messaging Pod used `10.244.0.18`.
Deletion created a new Pod at `10.244.0.22`, at `15:39:50Z`.
Config and API retained their old processes and reported socket readiness.
The non-mutating request `GET /Marti/api/user-management/api/list-users` returned HTTP 500.
The API log records `IgniteClientDisconnectedException` from the remote `getUserList` call.
The new messaging process did not finish startup until config was restarted.
The failure remained observable 54 seconds after replacement.

The recovery experiment used `Recreate` deployments:

1. Restart the single configuration deployment.
2. Wait for configuration readiness, then request an API restart.
3. Confirm that messaging finishes startup and the new API becomes ready.
4. Verify the authenticated remote user-list request and real CoT exchange.

The recovery sequence started at `15:40:44Z`.
Config became ready at `15:41:22Z`, messaging at `15:41:27Z`, and API at `15:42:10Z`.
Remote reads and bidirectional authenticated CoT were verified by `15:43:01Z`, 137 seconds after recovery started.
All three test identities remained usable.
The accepted administrator XML edits were lost as described above.

This is one manual recovery observation, not a production recovery bound.
The authenticated API read detects a failure that socket checks miss.
It does not yet supply a minimal production probe or prove recovery of a separate JNI client.
The automatic detector, retry limit, escalation path, and repeated recovery tests remain unfinished.

## Native JKS and identity separation

cert-manager issued a test CA and separate CoT, HTTPS, administrator, and client identities.
Ordinary TAK Pods did not mount the CA signing key.
The experiment copied native JKS output without conversion.

Both JKS stores contained `certificate` as a `PrivateKeyEntry` and `ca` as a trusted certificate entry.
The private-key chain length was one, with the issuing root stored separately.
This test used direct root issuance; intermediate-CA chains remain untested.
The CoT private key was RSA 2048. The HTTPS private key was ECDSA P-256.
Keytool accepted the passwords and stores. TAK started with both identities.
HTTPS clients verified the expected DNS name against the test CA.
Two authenticated clients exchanged CoT in both directions before and after recovery.

`POST /Marti/api/generateFederationJwtToken` generated an RS256 token.
OpenSSL verified its signature against the CoT certificate's public key.
This proves that the tested federation JWT path uses the separate RSA identity.
It does not test every JWT endpoint or a real federation peer.

The first test password included a trailing newline.
Changing the password Secret alone left already-issued stores using the previous password during the initial test.
Reissuing the unused test identities produced matching stores and successful startup.
The final adapter must activate a coherent identity and password generation.
This experiment does not establish renewal activation or federation-trust preservation across renewal.

## Historical separate-Pod patch proposal

This proposal preceded the user's shared-Pod decision. No application patch was authorized or made.
Separate Pods cannot pass administrator persistence with the tested save condition.
Enabling TAK cluster mode would change paths and writer behavior. It is not an accepted workaround.

For continued separate-Pod research, restore private follower CoreConfigs and isolate file-auth storage by role.
Repeat the admin edit with write tracing. File separation does not change the verified save guard, but it removes a possible competing writer.
Startup writes to private files do not require an application patch.

The remaining proposed application work must use matching TAK source:

1. Make the configuration service the persistent CoreConfig writer independently of messaging/API address equality. Keep administrator saves synchronous with that owner.
2. Make persistent XML publication atomic and propagate save failures from the persistent owner. Keep restrictive permissions and a persistent backup. The misplaced backup can also be corrected by mount/link layout.
3. Change startup or file-auth ownership in TAK only if role-specific file storage cannot enforce the required separation. Messaging owns persistent file-auth; API may write its private copy.

Do not globally change `areTakserverIgnitesLocal()`, enable cluster mode, or add a whole-file synchronization watcher.
The patch must be limited to the supported separate-process mode and preserve offline tool behavior.
Rerun the reproduced admin saves, startup upgrades, competing-owner checks, and interrupted saves before accepting it.
Then finish recovery detection and the separate JNI-client tests on the resulting runtime tuple.

Matching source or a vendor-fixed distribution is needed.
The public `TAK-Product-Center/Server` repository returned no `5.8*` tags when queried.
This does not establish whether matching source is available through another authorized channel.
The existing source-build Dockerfile targets an older release and is not a validated 5.8 build path.
The later shared-Pod and private-file experiments passed the tested administrator saves with the original binaries.
Their observations and remaining publication risks are recorded in the [follow-up](t1-single-pod-findings.md).

## Evidence and remaining work

Local evidence is retained under ignored `outputs/t1/`:

- `context/`, `candidate-unit-tests.log`, `candidate-image-id.txt`: candidate inputs and image results.
- `inputs.json`, `initialize.json`, `workloads.json`, `bootstrap.json`: experimental Kubernetes resources. Initialization is a test fixture, not the final migration contract.
- `config-before.txt`, `config-after.txt`, `before-restart-*.json`, `recovered-*.json`: accepted edits, unchanged authority, and lost edits after restart.
- `messaging-before.json`, `messaging-after.json`, `api-after-replacement.log`, `recovery-*.txt`: replacement and recovery evidence.
- `native-jks-details.txt`, `initialize-complete.log`, `check-cot.py`: store inspection and client test.
- `binary/`, `decompiled/`: exact local binary inspection material.

These are local reproduction artifacts, not a portable test package.
Some contain credentials or tokens. Keep them out of commits.
The owned cluster, namespace, data PVC, database, and completed Jobs remain for investigation.
Unrelated clusters and containers were not changed. Nothing was pushed or published.

T1 can hand off the selected runtime to T2. The migration plan is still missing; its location was requested.
The follow-up verifies a separate JNI read client and plugin launcher startup/replacement.
Renewal, supported upgrade, restore, concurrent migration, retention, third-party plugins, real federation, offline operation, and production NetworkPolicy checks remain unverified.
Do not promote this candidate or enable image publication.
