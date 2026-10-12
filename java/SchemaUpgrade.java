package org.opendefence.tak;

import org.flywaydb.core.Flyway;

public final class SchemaUpgrade {
    public static void main(String[] args) {
        String address = System.getenv("POSTGRES_ADDRESS");
        String database = System.getenv("POSTGRES_DB");
        String user = System.getenv("POSTGRES_USER");
        String password = System.getenv("POSTGRES_PASSWORD");
        if (address == null || database == null || user == null || password == null) {
            throw new IllegalArgumentException("Database address, name, user, and password are required");
        }
        String url = "jdbc:postgresql://" + address + ":5432/" + database;
        int applied = Flyway.configure()
                .dataSource(url, user, password)
                .table("schema_version")
                .cleanDisabled(true)
                .load()
                .migrate()
                .migrationsExecuted;
        System.out.println("Applied " + applied + " schema migrations");
    }
}
