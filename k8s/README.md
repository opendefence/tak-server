# Native Kubernetes candidate

This base runs TAK 5.8.84 as config, messaging, and API containers in one singleton StatefulSet.
The image includes the external plugin launcher. The base does not enable plugin manager or retention.
The candidate supports explicit legacy authentication. Strict authentication remains under implementation.
Selecting `TAK_AUTH_MODE=strict` stops startup until that injection exists. Do not use this candidate as a strict-authentication release.

## Required inputs

Supply a PostgreSQL database with PostGIS and pgcrypto installed.
Apply the separate schema Job before the server base.
Give the migration account the rights to create and alter TAK tables.
Keep the runtime account separate.
Grant the runtime account data access after the schema Job completes.

| Secret | Required keys | Purpose |
| --- | --- | --- |
| `tak-database-migration` | `username`, `password` | Schema Job database access. |
| `tak-database-runtime` | `username`, `password` | Application database access. |
| `tak-store-passwords` | `cot-password`, `https-password`, `trust-password` | Passwords matching the supplied stores. |
| `tak-cot-identity` | `keystore.jks` | RSA CoT/JWT private-key entry. |
| `tak-https-identity` | `keystore.jks`, `ca.crt` | Separate HTTPS identity and public outbound CA bundle. |
| `tak-client-trust` | `truststore.jks` | CoT client trust. |
| `tak-federation-bootstrap` | `truststore.jks` | Initial federation trust, used only when persistent trust is absent. |
| `tak-probe-identity` | `tls.crt`, `tls.key`, `ca.crt` | Client certificate, unencrypted client key, and HTTPS server CA bundle for authenticated probes. |

Use issuer-managed or supplied native JKS stores. The tested cert-manager private-key alias is `certificate`.
Match `TAK_SERVER_ADDRESS` to the served HTTPS certificate's DNS name.
The probe certificate must be trusted for client authentication. The bootstrap Job registers it as an administrator through UserManager.
This is the legacy standalone bootstrap path. It is not an implicit strict-mode exception.
The probe identity has administrator access; restrict Secret access to the installation owner.
The Job mounts only its public certificate. Application containers mount its client key for the authenticated read.
Ordinary Pods do not mount issuer CA signing keys.

The client and federation truststores use `trust-password`. Preserve that password while retaining an existing federation store.
An unrelated client trust root must not replace administrator-managed federation trust.
Keep CoT and HTTPS identities separate. Do not widen client trust with public Java roots.

## Install

Build the image with the repository Dockerfile. Override `JAVA_RUNTIME_IMAGE` and `JAVA_BUILD_IMAGE` with pinned images.
Pin the candidate image in an overlay before applying it. A publishing destination is not yet enabled.
The Kind overlay selects the local `localhost/tak-server:t2-layout-5.8.84` test image and disables pulls.
Load that image into the intended Kind cluster before applying the overlay.

Create a local overlay that consumes `k8s/base`, `k8s/overlays/standalone`, or `k8s/overlays/integrated`.
Set its namespace, image digest, storage size/class, advertised DNS name, and database address/name.
Merge `tak-settings` with `configMapGenerator` and `behavior: merge`.
Keep passwords and rendered XML out of ConfigMaps.

The integrated overlay targets the `integration-tak` namespace created by the sibling
`integration-tak/k8s/integration` deployment. It does not create or own that namespace.
Its TAK resources, database/identity Secrets, schema Job, and PVC must all be placed
there by the installer. The overlay allows the sibling's `app: integration-tak-operator`
Pod to reach Ignite; it does not deploy the operator or grant it TAK Secret access.
The sibling API and operator manifests are managed in their own repository.
The integrated overlay is still a legacy-authentication candidate until strict
admission and the management contract pass their acceptance checks.

Create a separate local overlay for `k8s/schema`.
Set the same namespace and image as the server overlay (`integration-tak` for the integrated deployment).
Merge `tak-schema-settings` with the database address and name.
Apply and wait for the versioned Job before starting the server:

```sh
TAK_NAMESPACE=tak-server # use integration-tak for the integrated overlay
kubectl apply -k path/to/schema-overlay
kubectl -n "$TAK_NAMESPACE" wait --for=condition=complete job/tak-schema-5-8-84 --timeout=900s
```

The Job uses Flyway and the migrations bundled in the pinned `SchemaManager.jar`.
The small `SchemaUpgrade` launcher never calls the vendor `repair` path.
It rejects a changed migration checksum and leaves the history row unchanged.
Flyway uses a PostgreSQL advisory lock during migration.
The versioned Job stays complete after success; a new release needs a new Job name.
On an empty database, the Job installs the schema without `takdb_base.sql`.
The old Compose initializer still uses that file, so keep it until Compose retirement.
Back up the database before any upgrade.
Inspect the Job logs and schema history before starting the server.
An existing database without Flyway history needs a separate reviewed migration.
The repository's legacy SQL dump has V7 and V9 checksum mismatches with this release.
The Job rejects it until an operator reviews and reconciles those exact history rows.
The disposable dump upgrade passed after that step. A new Job also resumed after the first Job stopped at a blocked V98 migration.
A production data upgrade and other interruption modes still need tests.

Run these grants as a database administrator after the Job completes.
Replace `cot`, `tak_migration`, and `tak_runtime` with the actual database and role names.
Use the migration account as the owner of the new TAK tables.

```sql
GRANT CONNECT ON DATABASE cot TO tak_runtime;
GRANT USAGE ON SCHEMA public TO tak_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tak_runtime;
REVOKE INSERT, UPDATE, DELETE ON TABLE public.schema_version FROM tak_runtime;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO tak_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE tak_migration IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tak_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE tak_migration IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO tak_runtime;
```

The runtime role must not own the schema, have `CREATE` on it, or change `schema_version`.
The disposable test runtime role could read a TAK table and could not create a table.

The standalone overlay creates namespace `tak-server` and a TCP LoadBalancer Service.
It requires the database and Secrets above. It has no Core, RMAPI, integration operator, or sibling-checkout dependency.
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
It does not establish direct configuration RPC health or plugin callback health.
Readiness checks every 15 seconds and fails on the first failed operation.
Startup allows 60 attempts at five-second intervals. Liveness restarts each affected role after six failed checks at 15-second intervals.
These probes share the authenticated RPC check. A messaging stall can restart config and API as well as messaging.
Recovery can therefore involve several roles. Kubernetes reports probe failures and container restart counts.
Do not treat these thresholds as a service restoration guarantee; scheduling, termination, and startup add time.
Use `scripts/restart-kubernetes.sh namespace` for coordinated Pod replacement. It reports failure after a 300-second rollout wait.

The base permits CoT, HTTPS, and federation ingress. It restricts Ignite ingress to same-namespace TAK-labelled Pods.
The integrated overlay also permits the sibling's operator-labelled Pod to reach Ignite. The base does not restrict egress.
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
