# CI migration

Workflow callers now pin checkout, uv, prek, and shared CI actions to commit IDs.
The shared publishing action derives the registry owner from `GITHUB_REPOSITORY_OWNER`.
In this repository, it targets `ghcr.io/opendefence/tak-server`.
Docker Hub and ACR inputs are omitted.
PR checks do not publish images.

Main publishing requires the repository variable `TAK_PUBLISH_ENABLED=true`.
Leave it unset during migration.
Before enabling it, complete these checks:

1. Verify the `arc-runner-set` runner.
2. Verify its `/etc/buildkit/tls/{ca.crt,tls.crt,tls.key}` files and both native BuildKit endpoints.
3. Validate the disposable Kind deployment on the ARC runner.
4. Require tests of the exact published image on main.
5. Complete the required live acceptance evidence.

The pinned publishing action checks the ARC runner name and TLS file presence.
Live BuildKit access has not been tested from this session.
PR validation now builds the image directly, runs image checks, and uses the
native Taskfile to deploy into a disposable Kind cluster. Runner execution is
still unverified; the same Taskfile passed locally.
No Snyk job was added.
No workflow, image, or release was published from this session.
