# T1 CoT cache investigation

The user confirmed `Switched; resume T1` on 2026-10-10 for `gpt-6-astra` / `xhigh`.
Runtime model metadata is unavailable. This investigation uses the unchanged [T2 candidate](t2-native-layout.md#candidate).

## Cause and evidence

The native base reduced `TAK_IGNITE_CACHE_MAX_BYTES` from T1's 268435456 bytes (256 MiB) to 67108864 bytes (64 MiB).
At 64 MiB, messaging spins in Ignite page eviction while creating client subscriptions.
Client-side TLS can finish, but CoT delivery cannot proceed. Further connections can also time out during TLS.
The authenticated user-list readiness check continues to pass.

The messaging thread dump contains this call path:

```text
NioNettyTlsServerHandler.operationComplete
NioNettyHandlerBase.createSubscription
SubmissionService.createSubscriptionFromConnection
DistributedSubscriptionManager.addSubscription
SubscriptionStore.updateSubscriptionCaches
IgniteCacheHolder.cacheRemoteSubscription
IgniteCacheProxyImpl.put
IgniteCacheDatabaseSharedManager.ensureFreeSpace
Random2LruPageEvictionTracker.evictDataPage
```

Several Netty event threads use CPU in this path. The group-manager user-cache writer also spins in eviction.
Ignite reports about 56 MiB used in the 64 MiB region.
Inspection of the pinned TAK bytecode confirms that the supplied cache maximum configures this region with `RANDOM_2_LRU` eviction.
The page composition and a general Ignite defect were not established.

## Controlled comparison

The experiment changed only `TAK_IGNITE_CACHE_MAX_BYTES` in the owned StatefulSet and replaced the Pod.
It kept the image, database, PVC, identities, authentication settings, launchers, and `tests/check-cot.py` unchanged.
The initial cache size remained 16777216 bytes (16 MiB). The Ignite pool setting remained 2.
Each test used the same issued clients and verified the server certificate and hostname.

| Run | Pod IP | Maximum | Result |
| --- | --- | --- | --- |
| Original T2 setting | `10.244.0.44` | 64 MiB | Peer read timed out. Messaging threads spun in page eviction. |
| First control | `10.244.0.45` | 256 MiB | CoT passed in both directions. |
| Repeated failure | `10.244.0.46` | 64 MiB | Peer read timed out again. The same eviction path appeared while readiness remained 3/3. |
| Final restoration | `10.244.0.47` | 256 MiB | CoT passed in both directions. Verified mTLS user-list returned HTTP 200. All three roles were ready with zero restarts. |

Both passing controls preserved the SHA-256 values of owner XML, persistent file-auth, federation trust, and both identity stores.
The final live WAR and `UserManager.jar` hashes match the pinned T2 candidate.
The StatefulSet remains at 256 MiB through an explicit environment override in the test namespace.

The existing client test is the regression check. Recreate the port-forward after each Pod replacement:

```sh
kubectl --kubeconfig outputs/t0/kubeconfig --context kind-tak-server-t0 \
  -n tak-server-t1 port-forward statefulset/tak-server 38089:8089
# In another terminal, use the configured project Python interpreter:
.venv/bin/python tests/check-cot.py --cert-dir outputs/t1/client \
  --server-name tak-messaging.tak-server-t1.svc.cluster.local --port 38089
```

For the controlled experiment, `kubectl set env statefulset/tak-server TAK_IGNITE_CACHE_MAX_BYTES=268435456`
overrode the ConfigMap value in all three role containers. Use the same kubeconfig, context, and namespace as above.
The failing value is `67108864`. This failure is reproduced only in the owned disposable test environment.

Private evidence is under ignored `outputs/t1-cot/`: client results, rollout logs, thread dumps, cache configuration, and state hashes.
An initial attempt after the first rollout reached a stale port-forward and returned EOF. It is excluded from the comparison.
The successful run used a new forward to the replacement Pod.

## T2 handoff and limits

- Correct the cache maximum in `k8s/base/kustomization.yaml`. Validate the rendered base and the live candidate together.
- Remove the experimental environment overrides only after the generated ConfigMap supplies the corrected value.
- Retain the two-client CoT check in native acceptance. RPC readiness alone missed this failure.
- Account for Java heap, Ignite regions, and other native memory when setting container resources. The 256 MiB result covers this fixture only.

The source base still selects 64 MiB. The experiment is not the source fix.
Strict authentication remains unwired. This result does not establish load capacity, a minimum safe cache size, recovery after arbitrary exhaustion, or production readiness.
No PVC, identity, database, or unrelated cluster was removed. Product code and vendor binaries were not edited during this investigation.
