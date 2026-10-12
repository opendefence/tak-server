# Strict authentication hook inspection (TAK 5.8.84)

The inspected vendor tuple is `takserver.war` SHA-256
`64309513e45ba1e92084d457cd787b35d1c570ab918a11fd1ce1e5bdd4d6f26c`
and `UserManager.jar` SHA-256
`4ad7adcb9a09156d7122bfb2d4ddf3fd6705fb612f4d521335a5e08b449d24f6`.
`extensions/strict-fingerprint/check-vendor-hooks.sh` rejects other artifacts and
checks the inspected class signatures and HTTP security configuration.
This is a compatibility probe, not an installed authentication hook.

`X509AuthCodec.doTlsAuth()` obtains the messaging connection's peer certificate,
constructs an `AuthenticatedUser`, and calls `X509Authenticator.authenticate(User, Input)`.
Its `lastAuthTime` interval can skip repeat authentication. It catches an authentication
exception and can close the channel asynchronously; that alone does not prove the first
CoT was stopped. The private `X509Authenticator.auth(User, Input)` checks revocation and
may grant token, file, cache, LDAP, or anonymous access. Its legacy file path accepts a
matching account identifier even when the stored scalar fingerprint differs.
`X509AuthCodec.decode(ByteBuffer)` returns inbound bytes after `doTlsAuth()` returns, so
the inbound decoder must block a rejected leaf before returning the first CoT. Its
`encode(ByteBuffer)` path also needs a current approval check for existing connections.

HTTP loads `security-context.xml` with `X509AuthenticationFilter` before the basic,
OAuth token, bearer token, and access-decision filters. The X.509 filter calls
`TakAuthenticationProvider.authenticate(Authentication)` with a certificate credential.
The provider records the certificate and fingerprint in the HTTP session. A hook only
in this provider would miss previously cached principals and other token paths.
`FilterSecurityInterceptor.doFilter(ServletRequest, ServletResponse, FilterChain)` is
the final configured authorization filter for `/**`, after the authentication filters.
A per-request guard there can reject a missing/revoked leaf and a principal whose
account differs from the approved certificate CN before the application handler runs.

The external agent now checks messaging before `decode` returns CoT and before `encode`
sends data, checks the authenticator before grants, and checks the HTTP authorization
filter on every request. Its launcher loads and verifies each required transformed class
before TAK opens client traffic; absent injection or changed vendor bytes stop startup.
The policy starts empty. Trusted projection and both-JVM readback are still required
before strict mode can admit approved clients or report full capability.

Probe command (using the pinned Java 17 JDK image and locally retained vendor binaries):

```sh
podman run --rm --network none -v "$PWD:/repo:ro" \
  eclipse-temurin:17-jdk-noble@sha256:fb79620c3f6ee8f1c7530a8dc4fd49e3b410bcef037694ad4858a1553bac4170 \
  sh /repo/extensions/strict-fingerprint/check-vendor-hooks.sh \
  /repo/outputs/t1/binary/takserver.war /repo/outputs/t1/binary/UserManager.jar
```
