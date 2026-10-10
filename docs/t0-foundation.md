# T0 foundation

## Source import

The source is `pvarki/docker-atak-server`.
The imported main revision is `beaab168e70187dbdc4eadeca77d4939413df6b5`.
The import preserves 342 commits, 13 branches, and four tags.
PR #136 is preserved as `feat/container-ignite-networking` at `025355ba9f76bf6c41187897f4a5fcac93b82afb`.
No inherited history was rewritten.

`git lfs fetch --all upstream` reported 55 entries.
The complete Git object scan contains 54 unique historical LFS object hashes.
All 54 objects passed SHA-256 checks in the independent clone.
An independent local mirror retrieved Git and LFS data from this destination checkout.
Git integrity checks passed in both repositories.
The normalized LFS inventories match.
The independent mirror is `/private/tmp/tak-server-t0-destination.git`.
The historical pointer and hash results are in `outputs/t0/lfs-pointer-objects.txt` and `outputs/t0/lfs-all-pointer-hashes.log`.

The remote destination has no branches or tags.
No remote changes were made.
After authorized publication, verify a new remote clone with Git LFS.
Repository import does not transfer issues, PR discussions, releases, settings, secrets, or registry artifacts.
Transfer or recreate those items separately.
Do not use a mirror push after destination changes exist.

## Current runtime

| Item | Baseline |
| --- | --- |
| Architecture | `linux/arm64` |
| TAK | `5.8-RELEASE-84`, hardened distribution |
| Java | Temurin `17.0.20.1+1` |
| Image Python | `3.12.3` |
| Development Python | `3.12.14` |
| Scripts and Dockerfile | Source main revision above |
| Local image | `localhost/tak-server:baseline-5.8.84-beaab168` |
| Podman image manifest | `sha256:f0521e15dacfa1d03f5d9b46da3f236c2bfe8c01c89194ff491b403f39209bfa` |
| Image configuration | `sha256:385657961bec5f0ea3ae69e70380a530172831dfea04ddc4df94ec08973a6a48` |
| Distribution archive SHA-256 | `27461a0c79818f4d636aeaa7692e9c6122051ab4b40ef4f73333d59d39733fea` |
| `UserManager.jar` SHA-256 | `4ad7adcb9a09156d7122bfb2d4ddf3fd6705fb612f4d521335a5e08b449d24f6` |
| `SchemaManager.jar` SHA-256 | `7d1a1fe79c2023bdd3f01644609af4c77e5b6d7caf1cfcf3e813e62f3498e337` |
| `takserver.war` SHA-256 | `64309513e45ba1e92084d457cd787b35d1c570ab918a11fd1ce1e5bdd4d6f26c` |

The local supplied archive matches the archive in the published distribution image.
The distribution image reports digests `sha256:cd080d18e7c52e848fb99ff386856e9e3859dda1124714cad8260f86ab0878d5` and `sha256:ef7908347ed1e2313a937f12d6ecf89c32078ff6095038e2d13981c3c4352820`.
The Java base reports digests `sha256:8db3be29199466e2a3b6c862643bd336240d179c9cf7bd846a92b86eaa47bb69` and `sha256:900322f4cc1b9da9d730ae4bb56d8a1dabbaa9cfa32809fc8b542b600370a045`.
The imported Dockerfile still uses mutable dependency tags and downloads.
Use the recorded local image for this baseline.
T1 must select the supported tuple before T2 changes.
These checks do not establish JNI compatibility or live server acceptance.

## Behavior inventory

- `start_tak.py` holds a configuration-service file lock across JVM execution. Followers wait for a matching generation file.
- `coreconfig.py` merges owned attributes into `/opt/tak/data/CoreConfig_config.xml`. It validates the installed XSD. It publishes files atomically with restrictive permissions and a backup.
- The compatibility links use `/opt/tak/CoreConfig.xml` and `/opt/tak/data/CoreConfig.xml`. Actual JVM save paths and administrator saves need T1 tests.
- File authentication uses `/opt/tak/data/UserAuthenticationFile.xml`. Certificates, federation trust, and logs use `/opt/tak/data/certs` and `/opt/tak/data/logs`.
- Each startup links to one shared Ignite XML file. Main does not provide the separate-Pod configuration required by the handoff.
- Compose shares the config service network with other roles. Its probes return `true`. They do not prove remote Ignite operation.
- Standalone initialization creates a local CA. It uses `firstrun.done` for database upgrades. Replace both contracts only after T1 evidence.
- HTTPS uses a separate keystore. CoT and the JWT signer use the RSA identity. Federation trust initializes only when absent. Outbound Java trust has a separate derived store.
- Retention starts a long-running JAR. Plugin manager uses the inherited launcher. Their remote behavior needs T1 evidence.
- RASENMAEHER bootstrap, user wrappers, package generation, Compose, Azure, and DevSpace remain inherited code. Remove them in later verified slices.
- Mission, content, audit, and other write paths still need a binary-level inventory. The image is not declared read-only.

The inherited `AGENTS.md` describes older versions and volume deletion.
The implementation handoff takes precedence.
Do not delete persistent data for certificate renewal.

## Local validation

The dedicated cluster is `tak-server-t0`.
Its context is `kind-tak-server-t0`.
Its namespace is `tak-server-baseline`.
Kind `v0.33.0` uses node image `kindest/node:v1.35.8@sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0`.
The Kind binary passed its official checksum check.
The [Kind guide](https://kind.sigs.k8s.io/docs/user/quick-start/) documents release binaries and archive loading.
The kubeconfig is `outputs/t0/kubeconfig`.
The existing OpenDefence cluster was not changed.

```sh
podman build --pull=missing --target run -t localhost/tak-server:baseline-5.8.84-beaab168 .
podman run --rm --pull=never --network none -v "$PWD:/workspace:ro" --entrypoint /usr/bin/python3 localhost/tak-server:baseline-5.8.84-beaab168 -B -m unittest discover -s /workspace/tests -v
podman run --rm --pull=never --network none -v "$PWD:/workspace:ro" --entrypoint /bin/bash localhost/tak-server:baseline-5.8.84-beaab168 /workspace/tests/test-fed-truststore.sh
podman run --rm --pull=never --network none -v "$PWD:/workspace:ro" --entrypoint /bin/bash localhost/tak-server:baseline-5.8.84-beaab168 /workspace/tests/test-api-keystore.sh
podman save --format docker-archive -o outputs/t0/baseline-image.tar localhost/tak-server:baseline-5.8.84-beaab168
KIND_EXPERIMENTAL_PROVIDER=podman /private/tmp/tak-server-t0-tools/kind-darwin-arm64 load image-archive outputs/t0/baseline-image.tar --name tak-server-t0
uv lock --check
.venv/bin/python -m ruff check scripts tests
.venv/bin/python -m ruff format --check scripts tests
.venv/bin/python -m pyrefly check
```

All 19 unit tests passed in the candidate image.
Both shell checks passed.
Lock, lint, format, and type checks passed.
The Kind `runtime-smoke` Job passed Java, XSD presence, and `UserManager.jar` checksum checks.
Archive loading can change the manifest format and digest.
The Kind image identifier is recorded in `outputs/t0/kind-image-id.txt`.
Logs and the image archive are under ignored `outputs/t0/`.
Do not commit that directory.

No TAK service topology, administrator UI persistence, messaging recovery, live authentication, rotation, or restore result is claimed.
Kind uses local-path storage and a CNI that does not prove NetworkPolicy enforcement.

## Inputs and skills

The Core architecture handoff was read from `/Users/rambo/Downloads/rasenmaeher-core-architecture-handoff.md`.
The integration implementation handoff was read from the sibling checkout.
`tak-server-kubernetes-migration-plan.md` was not found.
Its location was requested from the user.

The user confirmed `gpt-6.1-sol` / `medium` with `Switched; resume T0`.
This is user confirmation, not runtime metadata verification.
The installed skills have no Git revision metadata.
Their file SHA-256 values identify the loaded copies:

| Skill | File SHA-256 |
| --- | --- |
| Ponytail, full | `1316a2f3f95741d2300b116fe0c2d81ce4a9568656ed0a62643f54aaf09957f2` |
| Caveman | `0bf09a0a9a017d004a81d4b693e5a2d830e1a28230a5885df773e1ed9c0571cc` |
| Ponytail review, plugin `5.1.0` | `33fe4ebe22a460924e5d4a261e223df22e409cc94ab76182bee9fb91a3ef022e` |
| Ponytail audit, plugin `5.1.0` | `2b3223a02c386d1263e1b08343cb8eb3a53e444cdafb1d79e26c8ec2a8fcad28` |

The upstream pins in the handoff are reference revisions.
The local copies are not claimed to match those revisions.
