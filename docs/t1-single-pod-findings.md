# T1 shared-Pod follow-up

The user selected multiple containers in one Pod after reviewing the separate-Pod failures.
This instruction supersedes the original implementation handoff's separate-Pod constraint.
T1 now selects one server Pod, private follower CoreConfigs, and the supplied plugin launcher.
No TAK binary was modified. T2 must turn the tested fixtures into supported packaging.

## Topology control

The first comparison changed only Pod grouping and Service selectors.
It retained the [recorded image](t1-runtime-findings.md), scripts, shared-file mapping, database, identities, and PVC.
Config, messaging, and API used private runtime volumes and one Pod IP.
The old separate Deployments remain scaled to zero for rollback.
A private archive of the data directory was taken before the change. This was not a database backup or restore test.

The admin API accepted the disabled peer `t1_singlepod_peer` at `127.0.0.1:19001` and recency value `43201`.
Both values reached `/opt/tak/data/CoreConfig_config.xml` and survived Pod replacement from `10.244.0.25` to `10.244.0.26`.
Authenticated user-list reads and bidirectional CoT passed within 41 seconds of the rollout request in this observation.
Restarting only messaging kept the Pod IP unchanged. Existing config and API containers stayed running.
Remote user reads and CoT passed within 33 seconds of that request.
See [selected evidence](../bugreports/001-coreconfig-admin-edits-lost/single-pod-evidence.json).

These results support the address-locality explanation for bug 001 and the shared Pod as the selected deployment model.
They do not repair separate-address saves or establish a production recovery bound.

## Private follower files

The next fixture copies the prepared canonical XML into each follower's private runtime directory before Java starts.
`/opt/tak/CoreConfig.xml` and `TAKCL_CORECONFIG_PATH` select that local copy.
Only config links its local CoreConfig to the persistent authority.
The fixture also adds plugin manager to the same Pod with the [verified launcher](../bugreports/006-pluginmanager-forces-localhost/HANDOFF.md).

All four roles started with peer `t1_singlepod_peer` and recency `43201`.
The API then accepted peer `t1_private_peer` at `127.0.0.1:19002` and recency `43202`.
The canonical XML changed. Messaging, API, and plugin bootstrap files kept their earlier hashes and values.
API reads returned the new values through the runtime configuration.
A first attempt to reuse port `19001` was rejected as an existing outgoing endpoint. The successful request used `19002`.

After full Pod replacement from `10.244.0.30` to `10.244.0.31`, both peers and `43202` remained in the authority and API.
Fresh follower copies contained the saved values. Authenticated CoT passed in both directions.
Plugin manager found all three remote APIs after startup and replacement.
See [private-file evidence](../bugreports/001-coreconfig-admin-edits-lost/private-files-evidence.json).

This proves the tested settings do not need live follower file updates.
It does not prove that every local read can use a minimal template. Seed private copies from validated saved state.
File-auth still uses the shared PVC path in this fixture. Isolate API's private auth file and backup directory separately in T2.
The existing persistent auth records survived, and the user-management service returned all three test identities.

## Separate JNI client

A disposable Python/PyJNIus process loaded the exact 5.8.84 `UserManager.jar` and a small Java read probe.
The JAR SHA-256 was `4ad7adcb9a09156d7122bfb2d4ddf3fd6705fb612f4d521335a5e08b449d24f6`.
The probe ran in a separate Pod at `10.244.0.29`. It mounted no server state or signing keys.
It advertised `tak-profile=t1-jni`, bound to its own Pod IP, and used `tak-ignite:47500` for discovery.
Every three seconds it obtained a non-sticky proxy to `distributed-user-file-manager` and called `getUserList()`.
Each successful call returned three users. This exercised a remote service, not a cached CoreConfig read.

The same Python process and JVM stayed running through two server Pod replacements.
It detected transient `ComputeTaskTimeoutException` and `IgniteClientDisconnectedException` failures.
Successful remote reads resumed after 18.574 seconds and 42.316 seconds from the respective rollout requests.
The client Pod had zero restarts. Ignite assigned a new client node ID after each reconnect.
The probe requests a 5-second service-proxy timeout, but failure detection and reconnect add latency; this is not a 5-second end-to-end bound.

Ignite explicitly warned that continuous queries and remote event listeners are removed after this reconnect path.
Any integration observer must restore subscriptions and reconcile current state after reconnect.
This read-only test does not validate an observer, integration reconciliation, or the real integration controller.
The old TAKCL and Kubernetes helper modes advertise `messaging`; the XML-aware helper uses a distinct client profile.
Require a distinct integration profile. Do not assume that every helper mode preserves the server's locality test.

The disposable client image is `localhost/tak-server:t1-jni-5.8.84` with manifest `sha256:1d4d3bad1679e6a5795ca2b6785be8372b367a50102442075c564d95e38ba62f`.
It reuses the local integration image's Python/PyJNIus environment and replaces only the probe inputs with the selected JAR.
It is a test artifact, not a published integration image.

## T2 decisions and release limits

- Use one server Pod with separate role containers and non-overlapping replacement. Keep the configuration-owner lifetime lock.
- Keep deployment inputs in ConfigMaps/Secrets and live authority on the PVC. Merge only managed attributes at config startup.
- Seed private follower CoreConfigs from the prepared authority. Do not add a configuration watcher or JNI force-save workaround.
- Keep the plugin launcher optional, compile it against the selected release, and preserve its private runtime directory.
- Use actual remote calls for recovery checks. `/proc/net/tcp` is shared by Pod containers, so another container can satisfy the existing socket probe.
- Implement a finite recovery deadline and failure reporting in T2, then test the automatic path in T3. The observations above are not an SLA.
- Preserve native JKS consumption and separate RSA CoT/JWT and HTTPS identities, as verified in the earlier T1 findings.

Java XML publication still truncates the live target, and file-auth save errors can be suppressed. Bugs 004 and 005 remain open.
Co-location does not fix crash durability, file permissions, misplaced backups, or shared file-auth writers.
T2 must restore the intended mount ownership and persistent backup layout without changing TAK classes.
T3 must test failure handling before release acceptance.
No supported upgrade, certificate renewal, restore, production CNI, offline install, or third-party plugin callback was established by this follow-up.
The companion migration plan remains an unresolved input. The supplied implementation handoff and later user instructions govern the recorded decisions.

Raw fixtures and logs remain under ignored `outputs/t1/singlepod/`, `outputs/t1/plugin-launcher/`, and `outputs/t1/jni/`.
They include private data and are not a portable installer.
The old report ZIP remains untracked and unchanged. No report or image was published.
