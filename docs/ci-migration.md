# CI migration

Workflow callers now pin checkout, uv, prek, and shared CI actions to commit IDs.
The shared publishing action derives the registry owner from `GITHUB_REPOSITORY_OWNER`.
In this repository, it targets `ghcr.io/opendefence/tak-server`.
Docker Hub and ACR inputs are omitted.
PR checks do not publish images.

Every push to main publishes the Dockerfile's `run` target after the checks job
passes; `TAK_PUBLISH_ENABLED` is no longer required. The shared action uses native
AMD64/ARM64 BuildKit and publishes both platforms under the same image reference.
Main runs are serialized so a later run cannot move the release tag while the
current run resolves its digest.

The publishing job pulls that digest and runs the Python, strict-agent, vendor
launcher, federation truststore, and HTTPS keystore checks. It then lints both
Zarf flavors with the digest. The successful job exposes it as the `tak-image`
output and prints it in the workflow summary. Following the `base` repository's
publishing workflow, it creates both Zarf flavors for AMD64 and ARM64, signs each
archive with GitHub OIDC, and publishes to `ghcr.io/opendefence/zarf/tak-server`.
The Zarf path keeps package tags separate from the runtime image. Tags are
`VERSION-standalone`, `VERSION-integrated`, `latest-standalone`, and
`latest-integrated`; `VERSION` comes from `.bumpversion.toml` with `+` replaced by
`-`. Architectures publish sequentially into the same flavor tag's OCI index.
GHCR login is reused from the image publishing action; signing requires the
job's `id-token: write` permission.

Zarf package creation consumes the tested digest through `--set TAK_IMAGE=...`;
it does not build the server image. Failed checks or publishing steps fail the
workflow but do not remove artifacts already pushed to GHCR; use references
from successful runs. Package metadata still identifies this as the
`5.8.92-candidate` deployment.

Live runner and deployment acceptance still need these checks:

1. Verify the `arc-runner-set` runner.
2. Verify its `/etc/buildkit/tls/{ca.crt,tls.crt,tls.key}` files and both native BuildKit endpoints.
3. Validate the disposable Kind deployment on the ARC runner.
4. Complete the required live acceptance evidence, including the integrated
   deployment and offline deployment of the published packages.

The pinned publishing action checks the ARC runner name and TLS file presence.
Live BuildKit access has not been tested from this session.
PR validation now builds the image directly, runs image checks, and uses the
native Taskfile to deploy into a disposable Kind cluster. Runner execution is
still unverified; the same Taskfile passed locally.
No Snyk job was added.
No workflow, image, or release was published from this session.
