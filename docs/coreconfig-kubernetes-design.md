# CoreConfig ownership in Kubernetes

Keep the live `CoreConfig.xml` as persistent application state on a PVC.
Use ConfigMaps and Secrets for deployment inputs.
Reuse `scripts/coreconfig.py` to merge those inputs into the saved state before the configuration service starts.
No new operator or synchronization sidecar is needed.

This records the T1 storage decision. It does not resolve the TAK Java persistence defects or complete T1.

## Ownership

| Data | Owner | Kubernetes storage |
| --- | --- | --- |
| Database endpoint, listener settings, authentication mode, identity paths | Deployment | ConfigMap inputs |
| Database credentials and identity passwords | Deployment | Secret inputs |
| Initial XML structure and defaults | Image | Existing `CoreConfig.tpl` |
| Saved XML, including administrator changes | Configuration service | PVC |
| File-auth records and administrator-managed federation trust | Application | Persistent storage |

The exact deployment-owned XML attributes are listed in `coreconfig.MANAGED`.
The merger also replaces the entire LDAP element from deployment inputs.
It preserves other saved settings, including peers, groups, policy, extra listeners, and federation truststore attributes.
If an administrator changes a deployment-owned attribute, the next startup merge restores the deployment value.
Expose this ownership rule in the deployment documentation.
An extra TAK listener still needs the corresponding Kubernetes Service and network access rules.

The rendered XML contains credentials. Do not store it in a ConfigMap.
ConfigMap volumes are read-only, and environment variables sourced from them require a Pod restart to change.
See the [ConfigMap documentation](https://kubernetes.io/docs/concepts/configuration/configmap/).

## Startup and updates

1. Mount the PVC directory at `/opt/tak/data`.
2. Keep `/opt/tak/data/CoreConfig_config.xml` as the canonical saved file.
3. Keep `/opt/tak/CoreConfig.xml` and `/opt/tak/data/CoreConfig.xml` as compatibility links to it.
4. Let the config startup wrapper acquire the existing exclusive lock.
5. Render a temporary template from ConfigMap and Secret inputs.
6. Merge the managed attributes into the saved XML. Seed from the template only when no saved or legacy file exists.
7. Validate the result with the release's XSD. Preserve the saved file when parsing, merging, or validation fails.
8. Save the existing file as a pre-merge backup before publishing a changed result.
9. Start the configuration JVM and keep the lock for its lifetime.

Mount the containing directory so the merger can create temporary files, replace the canonical file, and retain backups together.
Do not mount a ConfigMap over either XML path.
Do not copy a complete template over the saved file on each startup.
Do not use `emptyDir` for the saved authority: its contents are lost when the Pod is removed.
See the [volume documentation](https://kubernetes.io/docs/concepts/storage/volumes/).

Keep this merge in the existing startup wrapper.
A completed init container cannot retain the lifetime lock or rerun the merge after an application-container restart.
Do not add a file watcher that merges deployment inputs while the JVM is saving administrator changes.

Change deployment inputs through a controlled replacement of the config Pod.
Kustomize's generated ConfigMap names include a content hash, which can change the referenced Pod template when inputs change.
Coordinate the affected role restarts; a changed reference alone does not establish safe ordering.
T1 must establish the supported recovery procedure before production rollout.
Treat Secret rotation as a coordinated update of the identity files and matching passwords.
See the [Kustomize generator documentation](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/#generatoroptions).

## One persistent writer

Run one configuration-service replica.
The wrapper lock prevents competing wrappers from merging the same state.
It does not stop Java code that writes without acquiring that lock.
All runtime saves must reach the configuration-service owner before this model is accepted.

Retain the current shared RWO PVC and same-node placement for the T1 baseline.
RWO allows several Pods on one node; it does not enforce one writer.
Do not switch this shared claim to `ReadWriteOncePod`: that mode permits only one Pod to mount it.
A dedicated config-only PVC could use `ReadWriteOncePod` with a supporting CSI driver after the other roles no longer need to mount it.
That is a separate runtime change, not a prerequisite for preserving administrator edits.
See the [persistent-volume access modes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes).

A singleton StatefulSet is a suitable native controller for a persistent config owner.
Changing the controller does not fix Java saves or remove the shared-volume constraints.
The current `Recreate` Deployment prevents rollout overlap, but does not guarantee this during manual Pod deletion.
Keep the lock and storage constraints even if the controller changes.
See [StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/) and [Recreate Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#recreate-deployment).

Back up the persistent state separately from the manifests.
A Git rollback restores deployment inputs; it does not restore administrator state.
Retain the PVC through application upgrades and certificate renewals.

## Evidence and remaining acceptance

The current merger already implements selective ownership, validation, backups, and atomic replacement.
The config wrapper already holds its lock across JVM startup.
Ten focused tests passed in `localhost/tak-server:t1-5.8.84-pr136` using the repository helpers and the image's XSD and gomplate.
The output is recorded in ignored `outputs/t1/coreconfig-design-tests.log`.
The tests cover the merger and wrapper, not JVM persistence or crash durability.

Run the focused checks from the repository root:

```sh
podman run --rm --pull=never --network none -v "$PWD:/workspace:ro" \
  -e PYTHONPATH=/workspace/tests --entrypoint /usr/bin/python3 \
  localhost/tak-server:t1-5.8.84-pr136 \
  -B -m unittest -v test_coreconfig test_start_tak
```

The [lost-edit reproduction](../bugreports/001-coreconfig-admin-edits-lost/HANDOFF.md) already used a writable PVC.
The Java address comparison suppressed the save despite a successful admin API response.
The [additional writers](../bugreports/003-multiple-xml-writers/HANDOFF.md) and [unsafe publication](../bugreports/004-unsafe-xml-publication/HANDOFF.md) also remain unresolved.
Moving the file to another Kubernetes resource cannot repair those application paths.

After the application persistence decision, verify a real admin edit reaches the canonical file.
Then change a managed input, replace the config Pod, and verify both values survive in the saved file and the admin API.
Verify follower startup and upgrades cannot overwrite that state.
The existing [T1 findings](t1-runtime-findings.md) define the application-patch boundary and recovery work still required.
