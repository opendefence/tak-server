# AGENTS.md — tak-server

## Purpose

Package TAK Server 5.8 for OpenDefence. The TAK WAR and vendor JARs are pinned
binary inputs; server behavior changes use external launchers or extensions.
The native Kubernetes candidate runs config, messaging, and API in one singleton
StatefulSet. Strict fingerprint authentication is still under implementation.
Standalone uses legacy TAK certificate authentication; strict approval depends
on OpenDefence Core User authority and applies only to integrated deployments.
The `tak-operator` in sibling `integration-tak` owns that strict-authentication
work. Keep only required TAK image changes and binary compatibility checks here.
The integration's `docs/remaining-work-handoff.md` is the authoritative work list.

## Local development

```sh
mise install
mise exec -- task --yes up
mise exec -- task --yes status
mise exec -- task --yes smoke
```

This creates the disposable `tak-server-local` Kind cluster, with its kubeconfig
at `outputs/local/kubeconfig`. `mise exec -- task --yes down` deletes that cluster
and its test database and identities. See [k8s/README.md](k8s/README.md) for the
native deployment contract and [docs/implementation-plan.md](docs/implementation-plan.md)
for remaining work. `build_compose.yml` remains for distribution builds.

## Native architecture

- `k8s/base` owns the singleton StatefulSet, persistent TAK state, bootstrap Job,
  Services, and network policy. Config, messaging, and API share one Pod and
  Ignite network identity.
- `k8s/overlays/standalone` uses namespace `tak-server`.
  `k8s/overlays/integrated` targets `integration-tak`, created by the sibling
  integration manifests, and permits the `tak-operator` Pod to reach Ignite.
  Its current Kubernetes Deployment is named `integration-tak-operator`.
- CloudNativePG owns PostgreSQL and its generated application Secret. A separate
  CNPG-managed runtime role consumes a generated password Secret.
- cert-manager issues the local test JKS identities. Matching store passwords
  come from retained Kubernetes Secrets. Ordinary TAK Pods do not mount CA keys.
- `zarf.yaml` packages standalone and integrated flavors. Its schema and grants
  components wait for their Jobs to complete before installing the server.

CoT uses TCP 8089, HTTPS `/Marti` uses 8443, and federation uses 9000–9002.
The local Kind Service is ClusterIP; the ordinary standalone Service defaults to
LoadBalancer.

## Working rules

1. Keep `zarf.yaml` and `k8s/zarf/` aligned with native overlay inputs, Secrets,
   images, workloads, and namespaces. Lint both flavors after changes.
2. Preserve native Kubernetes identity and data state. Rotate matching identity
   and password Secrets together and replace the whole server Pod. Never delete
   the PVC to renew certificates. Administrator federation trust remains on it.
3. Keep vendor WAR/JAR bytes unchanged. Verify every external injection against
   the selected release. The candidate explicitly uses legacy authentication;
   selecting strict mode currently stops startup.
4. The integrated deployment belongs in the `integration-tak` namespace. The
   `tak-operator` and integration API live in the sibling repository; this repo
   does not install them or grant them TAK Secret access.
5. The user/admin wrappers, client-ZIP generator, Compose initializer, and
   `makeCert` have been removed. Do not add callers to distribution certificate
   helpers.
6. Name each operator explicitly in prose: `core-operator` (not present in this
   TAK deployment yet), `tak-operator` (currently `integration-tak-operator` in
   Kubernetes), `mediamtx-operator`, CloudNativePG operator, or External Secrets
   Operator. Avoid bare "operator" or "sibling operator" when a specific component
   is meant. Say "administrator" when referring to a person.
7. Run `prek install` in each checkout so the repository's basic pre-commit and
   commit-message checks run on local commits. Run `prek run --all-files`
   regularly, especially before pushing or creating/updating a PR when authorized
   to do so. Fix any failures before proceeding.
 8. Use the [`ponytail`](https://github.com/DietrichGebert/ponytail) skill for all coding work.
 9. Run `ponytail-audit` before every commit. Fix findings caused by the staged change before committing.
10. Write all documentation in Simplified Technical English (STE). Use short, active sentences and consistent terms. Give one instruction per sentence. Preserve exact commands and identifiers.



## Related repositories

- [OpenDefence base](https://github.com/opendefence/base): platform components and local cluster tasks.
- [OpenDefence core](https://github.com/opendefence/core): platform API, `core-operator`, and CRDs.
- [OpenDefence integration-tak](https://github.com/opendefence/integration-tak): TAK integration API, `tak-operator`, and client packages.
