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
| New launcher after a database statement timeout | The Job failed before the first migration at 1 ms. After reset, a new Job applied all 101 migrations. |
| Separate runtime role with documented grants | Read a TAK table. `CREATE TABLE` and `UPDATE schema_version` failed with permission denied. |
| Legacy `takdb_base.sql` in a disposable database | Import succeeded. The dump had 81 versioned migrations through V87, one repeatable migration, and three `role` rows. The new Job stopped on V7 and V9 checksum mismatches. |
| Exact V7/V9 metadata reconciliation in that disposable database | Changed only the two known checksum values, then a new candidate Job applied 19 migrations through V106. All 101 history rows succeeded. The `role` row hash was unchanged. |
| Legacy repeat and schema comparison | Repeat applied zero. A schema-only dump matched a fresh V106 install after removing dump tokens and trailing whitespace. |
| Legacy Job interrupted at V98 | A held `client_endpoint` lock stopped V98 after V88–V97 committed. Terminating the Job and its database session left V97 as the last successful migration and no V98 `team` or `role` columns. |
| New Job after that interruption | Applied the remaining nine migrations through V106. All 100 versioned rows succeeded, the seeded role hash was unchanged, and the normalized schema-only dump matched a fresh install. |
| Legacy dump with three added data rows | A CoT row, mission, and TAK user survived V88–V106. CoT ID became `bigint`; 4,096-bit CoT and mission groups became 32,768 bits with the last bit retained; the mission GUID was filled. The normalized schema matched a fresh install. |

The test migration account owned its databases and schema objects.
The test runtime role had data grants and no schema creation right.
PostgreSQL advisory locking is present in the pinned Flyway implementation.
Concurrent Job results confirm serialization for these empty databases.

A 100 ms or 5 ms statement timeout did not interrupt a migration.
Those test database settings were reset.

The legacy fixture was `scripts/takdb_base.sql` at SHA-256
`88dee8d2d86eae0cbaf3e202b4800b4d3c5dee39a5372c72de274b1a743aed24`.
Its stored V7 checksum was `1620613293`; the pinned JAR expects `-1424456146`.
Its stored V9 checksum was `-1676016357`; the pinned JAR expects `-663149251`.
The test changed those two history values only in the disposable copy.
It did not enable automatic Flyway repair or change the source dump.
The added rows exercise selected data migrations, but they do not represent the size or variety of a production database.
Before adopting a real database, review its history, ownership, source release, backup, and data preservation.
The migration account must own the existing objects or have equivalent migration rights.
Do not replay V7: it contains `DROP ... CASCADE` statements.
This interruption stopped V98 while it waited for a table lock, before its first statement changed the table.
It does not prove recovery from every possible failure within a migration.
The test used a second disposable copy; it did not interrupt the live TAK database.
Do not infer automatic adoption of an unversioned legacy database from this result.
