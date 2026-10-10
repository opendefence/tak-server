# Implementation status

- Stage: T0 local foundation complete. Paused before T1, `gpt-6-astra` / `xhigh`.
- Effective T0 model: `gpt-6.1-sol` / `medium`, confirmed by the user with `Switched; resume T0`. Runtime metadata is unavailable.
- Skills: Ponytail full, Caveman, Ponytail review, and Ponytail audit loaded. Local file hashes and provenance are in [T0 evidence](t0-foundation.md).
- Branch: `implementation/t0-foundation`. Imported main: `beaab168e70187dbdc4eadeca77d4939413df6b5`. Source branches, tags, and LFS data are preserved.
- Completed commits: `9f0669c1e5742f5fe2ff1ec05548a825bd01476a` records the baseline. HEAD contains `ci: gate OpenDefence image publishing` and this checkpoint. Resolve HEAD with `git rev-parse HEAD`.
- Checks: independent local Git/LFS clone, Git integrity, image build, 19 unit tests, federation and HTTPS shell tests, Kind smoke Job, lock, Ruff, and Pyrefly passed.
- Candidate: TAK `5.8-RELEASE-84`, Temurin `17.0.20.1+1`, image Python `3.12.3`, ARM64. Image manifest: `sha256:f0521e15dacfa1d03f5d9b46da3f236c2bfe8c01c89194ff491b403f39209bfa`.
- `UserManager.jar` SHA-256: `4ad7adcb9a09156d7122bfb2d4ddf3fd6705fb612f4d521335a5e08b449d24f6`. Full tuple and commands are in T0 evidence.
- Owned resources: Kind `tak-server-t0`, context `kind-tak-server-t0`, namespace `tak-server-baseline`, completed `runtime-smoke` Job, and local image `localhost/tak-server:baseline-5.8.84-beaab168`. Kubeconfig and logs are in ignored `outputs/t0/`.
- Inputs: Core architecture and integration handoffs were read. The migration plan is missing. Its location was requested.
- Remote publication: none. The remote destination is empty. Verify a fresh remote clone after authorized publication.
- CI: callers are pinned. PR jobs do not publish. Main publishing requires `TAK_PUBLISH_ENABLED=true` and uses GHCR. Workflow and documentation hooks passed. Ponytail review found no issues in either T0 commit. [CI limits](ci-migration.md) include untested live ARC/BuildKit access and pending Kubernetes validation.
- Unfinished files: only the supplied implementation handoff remains untracked and unchanged. `.idea/` is ignored by the inherited rules.
- Next action: confirm the T1 model gate and read the missing plan. Reconcile PR #136 with the recorded candidate. Reproduce messaging replacement and trace actual JVM configuration writes. No live acceptance result is claimed.
