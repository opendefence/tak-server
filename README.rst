==========
TAK Server
==========

This repository packages the pinned TAK Server 5.8.92 distribution for
OpenDefence Kubernetes. The vendor WAR and JAR files remain unchanged; external
launchers and a strict-authentication agent provide the server-side additions.
The current Zarf package has ``standalone`` and ``integrated`` flavors. The
integrated flavor deploys into the namespace owned by ``integration-tak``.

Local standalone cluster
========================

With Docker or Podman running::

    mise install
    mise exec -- task --yes up
    mise exec -- task --yes status
    mise exec -- task --yes smoke

The Taskfile creates a disposable Kind cluster, installs the OpenDefence base package,
CNPG/PostGIS, generated password Secrets and cert-manager JKS identities, then
deploys TAK through Zarf. ``smoke`` requires a ready server and authenticated
HTTPS 200. ``mise exec -- task --yes down`` deletes only this test cluster and
its data. See `k8s/README.md <k8s/README.md>`_ for deployment inputs, identity
rotation, storage, and existing-cluster installation.

The standalone bootstrap Job registers the supplied probe certificate as a TAK
administrator through UserManager. Supply the client identity, trusted issuer,
and matching JKS password Secrets as described in the Kubernetes guide. Keep
administrator changes and federation trust on the persistent volume; do not
delete the volume to renew certificates.
Standalone uses TAK's legacy certificate authentication and does not project
fingerprint approvals because it has no OpenDefence Core User authority.

Client certificate issuance and package export for the integrated deployment
belong to `integration-tak <https://github.com/opendefence/integration-tak>`_.
This image does not create client ZIPs or provide user/admin account wrappers.
Strict fingerprint mode for integrated deployments is under implementation;
the current Zarf overlays select legacy authentication. See `docs/implementation-plan.md
<docs/implementation-plan.md>`_ for its remaining acceptance gates.

Build and checks
================

Build the candidate image with ``podman build -t localhost/tak-server:local .``
(or the equivalent Docker command). The local ``task up`` builds and loads it
into Kind. Pull-request CI validates the same disposable native deployment.

The Python and image checks are documented in `k8s/README.md <k8s/README.md>`_.
The pinned strict-agent check is ``sh tests/test-strict-agent.sh IMAGE``.
Publishing remains disabled until the acceptance gates in the implementation
plan pass.
