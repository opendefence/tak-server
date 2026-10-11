# TAK 5.8-RELEASE-92 local candidate

Source: [pvarki/docker-atak-server PR #143](https://github.com/pvarki/docker-atak-server/pull/143), commit `58efbf0`. This checkout now selects `5.8-RELEASE-92` for the distribution build, Compose, CI, native manifests, and both Zarf flavors. The local ARM64 image is tagged `localhost/tak-server:release-92` and `localhost/tak-server:local`; neither tag is published.

| Artifact | SHA-256 |
| --- | --- |
| Distribution image manifest | `07ece0dfce6c6285f63f8641a15556ca05c16c060e744765ec22fbca2716819c` |
| Local runtime image manifest | `12ecb27b054b05ce612bbd5b16d84e2544bad4c3e33d78b2edf57265e9ad78d2` |
| `takserver.war` | `9f03a3c21e5ed09350fd92a2c16fed0dca246122dfb8f266e4179f3ca4134523` |
| `UserManager.jar` | `0fe547c2f4ce05d06a2e9724e0c2837eab0a0ba5be398390bb974b2385ce6f14` |
| `SchemaManager.jar` | `286abc06a08e18b4072efdc6ce6020ae82f7775df471d7db152abb9f385a329e` |

The strict agent checks the new WAR and UserManager checksums. Its three instrumented classes (`X509AuthCodec`, `X509Authenticator`, and Spring's `FilterSecurityInterceptor`) have exactly the same bytes and method signatures as the 5.8-84 candidate; the vendor hook check and both fail-closed startup probes passed. The 101 SQL migration resources in the two SchemaManager JARs have identical paths and bytes. This is compatibility evidence for the tested hooks and migrations, not a claim about all vendor behavior.

The only `WEB-INF/classes` references to `getUpdateinterval` are `X509AuthCodec` and `LdapAuthenticator`. Release-92 bytecode multiplies the value by 1000 in the codec and passes it to `setUpdateIntervalSeconds` in the authenticator. Earlier practical testing observed millisecond behavior. The local cluster has no LDAP test service, so effective refresh timing remains unverified for this release. Keep the provisional `6000` default until a timed runtime test reconciles the difference; [the plan](implementation-plan.md#ldap-interval-binary-compatibility-follow-up) tracks removal.

Validation: the local image built; 33 Python tests passed inside it; the 46 policy assertions, hook helper test, strict installation/fail-closed probes, vendor hook check, federation truststore test, and HTTPS keystore test passed. Both Zarf flavor lints and native Kind/integrated renders passed. In the disposable `tak-server-local` Kind cluster, the new schema Job applied zero migrations, grants completed, all three server containers used image `25b04bdf89c7` with zero restarts, authenticated HTTPS returned 200, and two TLS connections using the local probe identity exchanged CoT in both directions. The federation truststore hash was unchanged. The persistent CoreConfig changed only its `network` version attribute; its previous copy remains in the owner backup. Test certificates and keys copied to the host for CoT were removed after the check.

The local rollback image is the retained 5.8-84 tag `localhost/tak-server:t2-schema-5.8.84`. Do not roll back a populated production database from this local evidence alone: review any data written while release 92 was active, the schema history, and the matching image/identity tuple first. The integrated flavor, an offline published-digest package, a timed LDAP refresh test, and complete strict-mode acceptance remain open.
