# T2 schema migration evidence

Date: 2026-10-10. Context: `kind-tak-server-t0`. Namespace: `tak-server-t1`.
All databases in this check were disposable. The live `cot` database and TAK PVC were unchanged.

The candidate image is `localhost/tak-server:t2-schema-5.8.84`.
Its local manifest digest is `sha256:7f33ba70240cbd85ce67324ec51b8f9d9e16b5b848c708cdab7baa9dba06d7f3`.
The unchanged TAK `SchemaManager.jar` SHA-256 is `7d1a1fe79c2023bdd3f01644609af4c77e5b6d7caf1cfcf3e813e62f3498e337`.
The image adds `SchemaUpgrade`, a Java launcher for the Flyway migrations in that JAR.
It uses `schema_version`, disables `clean`, and calls `migrate` without the vendor `repair` retry.

| Check | Result |
| --- | --- |
| Vendor command on an empty database with PostGIS and pgcrypto | Applied 101 migrations without `takdb_base.sql`. |
| Vendor repeat and two simultaneous fresh commands | Repeat applied zero. Simultaneous jobs applied 101 and zero. |
| Vendor `validate` after changing the V7 checksum to `1` | Returned success. Bytecode shows `upgrade` calls `repair` after a Flyway exception. |
| Rendered candidate Job on an empty database | Applied 101 migrations. `schema_version` had 101 successful rows. |
| New launcher on an empty database | Applied 101 migrations. `schema_version` had 101 successful rows. |
| New launcher on the same database | Applied zero migrations. |
| Two simultaneous new-launcher Jobs on another empty database | Applied 101 and zero migrations. Both completed. |
| New launcher after changing the V7 checksum to `1` | Job failed with a Flyway checksum error. The stored checksum remained `1`. |
| New launcher on a nonempty database without schema history | Job failed. It did not create `schema_version` or baseline the unknown tables. |
| Separate runtime role with documented grants | Read a TAK table. `CREATE TABLE` and `UPDATE schema_version` failed with permission denied. |

The test migration account owned its databases and schema objects.
The test runtime role had data grants and no schema creation right.
PostgreSQL advisory locking is present in the pinned Flyway implementation.
Concurrent Job results confirm serialization for these empty databases.

Attempts to force an interruption with 100 ms and 5 ms database statement timeouts did not stop a migration.
Both test Jobs completed all 101 migrations; those database settings were reset.
A populated older-schema upgrade and retry after a partial or interrupted migration remain untested.
Do not infer automatic adoption of an unversioned legacy database from the empty-database result.
