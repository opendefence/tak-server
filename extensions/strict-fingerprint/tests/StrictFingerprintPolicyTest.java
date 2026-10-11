import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.cert.CertificateException;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ConcurrentModificationException;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.opendefence.tak.auth.StrictFingerprintPolicy;

public final class StrictFingerprintPolicyTest {
    private static final String USER = "00000000-0000-4000-8000-000000000001";
    private static final String OTHER = "00000000-0000-4000-8000-000000000002";
    private static int assertions;

    private interface CheckedAction { void run() throws Exception; }

    private static void check(boolean condition) {
        assertions++;
        if (!condition) throw new AssertionError("Assertion " + assertions + " failed");
    }

    private static void rejects(Class<? extends Throwable> type, CheckedAction action) throws Exception {
        try {
            action.run();
        } catch (Throwable failure) {
            if (!type.isInstance(failure)) throw new AssertionError("Unexpected failure", failure);
            assertions++;
            return;
        }
        throw new AssertionError("Expected " + type.getSimpleName());
    }

    private static X509Certificate cert(String name) throws Exception {
        try (var input = Files.newInputStream(Path.of(name + ".pem"))) {
            return (X509Certificate) CertificateFactory.getInstance("X.509").generateCertificate(input);
        }
    }

    private static String fingerprint(X509Certificate cert) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(cert.getEncoded()));
    }

    public static void main(String[] args) throws Exception {
        var main = cert("main");
        var tak = cert("tak-only");
        var unapproved = cert("unapproved");
        var other = cert("other");
        var duplicateCn = cert("duplicate-cn");
        var duplicateCnRdn = cert("duplicate-cn-rdn");
        var multivaluedRdn = cert("multivalued-rdn");
        var missingCn = cert("missing-cn");
        var ca = cert("ca");
        var allFingerprints = new HashSet<String>();
        for (var leaf : List.of(main, tak, unapproved, other, duplicateCn, duplicateCnRdn, multivaluedRdn, missingCn)) {
            leaf.verify(ca.getPublicKey());
            check(allFingerprints.add(fingerprint(leaf)));
        }
        var now = Instant.now();
        var clock = Clock.fixed(now, ZoneOffset.UTC);
        var deadline = now.plusSeconds(300);
        var policy = new StrictFingerprintPolicy(clock);
        rejects(CertificateException.class, () -> policy.requireApproved(USER, main));
        var supplied = new HashSet<>(Set.of(fingerprint(main), fingerprint(tak)));
        var initialRevision = policy.read().revision();
        var both = policy.replace(initialRevision, USER, deadline, supplied);
        supplied.clear();
        check(policy.requireApproved(USER, main).equals(both.revision()));
        check(policy.requireApproved(USER, tak).equals(both.revision()));
        rejects(CertificateException.class, () -> policy.requireApproved(USER, unapproved));
        rejects(CertificateException.class, () -> policy.requireApproved(OTHER, main));
        rejects(CertificateException.class, () -> policy.requireApproved(USER, null));
        rejects(CertificateException.class, () -> policy.requireApproved(null, main));
        rejects(UnsupportedOperationException.class, () -> both.accounts().clear());
        rejects(UnsupportedOperationException.class, () -> both.accounts().get(USER).fingerprints().clear());
        System.out.println("RESULT main=ALLOW tak_only=ALLOW unapproved_same_uuid=DENY missing_account=DENY immutable_readback=PASS");

        rejects(ConcurrentModificationException.class,
            () -> policy.replace(initialRevision, USER, deadline, Set.of(fingerprint(unapproved))));
        rejects(IllegalArgumentException.class,
            () -> policy.replace(both.revision(), USER, deadline, Set.of("AB".repeat(32))));
        rejects(IllegalArgumentException.class,
            () -> policy.replace(both.revision(), USER, deadline, Set.of("00")));
        rejects(IllegalArgumentException.class,
            () -> policy.replace(both.revision(), USER, now, Set.of(fingerprint(main))));
        rejects(IllegalArgumentException.class,
            () -> policy.replace(both.revision(), " ", deadline, Set.of(fingerprint(main))));
        rejects(IllegalArgumentException.class,
            () -> policy.replace(both.revision(), "x".repeat(257), deadline, Set.of(fingerprint(main))));
        var oversized = new HashSet<String>();
        for (int i = 0; i < 33; i++) oversized.add(String.format("%064x", i));
        rejects(IllegalArgumentException.class,
            () -> policy.replace(both.revision(), USER, deadline, oversized));
        check(policy.read().equals(both));
        var onlyTak = policy.replace(both.revision(), USER, deadline, Set.of(fingerprint(tak)));
        rejects(CertificateException.class, () -> policy.requireApproved(USER, main));
        check(policy.requireApproved(USER, tak).equals(onlyTak.revision()));
        check(both.accounts().get(USER).fingerprints().size() == 2);
        var empty = policy.replace(onlyTak.revision(), USER, deadline, Set.of());
        check(!empty.accounts().containsKey(USER));
        rejects(CertificateException.class, () -> policy.requireApproved(USER, tak));
        System.out.println("RESULT single_certificate_removal=PASS empty_set=DENY stale_write=REJECT invalid_write_preserves_state=PASS");

        policy.replace(empty.revision(), USER, deadline, Set.of(fingerprint(main), fingerprint(other),
            fingerprint(duplicateCn), fingerprint(duplicateCnRdn), fingerprint(multivaluedRdn), fingerprint(missingCn)));
        rejects(CertificateException.class, () -> policy.requireApproved(USER, other));
        rejects(CertificateException.class, () -> policy.requireApproved(USER, duplicateCn));
        rejects(CertificateException.class, () -> policy.requireApproved(USER, duplicateCnRdn));
        rejects(CertificateException.class, () -> policy.requireApproved(USER, missingCn));
        policy.requireApproved(USER, multivaluedRdn);
        policy.replace(policy.read().revision(), "fixture-ca", deadline, Set.of(fingerprint(ca)));
        rejects(CertificateException.class, () -> policy.requireApproved("fixture-ca", ca));
        System.out.println("RESULT wrong_cn=DENY duplicate_cn=DENY missing_cn=DENY multivalued_rdn=ALLOW ca_leaf=DENY");

        var boundary = new StrictFingerprintPolicy(Clock.fixed(deadline.minusNanos(1), ZoneOffset.UTC));
        var boundarySnapshot = boundary.replace(boundary.read().revision(), USER, deadline, Set.of(fingerprint(main)));
        boundary.requireApproved(USER, main);
        // Use a mutable clock only to exercise lease expiry without sleeping.
        var time = new java.util.concurrent.atomic.AtomicReference<>(now);
        var advancingClock = new Clock() {
            public java.time.ZoneId getZone() { return ZoneOffset.UTC; }
            public Clock withZone(java.time.ZoneId zone) { return Clock.fixed(instant(), zone); }
            public Instant instant() { return time.get(); }
        };
        var expiring = new StrictFingerprintPolicy(advancingClock);
        expiring.replace(expiring.read().revision(), USER, deadline, Set.of(fingerprint(main)));
        var lease = expiring.read();
        check(lease.authorityValidUntil().equals(now.plusSeconds(60)));
        time.set(now.plusSeconds(30));
        var renewed = expiring.renewAuthority(lease.revision());
        check(renewed.authorityValidUntil().equals(now.plusSeconds(90)));
        rejects(ConcurrentModificationException.class, () -> expiring.renewAuthority(lease.revision()));
        time.set(now.plusSeconds(89));
        expiring.requireApproved(USER, main);
        time.set(now.plusSeconds(90));
        rejects(CertificateException.class, () -> expiring.requireApproved(USER, main));
        rejects(IllegalStateException.class, () -> expiring.renewAuthority(renewed.revision()));
        rejects(IllegalStateException.class,
            () -> expiring.replace(renewed.revision(), USER, deadline, Set.of(fingerprint(main))));
        expiring.invalidate();
        expiring.replace(expiring.read().revision(), USER, deadline, Set.of(fingerprint(main)));
        expiring.requireApproved(USER, main);
        time.set(deadline);
        rejects(CertificateException.class, () -> expiring.requireApproved(USER, main));
        for (var invalidTime : List.of(main.getNotBefore().toInstant().minusSeconds(1), main.getNotAfter().toInstant().plusSeconds(1))) {
            var invalidDate = new StrictFingerprintPolicy(Clock.fixed(invalidTime, ZoneOffset.UTC));
            invalidDate.replace(invalidDate.read().revision(), USER, invalidTime.plusSeconds(300), Set.of(fingerprint(main)));
            rejects(CertificateException.class, () -> invalidDate.requireApproved(USER, main));
        }
        boundary.invalidate();
        rejects(CertificateException.class, () -> boundary.requireApproved(USER, main));
        rejects(ConcurrentModificationException.class,
            () -> boundary.replace(boundarySnapshot.revision(), USER, deadline, Set.of(fingerprint(main))));
        var restarted = new StrictFingerprintPolicy(clock);
        rejects(CertificateException.class, () -> restarted.requireApproved(USER, main));
        rejects(ConcurrentModificationException.class,
            () -> restarted.replace(both.revision(), USER, deadline, Set.of(fingerprint(main))));
        System.out.println("RESULT authority_lease=DENY expired_replay=REJECT lease_deadline=DENY expired_leaf=DENY future_leaf=DENY unavailable_projection=DENY restart=DENY pre_restart_write=REJECT");

        var concurrent = new StrictFingerprintPolicy(clock);
        var sharedRevision = concurrent.read().revision();
        var start = new CountDownLatch(1);
        var executor = Executors.newFixedThreadPool(2);
        try {
            var tasks = new java.util.ArrayList<java.util.concurrent.Future<Boolean>>();
            for (var leaf : List.of(main, tak)) {
                Callable<Boolean> update = () -> {
                    if (!start.await(5, TimeUnit.SECONDS)) throw new AssertionError("Concurrent test start timed out");
                    try {
                        concurrent.replace(sharedRevision, USER, deadline, Set.of(fingerprint(leaf)));
                        return true;
                    } catch (ConcurrentModificationException conflict) {
                        return false;
                    }
                };
                tasks.add(executor.submit(update));
            }
            start.countDown();
            boolean firstWon = tasks.get(0).get(5, TimeUnit.SECONDS);
            boolean secondWon = tasks.get(1).get(5, TimeUnit.SECONDS);
            check(firstWon != secondWon);
            check(concurrent.read().accounts().get(USER).fingerprints().size() == 1);
        } finally {
            executor.shutdownNow();
        }
        var bounded = new StrictFingerprintPolicy(clock);
        for (int i = 0; i < 1024; i++) {
            bounded.replace(bounded.read().revision(), "fixture-" + i, deadline, Set.of(fingerprint(main)));
        }
        var full = bounded.read();
        rejects(IllegalArgumentException.class,
            () -> bounded.replace(full.revision(), "overflow", deadline, Set.of(fingerprint(main))));
        check(bounded.read().equals(full));
        System.out.printf("RESULT concurrent_replacement=ONE_WINNER assertions=%d%n", assertions);
    }
}
