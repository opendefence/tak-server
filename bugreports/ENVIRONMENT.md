# Shared T1 environment

These reports describe the test performed on 2026-10-10.
Packaging the evidence did not rerun or modify the application.

| Item | Tested value |
| --- | --- |
| TAK | `5.8-RELEASE-84`, hardened, `linux/arm64` |
| Java / image Python | Temurin `17.0.20.1+1` / Python `3.12.3` |
| Imported packaging revision | `beaab168e70187dbdc4eadeca77d4939413df6b5` |
| PR #136 adapter revision | `025355ba9f76bf6c41187897f4a5fcac93b82afb` |
| Experimental image | `localhost/tak-server:t1-5.8.84-pr136` |
| Image manifest | `sha256:a3c022ec0806378523ed86dc9949599fb3b5331cf4deb78293dd4ee9efd9fffe` |
| Image configuration | `sha256:e08d276f2329b78a5e6f308674a3af14331fa8b384cc471c76fb20968544f13b` |
| `UserManager.jar` SHA-256 | `4ad7adcb9a09156d7122bfb2d4ddf3fd6705fb612f4d521335a5e08b449d24f6` |
| `takserver.war` SHA-256 | `64309513e45ba1e92084d457cd787b35d1c570ab918a11fd1ce1e5bdd4d6f26c` |
| Kind / Kubernetes | `v0.33.0` / `v1.35.8` |
| Context / namespace | `kind-tak-server-t0` / `tak-server-t1` |
| cert-manager / CloudNativePG | `v1.21.2` / `v1.30.0` |
| Database image | `ghcr.io/cloudnative-pg/postgis:15.19-3.6.4-202608311017-standard-trixie@sha256:5c28ebba3202ff027da64bafeabb2a48983cbfec2f74ce1b36c9e635f35da763` |

The candidate overlays PR startup, Ignite, healthcheck, Java trust, and UserManager adapters on the T0 image.
The TAK binaries remain unchanged. The older release selected by the full PR was not adopted.
The adapter tests passed: 27 tests inside the candidate image.

## Preconditions for reproduction

- Run config, messaging, and API as separate Pods, each with one service container and a different Pod IP.
- Use the Downward API for Ignite binding and private runtime volumes for Ignite configuration and work files.
- Use the headless discovery Service `tak-ignite:47500`, with `publishNotReadyAddresses` enabled.
- Keep TAK cluster mode disabled. Kubernetes separation does not require TAK cluster mode.
- Mount the same RWO data PVC in the three roles. The experiment used local-path storage and same-node affinity.
- Preserve `/opt/tak/data/CoreConfig_config.xml` as authority. `/opt/tak/CoreConfig.xml` resolves to that file. `conf/CoreConfig.xml` is absent.
- Configure file-auth at `/opt/tak/data/UserAuthenticationFile.xml` and persistent federation trust under `/opt/tak/data/certs/files/`.
- Use native cert-manager JKS identities: RSA 2048 for CoT/JWT and ECDSA P-256 for HTTPS. Use coherent store passwords.
- Register an administrator and two client certificates through remote UserManager. Do not mount the CA signing key in TAK Pods.
- Verify an authenticated admin API read and bidirectional CoT before fault tests. Use a disposable namespace and data set.

The HTTPS API base was `https://takserver.tak-server-t1.svc.cluster.local:8443/Marti/api`.
Host tests used local port forwards with hostname and CA verification.
Socket-based PR readiness was retained to compare against actual remote calls; it is not sufficient acceptance evidence.

## Evidence sources

The original [T1 findings](../docs/t1-runtime-findings.md) were committed as `8ec035124c165c263606a8fd54734874de628154`.
Raw material remains in ignored `outputs/t1/` in the originating checkout.
The image context and fixtures are `context/`, `inputs.json`, `initialize.json`, `workloads.json`, and `bootstrap.json`.
These local fixtures are not a portable installer or a production migration contract.
The kubeconfig is `outputs/t0/kubeconfig`.

Each `evidence.json` contains selected fields or inspection notes and names its local source artifacts.
[SOURCE-SHA256SUMS](SOURCE-SHA256SUMS) records their SHA-256 checksums in standard checksum-file format.
From the originating repository root, verify them with `shasum -a 256 -c bugreports/SOURCE-SHA256SUMS`.
Source hashes establish provenance; they do not distribute the source artifacts.
HTTP response files contain bodies only. Status codes and some shell observations were captured in the T1 session and summarized in its committed findings.
Those observations are labeled separately from fields extracted from files.
Binary inspection used `javap` and CFR `0.152`; committed reports contain paraphrases, not decompiled source.

Matching source or a fixed vendor distribution is still needed for application changes.
The public source repository returned no `5.8*` tags during T1. Other authorized source channels were not ruled out.
These reports do not establish behavior in another TAK release, architecture, CNI, or storage driver.
