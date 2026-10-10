# Strict fingerprint policy

Status: the user adopted this server change on 2026-10-10.
The policy and its conformance tests are implemented. TAK does not call this policy yet.
Do not advertise strict authentication or deploy this directory as a complete server patch.

The user approved the integration proposal after the actual 5.8.84 component test accepted an unapproved same-UUID certificate.
This approval supersedes the older `AGENTS.md` restriction on application changes for this specific authentication change.
It does not authorize the separate persistence fixes in the server bug reports.

## Implemented behavior

`StrictFingerprintPolicy` uses only Java 17 standard libraries.
It holds an immutable projection in one JVM and returns a revision for each successful check.
It accepts only an exact leaf SHA-256 fingerprint and an exact, single certificate CN matching the account identifier.
It rejects repeated attribute types inside a CN-containing relative distinguished name (RDN).
It checks leaf validity and rejects CA certificates.
The caller must already have validated the TLS certificate chain and client-certificate usage.

Each update replaces one account's complete accepted set. Reads see one immutable snapshot.
Updates require the current revision. Exactly one competing update can use that revision.
An invalid update preserves the previous state. An empty set removes that account's approval.
The revision is a random server token. Restart and invalidation create a new token and an empty projection.
Old update tokens cannot overwrite state after either event.
This is a server revision, not a Core generation or durable activation event.

The caller supplies an explicit approval deadline. Access ends at that deadline, with no default overlap timer.
The owner must call `invalidate()` when authoritative state becomes unavailable.
The policy cannot detect transport failure by itself.
Concurrent revocation does not cancel a decision already made from an earlier snapshot.
Existing connections, resumed sessions, and cached HTTP principals need their own enforcement checks.

The limits are 1,024 accounts, 32 fingerprints per account, and 256 characters per account identifier.
Fingerprints use 64 lowercase hexadecimal characters without separators.
Account identifiers remain exact strings. This does not settle Core's UUID encoding contract.
The policy neither changes account roles nor stores private keys.

## Run the conformance test

From this worktree's root, run:

```sh
podman run --rm --network none --cpus 2 --memory 512m \
  --tmpfs /work:rw,size=64m \
  -v "$PWD/extensions/strict-fingerprint:/extension:ro" \
  eclipse-temurin:17-jdk-noble@sha256:fb79620c3f6ee8f1c7530a8dc4fd49e3b410bcef037694ad4858a1553bac4170 \
  sh /extension/test.sh
```

The container generates a CA and eight distinct signed leaves in tmpfs.
It compiles with `--release 17 -Xlint:all -Werror` and runs the assertions.
It tests two approved same-UUID certificates, an unapproved same-UUID certificate, CN ambiguity,
single-certificate removal, empty/missing state, lease and certificate expiry, concurrent updates, and restart tokens.
No keys or generated certificates remain after the container exits.
The 2026-10-10 ARM64 run passed 46 assertions. Applicable repository checks passed.
The duplicate-CN test first failed because JNDI collapsed identical values inside one RDN.
The policy now checks the RDN's attribute count before accepting its CN.

## Required server wiring

Fresh server source will not be available. Keep the pinned TAK 5.8.84 vendor artifacts unchanged on disk.
Compile an external extension against those binaries, following the [plugin launcher pattern](../../bugreports/006-pluginmanager-forces-localhost/HANDOFF.md).
Inspect the exact call paths before choosing launcher/component replacement or, if needed, a Java instrumentation agent.
The plugin workaround proves its own startup path, not authentication coverage.
Older public source is an inspection aid only. Compatibility depends on the target bytecode and tests.

Complete these changes together:

1. Add validated strict-mode extension configuration outside the vendor CoreConfig schema. Install and verify hooks before client admission in both JVMs. Missing or incompatible injection must stop strict startup. Preserve legacy mode only when explicitly selected.
2. Bind a trusted management writer to complete accepted sets, deadlines, and revision-checked updates.
3. Distribute and acknowledge the projection in messaging and API processes. A local write does not prove either remote process applied it.
4. Enforce the policy before token, group-cache, role, group, and anonymous grants. Cover every supported certificate authentication entry point.
5. Make denial stop message routing and HTTP access. A caught exception followed by channel close does not prove the first CoT was blocked.
6. Recheck cached HTTP identities and define existing/resumed-session enforcement. Keep the optional disconnect decision open.
7. Version the extension, its configuration schema, and management capability with the unchanged WAR and `UserManager.jar`. Supply a companion management JAR only if needed. Report the active enforcement mode and artifact versions to integration.
8. Repeat the actual-binary matrix and live TLS/CoT/HTTPS tests in a separate test environment. Include absent/incompatible injections, changed hooks, and classloader failures. Verify that these failures cannot expose an unprotected strict service.

The current tests exercise this policy, not the TAK authentication entry points.
The unmodified 5.8.84 binary still fails the approved-set requirement.
Production Core adapters also require the versioned identity, approval, freshness, and observation contracts.
