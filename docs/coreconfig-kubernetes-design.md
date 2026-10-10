# CoreConfig ownership in Kubernetes

Keep the live `CoreConfig.xml` as persistent application state on a PVC.
Use ConfigMaps and Secrets for deployment inputs.
Reuse `scripts/coreconfig.py` to merge those inputs into the saved state before the configuration service starts.
Only the config service uses the persistent CoreConfig as its local file.
Other roles use private, writable bootstrap copies and receive runtime configuration through Ignite.
No new operator or synchronization sidecar is needed.

The user selected one Pod with separate role containers.
The [T1 follow-up](t1-single-pod-findings.md) verifies admin persistence with private follower files in that topology.
It leaves the Java publication and file-auth failure risks open.

## Ownership

| Data | Owner | Kubernetes storage |
| --- | --- | --- |
| Database endpoint, listener settings, authentication mode, identity paths | Deployment | ConfigMap inputs |
| Database credentials and identity passwords | Deployment | Secret inputs |
| Initial XML structure and defaults | Image | Existing `CoreConfig.tpl` |
| Saved XML, including administrator changes | Configuration service | PVC |
| Follower CoreConfig bootstrap copies | Each follower | Private runtime storage |
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

1. Mount the PVC directory at `/opt/tak/data` in the config container.
2. Keep `/opt/tak/data/CoreConfig_config.xml` as the canonical saved file.
3. In that container, keep `/opt/tak/CoreConfig.xml` and `/opt/tak/data/CoreConfig.xml` as compatibility links to it.
4. Let the config startup wrapper acquire the existing exclusive lock.
5. Render a temporary template from ConfigMap and Secret inputs.
6. Merge the managed attributes into the saved XML. Seed from the template only when no saved or legacy file exists.
7. Validate the result with the release's XSD. Preserve the saved file when parsing, merging, or validation fails.
8. Save the existing file as a pre-merge backup before publishing a changed result.
9. Start the configuration JVM and keep the lock for its lifetime.

Followers must link their `/opt/tak/CoreConfig.xml` to a private file instead of the persistent authority.
They may write defaults or upgrades to that private file.
Seed these copies from the validated authority after the config wrapper completes its merge.
The live test confirmed that the selected admin edits reach the owner while follower copies stay unchanged.
Verify other local reads before replacing saved-state bootstrap input with a fresh template.
Their runtime use of administrator settings through Ignite does not require sharing the on-disk authority.

Mount the containing directory so the merger can create temporary files, replace the canonical file, and retain backups together.
Do not mount a ConfigMap over either XML path.
Do not copy a complete template over the saved file on each startup.
Do not use `emptyDir` for the saved authority: its contents are lost when the Pod is removed.
See the [volume documentation](https://kubernetes.io/docs/concepts/storage/volumes/).

Keep this merge in the existing startup wrapper.
A completed init container cannot retain the lifetime lock or rerun the merge after an application-container restart.
Do not add a file watcher that merges deployment inputs while the JVM is saving administrator changes.

Change deployment inputs through a controlled replacement of the shared server Pod.
Kustomize's generated ConfigMap names include a content hash, which can change the referenced Pod template when inputs change.
Coordinate the affected role restarts; a changed reference alone does not establish safe ordering.
T1 must establish the supported recovery procedure before production rollout.
Treat Secret rotation as a coordinated update of the identity files and matching passwords.
See the [Kustomize generator documentation](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/#generatoroptions).

## One persistent writer

Run one configuration-service replica.
The wrapper lock prevents competing wrappers from merging the same state.
It does not stop Java code that writes without acquiring that lock.
All administrator CoreConfig saves must reach the configuration-service owner before this model is accepted.
Use private follower files to isolate their local startup writes.

The original T1 baseline used a shared RWO PVC and same-node placement across three Pods.
The follow-up uses one Pod and private follower CoreConfigs.
RWO allows several Pods on one node; it does not enforce one writer.
`ReadWriteOncePod` can serve several containers in the selected single Pod when the CSI driver supports it.
The tested local-path claim remains RWO. It does not establish RWOP support or movable storage.
See the [persistent-volume access modes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes).

A singleton StatefulSet is a suitable native controller for the shared server Pod and its persistent config owner.
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
The [additional-writer report](../bugreports/003-multiple-xml-writers/HANDOFF.md) is reclassified as a shared-file deployment risk.
Restore private follower paths before requiring an application change for those startup writes.
The persistent owner's [unsafe publication](../bugreports/004-unsafe-xml-publication/HANDOFF.md) remains a separate concern.
The save guard also remains independent of file isolation; trace writes in an isolated-file reproduction to exclude an additional race.

Real admin saves and full Pod replacement passed with the private-file fixture.
T2 packages this adapter and isolates API file-auth from the persistent messaging authority.
The external server launcher selects the actual role CoreConfig path before TAK starts.
The vendor copy routine replaces backup symlinks, so a root backup link alone cannot persist the Java backup.
Actual owner-path selection places that backup beside the PVC authority.
TAK cluster mode is rejected because it redirects the authority to another path.
The native candidate preserved an admin edit through a managed database endpoint change and Pod replacement.
API file-auth and its backup were private; the owner's Java backup was persistent. All inspected files had mode `0600`.
See [T2 evidence](t2-native-layout.md). Follower upgrades and interrupted owner saves still need separate tests.
The [T1 follow-up](t1-single-pod-findings.md) records the selected architecture and release limits.
