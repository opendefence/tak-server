# Federation acceptance tests

These tests use two native TAK servers in one disposable test cluster.
Each server has its own database, volume, CA, and client identities.
Federation uses the internal Service address on TCP 9001.
Linkerd injection stays disabled.

## Run the test

Start the [local test cluster](../../k8s/README.md#local-standalone-test-cluster).
Load the image under test into that cluster.
The commands below use the local task's image tag.

```sh
mise exec -- tests/federation/setup.sh outputs/local/kubeconfig localhost/tak-server:local
mise exec -- uv run --frozen python tests/federation/check.py --kubeconfig outputs/local/kubeconfig
```

The setup script requires cert-manager, CloudNativePG, and External Secrets Operator.
It reuses the native manifests and schema Jobs.
It creates `tak-federation-a` and `tak-federation-b`.
Both scripts refuse existing namespaces without the `opendefence.io/test=federation` label.
Use these namespaces only for this test.
Do not run two copies of the test at the same time.
Keep the host awake until the runner exits.

The runner imports each peer's CA through `/Marti/api/federatecertificates`.
It creates one outgoing connection from A to B.
It assigns `federation-test` as a bidirectional group on both peers.
The ordinary client on each server belongs to that group.
All REST calls use certificate authentication and verified HTTPS.
The runner also requires HTTP 403 for an ordinary client's settings read and group update.

The runner sends fresh CoT events in both directions.
It then restarts config, messaging, and API separately on each server.
It also replaces each complete server Pod.
The containers must become ready within 300 seconds after each restart.
The federation connection must then become active within 90 seconds.
Each stage must preserve the truststore bytes, trusted CA fingerprints, peer identity,
group permissions, and outgoing connection settings.
Each stage must deliver fresh CoT events in both directions.
The runner does not repeat setup calls between restart stages.

## Results and retained state

Read `outputs/federation/result.json` for completed stages and state assertions.
A successful run sets `complete` to `true`.
A failed run exits nonzero and leaves `complete` set to `false`.
The output directory also contains private client keys and administrator credentials.
It is ignored by Git. Keep it private.

The test retains both namespaces and their data.
Rerun the check to test the retained configuration.
The setup script can reuse its fixtures. Use a tagged image reference.
After changing the image or identity Secrets, replace the complete server Pods before testing.
Do not delete PVCs to renew certificates.

To remove the fixture resources from the disposable local cluster, run:

```sh
mise exec -- kubectl --kubeconfig outputs/local/kubeconfig delete namespace tak-federation-a tak-federation-b
```

This deletes the test databases and volumes.
It does not remove the exported credentials in `outputs/federation`.

## Remaining acceptance checks

The 2026-10-12 ARM64 Kind run passed all nine stages with TAK `5.8-RELEASE-92`.
It used local image `sha256:99c3ca82e4ec246aa926ed330b869751f63a0d5aa361912e4b9669efce03bc04`.
Container restart stages took 6–23 seconds. Pod replacement stages took 37–94 seconds.
Both peers retained their federation truststore bytes, peer identity, group permissions,
and outgoing settings. Fresh CoT events crossed both directions at every stage.

The test exposed two identity requirements that the local certificate manifests now meet.
The CoT identity needs client authentication usage and an issuer certificate in its TLS chain.
TAK rejected server-only usage. A leaf-only chain caused `Index 1 out of bounds for length 1`.
The pinned `TakFigClient` bytecode reads certificate chain entry 1 without a length check.

An exploratory upload of an already trusted CA caused `duplicate federation connection`
and disabled the outgoing connection. The runner skips duplicate trust uploads.
Live trust reload needs a separate test and investigation.

This first test covers direct federation between two copies of this native image.
It does not prove interoperability with an independent standalone TAK distribution.
The [implementation plan](../../docs/implementation-plan.md#federation-setup-and-restart-acceptance)
keeps that remote test open.
Group isolation, mission and file transfer, network interruption, untrusted peers,
and Linkerd multicluster tests also remain open.
