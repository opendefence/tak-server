# T2 native runtime and storage

T2 is active after the user's explicit `Switched; resume T2` confirmation.
The required setting is `gpt-6.1-sol` / `high`; runtime model metadata is unavailable.
This checkpoint packages the selected topology. It is not a strict-authentication release.

## Candidate

| Artifact | Value |
| --- | --- |
| Image | `localhost/tak-server:t2-layout-5.8.84` |
| Manifest | `sha256:cab586425fb9ddfd9952c99f9e2f87cb744cb491489547c4fcf2a91120764277` |
| Image configuration | `sha256:01c672c3e6f1dea2e485214de224d7a0e080dd425725fddae5ed4d2488ad1c8d` |
| TAK / Ignite | `5.8-RELEASE-84` / `2.18.0` |
| Runtime | Temurin `17.0.20.1+1`, Python `3.12.3`, ARM64 |
| Build JDK | `eclipse-temurin:17-jdk-noble@sha256:fb79620c3f6ee8f1c7530a8dc4fd49e3b410bcef037694ad4858a1553bac4170` |
| Unchanged WAR SHA-256 | `64309513e45ba1e92084d457cd787b35d1c570ab918a11fd1ce1e5bdd4d6f26c` |
| Unchanged UserManager SHA-256 | `4ad7adcb9a09156d7122bfb2d4ddf3fd6705fb612f4d521335a5e08b449d24f6` |

The image packages PR #136's per-process Ignite adapter, outbound trust helper, neutral UserManager wrapper, and external plugin launcher.
The source reference is `025355ba9f76bf6c41187897f4a5fcac93b82afb`.
The external server launcher selects the real local CoreConfig path before calling the unchanged TAK entry point.
The vendor WAR and management JAR remain unchanged. Build inputs other than the recorded JDK still need final provenance pins.

## Storage and native deployment

The uncommitted `k8s/base` uses a singleton StatefulSet with config, messaging, and API containers.
Each has a private runtime `emptyDir`. The config wrapper holds its lifetime lock across JVM startup.
The actual owner path remains `/opt/tak/data/CoreConfig_config.xml`.
Followers receive private startup copies and runtime configuration through Ignite.
Deployment inputs use hashed ConfigMaps and Secrets. The attribute-level ownership merger and installed XSD remain in use.
XML metacharacters in template inputs are escaped. Invalid saved state is preserved when startup fails.

Messaging file-auth is `/opt/tak/data/auth/UserAuthenticationFile.xml`.
API resolves the same logical `/opt/tak/auth` directory to its private runtime directory.
First adoption validates and copies legacy file-auth without overwriting a current authority.
Legacy files remain with mode `0600`, but no longer receive live updates. Older images require a controlled state conversion.

The init container validates federation trust and seeds it only when absent.
CoT/JWT, HTTPS, and client trust come from separate native JKS Secret mounts.
Passwords are purpose-specific. No issuer CA signing key is projected into ordinary Pods.
The finite admin bootstrap Job uses the remote UserManager interface and mounts only the public administrator certificate.
The Service selector excludes that Job from server endpoints.

The uncommitted `k8s/README.md` describes required database/Secret inputs and preservation rules.
The standalone and Kind overlays consume this base without Core or a sibling checkout.
A prepared database is still required; a native schema Job and complete fresh-install workflow remain unfinished.
The uninstall helper retains PVCs, identities, Secrets, database, and namespace.

## Backup correction

A real admin save returned HTTP 200 and updated the persistent owner XML.
TAK's `FileUtils.copyFile` replaced the root `.backup` symlink with a regular container-layer file.
A Python write-through test did not reveal that Java behavior.

`ServerLauncher` sets the public `LocalConfiguration.CONFIG_FILE` field to the actual absolute role path before TAK initializes.
TAK then constructs its backup beside that file. The root paths remain compatibility links.
The vendor `setenv.sh` supplies its own `loader.path`; the launcher explicitly extends that JVM option.
A real-loader test rejects missing path input before server startup.
Startup rejects TAK cluster mode, which otherwise redirects saves to `conf/CoreConfig.xml`.

The corrected live save created the owner's backup on the PVC with mode `0600`.
Messaging and API private CoreConfigs retained their pre-edit values while the admin API returned the new value.
API file-auth and its backup resolved to private storage with a different inode from the persistent authority.
This corrects backup placement and file isolation. Java still truncates live XML during publication.
Report [004](../bugreports/004-unsafe-xml-publication/HANDOFF.md) remains open for interrupted-save behavior.
Report [005](../bugreports/005-fileauth-save-errors-hidden/HANDOFF.md) remains open for hidden save failures.

## Verification

The focused suite passed 24 tests in the candidate's Python 3.12 runtime using its actual XSD, gomplate, Java, and OpenSSL.
Ruff and Pyrefly passed. Shell syntax, the HTTPS selector test, and the real vendor-loader test passed.
Base and Kind Kustomize rendering passed. Server dry-run passed against the owned test namespace.

```sh
podman run --rm --pull=never --network none -v "$PWD:/workspace:ro" \
  -e PYTHONPATH=/workspace/tests --entrypoint /usr/bin/python3 \
  localhost/tak-server:t2-layout-5.8.84 -B -m unittest -v \
  test_coreconfig test_start_tak test_ignite_config test_java_truststore \
  test_healthcheck test_user_manager test_initialize_volume
podman run --rm --pull=never --network none -v "$PWD:/workspace:ro" \
  --entrypoint /bin/bash localhost/tak-server:t2-layout-5.8.84 \
  /workspace/tests/test-server-launcher.sh
```

The native StatefulSet reached 3/3 readiness using the existing T1 database, issued identities, and PVC.
The bootstrap Job completed on its second attempt while messaging became available.
Repeating bootstrap with the final image completed successfully.
A real federation edit changed recency to `43204`; the API readback and owner XML agreed.
Changing the managed database endpoint triggered a full Pod replacement and retained that admin value.
Persistent file-auth and federation trust hashes stayed unchanged. Fresh follower copies contained the saved value.

Suspending the messaging JVM caused readiness failure after 21 seconds.
Liveness restarted each role once; authenticated RPC readiness recovered after 198 seconds on the same Pod IP.
The admin value and persistent backup survived. These times describe one test, not a restoration guarantee.

## CoT regression and T1 gate

The post-recovery two-client CoT check failed with a receiving-client timeout.
Both client-side TLS handshakes completed with CA and hostname verification.
Sending distinct presence events from both clients did not make the exchange pass.
A clean, coordinated Pod replacement reached 3/3 readiness on new IP `10.244.0.44` with zero restarts, but the same exchange still timed out.
RPC readiness therefore does not establish successful CoT delivery in this candidate.
No cause is established. This may be a packaging regression or upstream runtime behavior; do not label it an upstream TAK bug yet.

The persistent file-auth still contained `admin`, `client-a`, and `client-b` with their existing `__ANON__` groups.
The saved authentication flags matched the pre-change archive: `x509groups=true`, `x509addAnonymous=false`.
This excludes an incidental change to those two flags. It does not establish completed TAK authentication or group routing.
The earlier T1 candidate passed CoT; its runnable fixture remains under `outputs/t1/`.

Reproduce against the retained test identities:

```sh
kubectl --kubeconfig outputs/t0/kubeconfig --context kind-tak-server-t0 \
  -n tak-server-t1 port-forward statefulset/tak-server 38089:8089
# In another terminal, use the configured project Python interpreter:
.venv/bin/python tests/check-cot.py --cert-dir outputs/t1/client \
  --server-name tak-messaging.tak-server-t1.svc.cluster.local --port 38089
```

Expected: each client receives the other client's unique CoT event.
Observed: `TimeoutError: The read operation timed out` on the first receiving read.
The check uses distinct presence and exchange identifiers; a presence event cannot satisfy its expected identifier.
The private keys are fixture inputs, not committed test data.
Saved failure: `outputs/t2/fresh-pod-cot-check.log`; earlier failures and RPC recovery output are also under `outputs/t2/`.

The supplied handoff requires escalation of new unresolved runtime/design behavior through T1 `gpt-6-astra` / `xhigh`.
T2 is held at that gate. Preserve the uncommitted runtime/base work until this regression is understood.
Do not promote the image or mark the native runtime slice complete from RPC readiness alone.

Owned scope: Kind `tak-server-t0`, context `kind-tak-server-t0`, namespace `tak-server-t1`.
The old `tak-colocated` Deployment and separate role Deployments remain scaled to zero.
No PVC or identity was deleted. The unrelated development cluster was not changed.
Ignored evidence is under `outputs/t2/`: build/load logs, focused test output, live layout checks, and managed replacement checks.
The private pre-change data archive has mode `0600`. Raw XML, credentials, identities, logs, and kubeconfig are not committed.

## Remaining acceptance

CoT delivery is a known failed check. Strict admission, trusted projection/readback, session enforcement, and completed-authentication evidence are not wired into TAK.
Strict startup fails before touching persistent storage. The base selects legacy mode explicitly.
Direct configuration-service RPC health, observer restoration, plugin callbacks, schema concurrency/upgrade, renewal, restore, offline operation, production CNI enforcement, movable storage, and AMD64 remain unverified.
Mission/content/audit write-path inventory and removal of the old Compose/RM paths remain planned.
