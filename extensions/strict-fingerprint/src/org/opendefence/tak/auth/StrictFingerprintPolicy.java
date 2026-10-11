package org.opendefence.tak.auth;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.time.Clock;
import java.time.Instant;
import java.util.ConcurrentModificationException;
import java.util.Date;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import javax.naming.NamingException;
import javax.naming.ldap.LdapName;

/** In-process approval policy used by the strict admission agent. */
public final class StrictFingerprintPolicy {
    private static final int MAX_ACCOUNTS = 1024;
    private static final int MAX_FINGERPRINTS = 32;
    private final Clock clock;
    private volatile Snapshot snapshot = new Snapshot(UUID.randomUUID(), Map.of());

    public record Approval(Instant validUntil, Set<String> fingerprints) {
        public Approval {
            Objects.requireNonNull(validUntil);
            fingerprints = Set.copyOf(fingerprints);
            if (fingerprints.size() > MAX_FINGERPRINTS
                    || fingerprints.stream().anyMatch(value -> !value.matches("[0-9a-f]{64}"))) {
                throw new IllegalArgumentException("Expected at most 32 lowercase SHA-256 fingerprints");
            }
        }
    }

    public record Snapshot(UUID revision, Map<String, Approval> accounts) {
        public Snapshot {
            Objects.requireNonNull(revision);
            accounts = Map.copyOf(accounts);
        }
    }

    public StrictFingerprintPolicy(Clock clock) {
        this.clock = Objects.requireNonNull(clock);
    }

    public Snapshot read() {
        return snapshot;
    }

    /** Replace one complete set. A stale or pre-restart revision cannot overwrite newer state. */
    public synchronized Snapshot replace(UUID expectedRevision, String accountId,
            Instant validUntil, Set<String> fingerprints) {
        if (!snapshot.revision().equals(expectedRevision)) {
            throw new ConcurrentModificationException("Approval revision changed; read before retrying");
        }
        if (accountId == null || accountId.isBlank() || accountId.length() > 256) {
            throw new IllegalArgumentException("Expected an account identifier of 1 through 256 characters");
        }
        var approval = new Approval(validUntil, fingerprints);
        if (!validUntil.isAfter(clock.instant())) {
            throw new IllegalArgumentException("Approval deadline must be in the future");
        }
        var accounts = new HashMap<>(snapshot.accounts());
        // An empty set denies access and needs no stored entry. The snapshot revision still advances.
        if (approval.fingerprints().isEmpty()) accounts.remove(accountId);
        else accounts.put(accountId, approval);
        if (accounts.size() > MAX_ACCOUNTS) throw new IllegalArgumentException("Too many approved accounts");
        snapshot = new Snapshot(UUID.randomUUID(), accounts);
        return snapshot;
    }

    /** The owner must invalidate the projection when authoritative state becomes unavailable. */
    public synchronized void invalidate() {
        snapshot = new Snapshot(UUID.randomUUID(), Map.of());
    }

    /** Called after TLS certificate-chain validation and before any role, token, or cache grant. */
    public UUID requireApproved(String accountId, X509Certificate leaf) throws CertificateException {
        var current = snapshot;
        var now = clock.instant();
        if (accountId == null || leaf == null) throw new CertificateException("Client identity required");
        var approval = current.accounts().get(accountId);
        if (approval == null || !now.isBefore(approval.validUntil())) {
            throw new CertificateException("Current certificate approval required");
        }
        leaf.checkValidity(Date.from(now));
        if (leaf.getBasicConstraints() >= 0 || !accountId.equals(commonName(leaf))) {
            throw new CertificateException("Client certificate identity mismatch");
        }
        try {
            var fingerprint = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(leaf.getEncoded()));
            if (!approval.fingerprints().contains(fingerprint)) {
                throw new CertificateException("Client certificate is not approved");
            }
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("The JVM must provide SHA-256", impossible);
        }
        return current.revision();
    }

    static String commonName(X509Certificate leaf) throws CertificateException {
        String name = null;
        try {
            for (var rdn : new LdapName(leaf.getSubjectX500Principal().getName()).getRdns()) {
                var attributes = rdn.toAttributes();
                var values = attributes.get("CN");
                if (values == null) continue;
                // JNDI attributes can collapse repeated identical CN values in one RDN.
                if (name != null || rdn.size() != attributes.size() || values.size() != 1
                        || !(values.get() instanceof String value) || value.isBlank()) {
                    throw new CertificateException("An unambiguous nonempty certificate CN required");
                }
                name = value;
            }
        } catch (NamingException invalid) {
            throw new CertificateException("Invalid certificate subject", invalid);
        }
        if (name == null) throw new CertificateException("Certificate CN required");
        return name;
    }
}
