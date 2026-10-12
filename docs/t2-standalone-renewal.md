# T2 isolated standalone and HTTPS renewal check

Date: 2026-10-11. Kind context: `kind-tak-server-t0`.
The test used namespace `tak-server-t2`, database `tak_standalone`, and the pinned
`localhost/tak-server:t2-schema-5.8.84` image. It did not change the live `cot`
database, `tak-server-t1` PVC, or its identity Secrets.

An isolated overlay of `k8s/base` supplied the database address and test DNS name.
No Core, RMAPI, integration operator, or sibling checkout was present in that namespace.
The test CA signed separate RSA CoT and HTTPS identities and an admin probe identity.
Its signing key remained in ignored local test files, outside server Pods.
The JKS stores used alias `certificate`; the client and federation truststores used the CA public certificate.

| Check | Result |
| --- | --- |
| Fresh database and schema Job | Created an empty PostGIS/pgcrypto database. The separate Job applied 101 migrations. A distinct runtime role received data grants after migration. |
| First server start | The admin bootstrap succeeded on its second attempt. API startup raced messaging service deployment and logged a missing metrics service. Its JVM stayed alive after Spring startup failure. Restarting only the disposable API container brought the Pod to 3/3 readiness. |
| Authenticated HTTPS | Admin probe called the user-list endpoint with mTLS and received HTTP 200. The served HTTPS certificate fingerprint matched the supplied store. |
| Repeated apply | Every base resource was unchanged. The Pod UID remained the same and all three containers stayed ready. |
| HTTPS identity renewal | Replaced only `tak-https-identity` with a new JKS from the same test CA, then ran `scripts/restart-kubernetes.sh`. The new Pod reached 3/3 readiness with zero restarts. The served fingerprint changed from `20:40:A4:68:32:02:74:C3:91:8A:F2:76:47:91:13:38:AE:54:97:B5:26:53:1F:4A:8A:6B:74:C7:29:6E:48:4F` to `E5:CF:FA:C8:65:D8:47:4C:D9:84:41:27:1F:6C:B5:0E:E2:28:44:43:24:85:66:F8:90:FE:0C:71:82:15:76:7D`. Authenticated HTTPS still returned 200. |
| State and trust after replacement | Persistent file-auth and federation truststore hashes were unchanged. CoreConfig bytes changed on startup, but its backup matched the previous file and a parsed XML comparison found no changed elements, attributes, or text values. The served CoT certificate still matched the original CoT identity. |

This proves one supplied HTTPS identity replacement with an unchanged store password and CA.
It does not test issuer automation, password rotation, CoT/client/federation trust renewal,
external CoT delivery, or a production PKI. The first-start API race needs a bounded startup fix
before claiming reliable fresh installation. The actual LoadBalancer standalone overlay was not
applied; this test used the same base resources with a local Kind overlay.

Private certificates, keys, render, and logs stay under ignored `outputs/t2/standalone/`.
