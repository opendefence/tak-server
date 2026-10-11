# CI migration

Workflow callers now pin checkout, uv, prek, and shared CI actions to commit IDs.
The shared publishing action derives the registry owner from `GITHUB_REPOSITORY_OWNER`.
In this repository, it targets `ghcr.io/opendefence/tak-server`.
Docker Hub and ACR inputs are omitted.
After PR checks pass, same-repository PRs publish the
Dockerfile's `run` target for AMD64/ARM64 through the same shared action. It
generates `VERSION-prNUMBER` and `VERSION-prNUMBER-TIMESTAMP` tags, plus the PR
merge-ref tag, at `ghcr.io/opendefence/tak-server`; invalid version characters
such as `+` become `-`. An additional `pr-NUMBER-RUN_ID-ATTEMPT` tag lets the
publishing job resolve its own digest even when another PR run publishes at the
same time. PR builds do not move the vendor release tag or main's `latest` tag.
Fork PRs, Dependabot PRs, and manual validation runs skip the publishing job.
PRs do not publish Zarf packages.

`native_validations` consumes the publishing job's `tak-image` digest output,
pulls it from GHCR, and records the local platform image ID as `TAK_TEST_IMAGE`.
Both the image tests and disposable Kind deployment use that image. The native
Taskfile retags the supplied image ID for Kind instead of rebuilding it, and
fails if that image is missing. When publishing is skipped, native validation
builds locally once and follows the same tests and deployment path. A publishing
failure blocks native validation; it does not fall back to an unrelated build.
Published PR tags are candidates until native validation passes; a later test
failure does not remove them from GHCR. Runtime validation covers the runner's
architecture.

Docker's containerd image store can retain index entries for platforms that were
not pulled. Kind's import of all platforms then fails with a missing content
digest. The native task detects that store, saves only the tested image's
platform, and loads the temporary archive into Kind. It removes the archive on
success or failure. Podman and Docker's classic store keep their existing load
path. This follows [Kind's documented workaround](https://kind.sigs.k8s.io/docs/user/known-issues/#unable-to-kind-load-docker-images).

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

PR run [38141415603](https://github.com/opendefence/tak-server/actions/runs/38141415603)
passed checks and published both platforms through the shared BuildKit action.
Native validation pulled that digest and passed the image, strict-agent,
launcher, federation truststore, and HTTPS keystore checks on the ARC runner.
The standalone deployment stopped at Kind import with the missing-digest error.
On 2026-10-11, a disposable Docker 29.9 daemon with the containerd store reproduced
that error using the ARM64 pull of `alpine:3.22` at index
`sha256:5291449c3df73caf6ed85e649dec1b9e818b39a5d8c871e97afc13e9cd5e8fa8`.
The updated `task image` imported the platform archive into Kind 0.31.0;
CRI readback reported `linux/arm64`, and the task removed its temporary archive.
The test used a Docker CLI bridge to the disposable daemon and a Podman-backed
Kind node. The fixture image and daemon were removed after the check.
Regression tests cover AMD64/ARM64 selection, classic Docker and Podman paths,
export/import failures, and archive cleanup. This is import evidence, not a full
TAK deployment on the ARC runner.
The platform archive fix still needs a new ARC run after the user pushes it.
Integrated acceptance and offline deployment of published Zarf packages remain open.
No Snyk job was added.
No workflow, image, or release was published from this session.
