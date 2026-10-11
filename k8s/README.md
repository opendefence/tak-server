# Native Kubernetes candidate

This base runs TAK 5.8.92 as config, messaging, and API containers in one singleton StatefulSet.
The image includes the external plugin launcher. The base does not enable plugin manager or retention.
Standalone uses legacy TAK certificate authentication and does not require
OpenDefence Core User semantics or fingerprint approval projection.
Strict authentication is reserved for integrated deployments and remains under implementation.
Selecting `TAK_AUTH_MODE=strict` installs the pinned admission agent in messaging and API.
Its approval state starts empty, so client access and the current probe readiness fail
until a trusted projection is implemented. Do not use this candidate as a strict-authentication release.

## Local standalone test cluster

With Docker or Podman running and [mise](https://mise.jdx.dev/) installed, bring up an isolated Kind cluster using the pinned [OpenDefence base cluster task](https://github.com/opendefence/base/blob/b04ff076bc4d3ec6a2ce01074a66f10d0f09b7a6/taskfiles/cluster.yaml):

```sh
mise install
mise exec -- task --yes up
mise exec -- task --yes status
mise exec -- task --yes smoke
```

`up` creates `tak-server-local` and writes its kubeconfig to `outputs/local/kubeconfig`.
It installs the OpenDefence base package and a local CA, generates retained runtime/JKS password Secrets with External Secrets Operator, starts CNPG/PostGIS, issues JKS identities with cert-manager, builds and loads the current image, then deploys the standalone Zarf components. The final smoke check requires a ready StatefulSet and HTTP 200 from an authenticated `/Marti` read.
The local `task tak` restarts the whole server Pod after Zarf applies so repeated runs pick up changed ConfigMaps and a rebuilt image with the same local tag.
The local Zarf deployment uses a ClusterIP Service because Kind has no load balancer; the normal standalone package defaults to LoadBalancer. Use `kubectl --kubeconfig outputs/local/kubeconfig -n tak-server port-forward svc/tak-server 8443:8443` for local access. The test CA and admin probe identity are for this disposable cluster only.
`mise exec -- task --yes down` deletes that cluster, including its database and identities. It does not target other Kind clusters.

## Required inputs

Supply a same-namespace CloudNativePG Cluster named `tak-database`, bootstrapped
with the TAK database and owner. Its generated `tak-database-app` Secret supplies
the host, database name, and migration account to the schema Job; the server uses
its host and database name.
Install PostGIS and pgcrypto in that database.
Apply the separate schema and grants Jobs before the server base.
Give the CNPG application owner rights to create and alter TAK tables.
Keep the runtime account separate and manage it through CNPG role management.
CNPG generates the [application Secret](https://cloudnative-pg.io/docs/1.30/applications/),
but a separate runtime role needs a `kubernetes.io/basic-auth` password Secret
from the installation's Secret generator; [CNPG consumes that Secret and
reconciles the role](https://cloudnative-pg.io/docs/1.30/declarative_role_management/).
The grants Job gives the runtime account data access after the schema Job completes.

| Secret | Required keys | Purpose |
| --- | --- | --- |
| `tak-database-app` | `host`, `dbname`, `username`, `password` | CNPG-generated schema connection and server endpoint. |
| `tak-database-runtime` | `username`, `password` | Generated basic-auth Secret consumed by the CNPG-managed runtime role. |
| `tak-store-passwords` | `cot-password`, `https-password`, `trust-password` | Installation-generated passwords matching the supplied stores. |
| `tak-cot-identity` | `keystore.jks` | RSA CoT/JWT private-key entry. |
| `tak-https-identity` | `keystore.jks`, `ca.crt` | Separate HTTPS identity and public outbound CA bundle. |
| `tak-client-trust` | `truststore.jks` | CoT client trust. |
| `tak-federation-bootstrap` | `truststore.jks` | Initial federation trust, used only when persistent trust is absent. |
| `tak-probe-identity` | `tls.crt`, `tls.key`, `ca.crt` | Client certificate, unencrypted client key, and HTTPS server CA bundle for authenticated probes. |

Use issuer-managed or supplied native JKS stores. The tested cert-manager private-key alias is `certificate`.
Match `TAK_SERVER_ADDRESS` to the served HTTPS certificate's DNS name.
The probe certificate must be trusted for client authentication. The bootstrap Job registers it as an administrator through UserManager.
This is the standalone legacy bootstrap path; it does not populate strict approvals.
The probe identity has administrator access; restrict Secret access to the installation owner.
The Job mounts only its public certificate. Application containers mount its client key for the authenticated read.
Ordinary Pods do not mount issuer CA signing keys.

The client and federation truststores use `trust-password`. Preserve that password while retaining an existing federation store.
An unrelated client trust root must not replace administrator-managed federation trust.
Keep CoT and HTTPS identities separate. Do not widen client trust with public Java roots.

## Zarf packages

The repository root [`zarf.yaml`](../zarf.yaml) packages both native overlays and
the schema/grants Jobs as `standalone` and `integrated` flavors. Use Zarf's lowercase filename.
Build with a published, pinned TAK image digest; each package includes that image
for offline deployment.

The main workflow publishes the Dockerfile's `run` image to
`ghcr.io/opendefence/tak-server` for `linux/amd64` and `linux/arm64` after checks pass.
It tests the published digest, lints both Zarf flavors, then builds and signs
packages for AMD64 and ARM64 using GitHub OIDC, following the `base` publishing
workflow. Packages are published to `ghcr.io/opendefence/zarf/tak-server` with
`VERSION-standalone`, `VERSION-integrated`, `latest-standalone`, and
`latest-integrated` tags. `VERSION` is the repository version with `+` replaced by
`-`; each flavor tag contains both architectures. The workflow summary lists
the image digest and package references. Use references from successful runs.
The packages retain the `5.8.92-candidate` metadata version.

After preparing the deployment prerequisites below, deploy a published package:

```sh
zarf package deploy oci://ghcr.io/opendefence/zarf/tak-server:latest-standalone --architecture amd64
```

Use `latest-integrated` for the integrated flavor and `--architecture arm64` for
ARM64. To select a release, use the versioned flavor tag from the
workflow summary. To build a package locally, use the image digest from a
successful run of the same commit as the package sources:

```sh
zarf dev lint . --flavor standalone --set TAK_IMAGE=ghcr.io/opendefence/tak-server@sha256:<published-digest>
zarf package create . --flavor standalone --set TAK_IMAGE=ghcr.io/opendefence/tak-server@sha256:<published-digest>
zarf package deploy zarf-package-tak-server-*.tar.zst
```

For the integrated flavor, use `--flavor integrated` at creation. Apply the sibling
`integration-tak` deployment first; it owns that namespace. The integrated Zarf
package installs TAK resources there and does not install the `tak-operator`.
For standalone Zarf deployment, create namespace `tak-server` and install its
CNPG Cluster and identity/credential Secrets before deploying the package.

Zarf prompts for `TAK_SERVER_ADDRESS`. PostgreSQL host, database, and migration
credentials come from the CNPG-generated `tak-database-app` Secret. The separate
runtime role must be managed by CNPG, using the installation-generated
`tak-database-runtime` password Secret. Zarf does not prompt for or copy
database credentials. The identity provisioning workflow must generate
`tak-store-passwords` alongside the JKS identities so the passwords match;
Zarf does not prompt for or regenerate them.
Pool/cache sizes, JVM heap limits, and `JAVA_TOOL_OPTIONS` are also Zarf parameters
with the tested base defaults. Internal mount paths, the Ignite discovery Service,
and legacy authentication mode are fixed by this candidate. Compose-only CA
generation, admin certificate, and mission-package environment variables are not
used by the native deployment.
`LDAP_UPDATE_INTERVAL` is a Zarf parameter in seconds when LDAP is configured.
The pinned 5.8.92 bytecode converts the value to milliseconds for CoT X.509
re-authentication and schedules LDAP authentication with `TimeUnit.SECONDS`.
The default is `60`; recheck both paths when the vendor binary changes.
The template also sets `MissionStrictUidMissionMembership=false` for new installs.
Existing administrator XML with an explicit value keeps that choice; a missing
value is filled with `false` during the next configuration merge.
`TAK_SERVICE_TYPE` defaults to `LoadBalancer`; the local Kind task sets `ClusterIP`.

Before deployment, supply the five identity/trust Secrets listed above and the
matching store-password Secret in the target namespace (`tak-server` or
`integration-tak`). The same namespace must contain the CNPG Cluster, its
generated application Secret, and the separate runtime role/Secret. Generate
each Secret once and preserve it across Zarf redeployments; changing a store
password without reissuing its JKS prevents startup. Check the schema Job result
and its migration history before treating the server as ready.
Zarf waits for the schema and grants Jobs, then deploys the server. It does not generate a
CA, sign certificates, provision CNPG, or alter existing PVCs. The package marks
its PVC for retention when Zarf removes the generated Helm releases. A database
switch or TAK release
upgrade needs a reviewed new schema Job name; a completed Job is not rerun.
After changing ConfigMap or password inputs on an installed system, coordinate
a whole-Pod replacement so every TAK role reads the same generation.

Update `zarf.yaml` and `k8s/zarf/` whenever a native overlay adds or changes a
configurable input, Secret key, image, workload, or namespace. Render and inspect
the resulting package before release; Zarf's Kustomize build happens at package
creation, while values are substituted at deployment.

## Install

Build the image with the repository Dockerfile. Override `JAVA_RUNTIME_IMAGE` and `JAVA_BUILD_IMAGE` with pinned images.
Pin the candidate image from `ghcr.io/opendefence/tak-server` by digest in an overlay before applying it.
The Kind overlay selects the local `localhost/tak-server:release-92` test image and disables pulls.
Load that image into the intended Kind cluster before applying the overlay.

Create a local overlay that consumes `k8s/base`, `k8s/overlays/standalone`, or `k8s/overlays/integrated`.
Set its namespace, image digest, storage size/class, and advertised DNS name.
Merge `tak-settings` with `configMapGenerator` and `behavior: merge`.
Keep passwords and rendered XML out of ConfigMaps.

The integrated overlay targets the `integration-tak` namespace created by the sibling
`integration-tak/k8s/integration` deployment. It does not create or own that namespace.
Its TAK resources, CNPG Cluster/database/identity Secrets, schema Job, and PVC must all be placed
there by the installer. The overlay allows the `tak-operator` Pod (labelled
`app: integration-tak-operator`) to reach Ignite; it does not deploy the
`tak-operator` or grant it TAK Secret access.
The sibling API and `tak-operator` manifests are managed in their own repository.
For strict-mode REST access, the `tak-operator` creates `tak-integration-admin` with its public `tls.crt`, uses a certificate chaining to TAK's client truststore, and registers that certificate as a TAK administrator through JNI. The integrated overlay projects this optional Secret into the API container only. Until it is present, strict HTTP admission denies the integration certificate. Replacing the Secret changes the exact pinned leaf without a server restart; the new leaf must also be registered through JNI. This path does not bypass TAK's REST authorization.
This is the TAK integration's installed identity, not a separate approval. General installed-integration identities for 8443 or 8089 require the Core IntegrationManifest identity and certificate-status contract; they are not yet accepted by this overlay.
The integrated overlay is still a legacy-authentication candidate until strict
admission and the management contract pass their acceptance checks.

Create separate local overlays for `k8s/schema` and `k8s/grants`.
Set the same namespace and image as the server overlay (`integration-tak` for the integrated deployment).
Apply and wait for both versioned Jobs before starting the server:

```sh
TAK_NAMESPACE=tak-server # use integration-tak for the integrated overlay
kubectl apply -k path/to/schema-overlay
kubectl -n "$TAK_NAMESPACE" wait --for=condition=complete job/tak-schema-5-8-92 --timeout=900s
kubectl apply -k path/to/grants-overlay
kubectl -n "$TAK_NAMESPACE" wait --for=condition=complete job/tak-grants-5-8-92 --timeout=180s
```

The Job uses Flyway and the migrations bundled in the pinned `SchemaManager.jar`.
The small `SchemaUpgrade` launcher never calls the vendor `repair` path.
It rejects a changed migration checksum and leaves the history row unchanged.
Flyway uses a PostgreSQL advisory lock during migration.
The versioned Job stays complete after success; a new release needs a new Job name.
On an empty database, the Job installs the schema without `takdb_base.sql`.
The legacy dump remains as an upgrade fixture; it is not used for fresh installs.
Back up the database before any upgrade.
Inspect the Job logs and schema history before starting the server.
An existing database without Flyway history needs a separate reviewed migration.
The repository's legacy SQL dump has V7 and V9 checksum mismatches with this release.
The Job rejects it until an administrator reviews and reconciles those exact history rows.
The disposable dump upgrade passed after that step. A new Job also resumed after the first Job stopped at a blocked V98 migration.
A production data upgrade and other interruption modes still need tests.

The grants Job connects as the CNPG application owner. It grants existing-table
and sequence access to the runtime role, sets default privileges for later
migrations, and removes runtime write access to `schema_version`. It uses the
runtime username from its Secret and quotes it as a PostgreSQL identifier.
The runtime role must not own the schema, have `CREATE` on it, or inherit
`schema_version` write access through another role.
The disposable test runtime role could read a TAK table and could not create a table.

The standalone overlay creates namespace `tak-server` and a TCP LoadBalancer Service.
It requires the CNPG Cluster and Secrets above. It has no Core, RMAPI, `tak-operator`, or sibling-checkout dependency.
The Kind overlay uses ClusterIP services; use port forwarding for local traffic tests.

```sh
kubectl apply -k path/to/local-overlay
kubectl -n "$TAK_NAMESPACE" wait --for=condition=complete job/tak-admin-bootstrap --timeout=180s
kubectl -n "$TAK_NAMESPACE" rollout status statefulset/tak-server --timeout=300s
```

The headless discovery Service publishes the server Pod before application readiness.
The bootstrap Job can therefore reach messaging while probes still await administrator registration.
Services select only server Pods; they exclude bootstrap Pods.
The bootstrap Job has a 180-second deadline and two retries. Probe operations have a four-second process timeout.
Readiness checks the local JVM, live config ownership, and an authenticated API request that reads the messaging user-management service.
The API launcher waits for the messaging CoT listener before JVM startup; it exits after 180 seconds if messaging has not opened it, allowing Kubernetes to retry.
It does not establish direct configuration RPC health or plugin callback health.
Readiness checks every 15 seconds and fails on the first failed operation.
Startup allows 60 attempts at five-second intervals. Liveness restarts each affected role after six failed checks at 15-second intervals.
These probes share the authenticated RPC check. A messaging stall can restart config and API as well as messaging.
Recovery can therefore involve several roles. Kubernetes reports probe failures and container restart counts.
Do not treat these thresholds as a service restoration guarantee; scheduling, termination, and startup add time.
Use `scripts/restart-kubernetes.sh namespace` for coordinated Pod replacement. It reports failure after a 300-second rollout wait.

The base permits CoT, HTTPS, and federation ingress. It restricts Ignite ingress to same-namespace TAK-labelled Pods.
The integrated overlay also permits the `tak-operator` Pod to reach Ignite. The base does not restrict egress.
Kind policy objects are not evidence of enforcement by a production CNI.
Expose extra administrator-created listeners through additional Service and NetworkPolicy entries.
Keep `/Marti` TLS client authentication intact when adding external routing.

## State and replacement

`tak-data` persists the authoritative CoreConfig, messaging file-auth, logs, and existing certificate/federation state.
Config owns `/opt/tak/data/CoreConfig_config.xml`. Its root XML and `.backup` links resolve to the PVC.
The external server launcher sets `LocalConfiguration.CONFIG_FILE` to the actual role file before starting the unchanged server.
This makes Java create `.backup` beside the real file; a backup symlink alone is replaced by the vendor copy routine.
TAK cluster mode is rejected because it selects another storage path. Kubernetes does not require that mode.
Followers use private runtime CoreConfigs. API and other followers use private file-auth directories.
Messaging and config resolve `/opt/tak/auth` to `/opt/tak/data/auth`.
Messaging owns live persistent file-auth updates. API control updates can save its private copy and backup.

At first adoption, validate and copy legacy `/opt/tak/data/UserAuthenticationFile.xml` into `data/auth`.
Retain the legacy file and backup with restricted modes. Subsequent startup prefers the new authority.
The retained legacy file is no longer updated. Do not restore an older image against it without a controlled state conversion.
Preserve the PVC and identities. Stop the previous server controller before applying the singleton StatefulSet against its claim.
Match the claim's existing size and storage class in the adoption overlay.
Keep the lifetime config lock; RWO does not enforce exclusive ownership.

The startup merge follows `coreconfig.MANAGED` and replaces deployment-owned LDAP configuration.
Administrator-owned peers, groups, policy, and additional listeners remain in persistent XML.
An admin edit to a deployment-owned attribute is replaced at the next controlled startup merge.
Java XML publication still has the truncation risk described in reports 004 and 005. Private files and persistent backups do not make it atomic.

Coordinate changes to identity files and matching password Secrets. Replace the whole server Pod after the generation is ready.
Verify the served certificate and authenticated traffic after replacement. Live reload and certificate renewal acceptance are unfinished.
An isolated [T2 check](../docs/t2-standalone-renewal.md) renewed HTTPS with an unchanged password and CA through a coordinated Pod replacement.
It did not test automatic issuer renewal or a password change.
Back up database, XML, file-auth, trust, content, and identities together before upgrade or restore.
The base retains the existing data layout; mission/content/audit path inventory remains unfinished.

## Remove workloads

```sh
scripts/uninstall-kubernetes.sh tak-server
```

This removes labelled workloads and network/configuration resources. It retains PVCs, Secrets, database, and namespace.
Do not use `kubectl delete -k` as the default uninstall command: the base includes a PVC.
Local-path storage does not prove recovery after node or cluster loss.
