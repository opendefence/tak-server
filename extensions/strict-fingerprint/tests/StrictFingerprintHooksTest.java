package org.opendefence.tak.auth;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Set;

public final class StrictFingerprintHooksTest {
    private static final String USER = "00000000-0000-4000-8000-000000000001";

    public record Connection(X509Certificate cert) {
        public X509Certificate getCert() { return cert; }
    }

    public record User(String name, X509Certificate cert) {
        public String getName() { return name; }
        public X509Certificate getCert() { return cert; }
    }

    public record Authentication(String name) {
        public String getName() { return name; }
    }

    public record Request(X509Certificate[] chain) {
        public Object getAttribute(String name) {
            return "jakarta.servlet.request.X509Certificate".equals(name) ? chain : null;
        }
    }

    private static X509Certificate cert(String name) throws Exception {
        try (var input = Files.newInputStream(Path.of(name + ".pem"))) {
            return (X509Certificate) CertificateFactory.getInstance("X.509").generateCertificate(input);
        }
    }

    private static void denies(Runnable action) {
        try {
            action.run();
        } catch (SecurityException expected) {
            return;
        }
        throw new AssertionError("Expected strict admission denial");
    }

    public static void main(String[] args) throws Exception {
        var main = cert("main");
        var other = cert("unapproved");
        var approved = new Connection(main);
        var unapproved = new Connection(other);
        var policy = StrictFingerprintHooks.policy();
        denies(() -> StrictFingerprintHooks.messaging(approved));
        if (StrictFingerprintHooks.http(new Request(new X509Certificate[] {main}),
                new Authentication(USER))) throw new AssertionError("Empty projection allowed HTTP");
        var fingerprint = HexFormat.of().formatHex(
                MessageDigest.getInstance("SHA-256").digest(main.getEncoded()));
        policy.replace(policy.read().revision(), USER, Instant.now().plusSeconds(300),
                Set.of(fingerprint));
        StrictFingerprintHooks.messaging(approved);
        StrictFingerprintHooks.user(new User(USER, main));
        denies(() -> StrictFingerprintHooks.messaging(unapproved));
        denies(() -> StrictFingerprintHooks.user(new User(USER, other)));
        denies(() -> StrictFingerprintHooks.user(new User("different", main)));
        if (!StrictFingerprintHooks.http(new Request(new X509Certificate[] {main}),
                new Authentication(USER))) throw new AssertionError("Approved HTTP denied");
        if (StrictFingerprintHooks.http(new Request(new X509Certificate[] {other}),
                new Authentication(USER))) throw new AssertionError("Unapproved HTTP allowed");
        if (StrictFingerprintHooks.http(new Request(new X509Certificate[] {main}),
                new Authentication("different"))) throw new AssertionError("Mismatched principal allowed");
        if (StrictFingerprintHooks.http(new Request(null), new Authentication(USER))) {
            throw new AssertionError("Cached principal without client certificate allowed");
        }
        policy.invalidate();
        denies(() -> StrictFingerprintHooks.messaging(approved));
        if (StrictFingerprintHooks.http(new Request(new X509Certificate[] {main}),
                new Authentication(USER))) throw new AssertionError("Invalidated HTTP allowed");
        System.out.println("RESULT hook_helpers=PASS approved=ALLOW unapproved=DENY revoked=DENY");
    }
}
